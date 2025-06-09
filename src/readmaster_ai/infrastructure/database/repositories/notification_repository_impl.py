"""
Concrete implementation of the NotificationRepository interface using SQLAlchemy.
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, func, and_

from readmaster_ai.domain.entities.notification import Notification as DomainNotification
# Assuming NotificationType is correctly imported by DomainNotification or available globally if needed for mapping
from readmaster_ai.domain.value_objects.common_enums import NotificationType as NotificationTypeEnum
from readmaster_ai.domain.repositories.notification_repository import NotificationRepository
from readmaster_ai.infrastructure.database.models import NotificationModel
from readmaster_ai.shared.exceptions import ForbiddenException # For auth checks on mark_as_read


def _notification_model_to_domain(model: NotificationModel) -> Optional[DomainNotification]:
    """Converts a NotificationModel SQLAlchemy object to a DomainNotification domain entity."""
    if not model:
        return None

    notification_type_enum_member = None
    if model.type:
        try:
            notification_type_enum_member = NotificationTypeEnum(model.type)
        except ValueError:
            print(f"Warning: Invalid notification type '{model.type}' in DB for notification {model.notification_id}")
            # Default to a generic type or handle error as appropriate
            # For now, this will cause DomainNotification init to fail if type is mandatory and invalid
            pass

    return DomainNotification(
        notification_id=model.notification_id,
        user_id=model.user_id,
        type=notification_type_enum_member, # Use the converted enum member
        message=model.message,
        related_entity_id=model.related_entity_id,
        is_read=model.is_read,
        created_at=model.created_at
    )

class NotificationRepositoryImpl(NotificationRepository):
    """SQLAlchemy implementation of the notification repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, notification: DomainNotification) -> DomainNotification:
        """Creates a new notification entry in the database."""
        if not isinstance(notification.type, NotificationTypeEnum):
             raise ValueError(f"Notification type must be a NotificationTypeEnum, got {type(notification.type)}")

        model = NotificationModel(
            notification_id=notification.notification_id, # Domain entity generates ID
            user_id=notification.user_id,
            type=notification.type.value, # Convert Enum to its string value for DB
            message=notification.message,
            related_entity_id=notification.related_entity_id,
            is_read=notification.is_read,
            created_at=notification.created_at # Domain entity sets this
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        domain_entity = _notification_model_to_domain(model)
        if not domain_entity: # Should not happen
            raise Exception("Failed to map created NotificationModel back to domain entity.")
        return domain_entity

    async def get_by_id(self, notification_id: UUID) -> Optional[DomainNotification]:
        """Retrieves a notification by its ID."""
        stmt = select(NotificationModel).where(NotificationModel.notification_id == notification_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _notification_model_to_domain(model)

    async def list_by_user_id(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 20,
        unread_only: bool = False
    ) -> Tuple[List[DomainNotification], int]:
        """Lists notifications for a user, with pagination and optional unread filter."""
        offset = (page - 1) * size

        conditions = [NotificationModel.user_id == user_id]
        if unread_only:
            conditions.append(NotificationModel.is_read == False) # SQLAlchemy uses False for boolean false

        # Query for fetching the items
        query = select(NotificationModel).where(and_(*conditions))
        # Query for counting total matching items
        count_query = select(func.count(NotificationModel.notification_id)).select_from(NotificationModel)\
            .where(and_(*conditions))

        total_count_result = await self.session.execute(count_query)
        total_count = total_count_result.scalar_one()

        query = query.order_by(NotificationModel.created_at.desc()).limit(size).offset(offset)

        result = await self.session.execute(query)
        models = result.scalars().all()

        domain_notifications = [_notification_model_to_domain(m) for m in models if _notification_model_to_domain(m) is not None]
        return domain_notifications, total_count

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional[DomainNotification]:
        """Marks a specific notification as read for a user if it belongs to them."""
        # First, fetch the notification to ensure it belongs to the user (authorization)
        notification_to_update = await self.get_by_id(notification_id)
        if not notification_to_update:
            return None # Notification not found

        if notification_to_update.user_id != user_id:
            raise ForbiddenException("User not authorized to modify this notification.")

        if notification_to_update.is_read: # Already read
            return notification_to_update

        # If authorized and not already read, update it
        stmt = (
            sqlalchemy_update(NotificationModel)
            .where(NotificationModel.notification_id == notification_id)
            # Redundant user_id check in WHERE, but good for safety if get_by_id was skipped
            # .where(NotificationModel.user_id == user_id)
            .values(is_read=True)
            .returning(NotificationModel) # Get the updated model back
        )
        result = await self.session.execute(stmt)
        updated_model = result.scalar_one_or_none() # Should find one if previous checks passed

        # await self.session.flush() # Not strictly needed with .returning() if autocommit is on
                                  # or if subsequent operations in same transaction will flush.

        return _notification_model_to_domain(updated_model)

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Marks all unread notifications as read for a specific user. Returns count of updated notifications."""
        stmt = (
            sqlalchemy_update(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.is_read == False) # Only update unread ones
            .values(is_read=True)
            # .returning(NotificationModel.notification_id) # Could return IDs if needed
        )
        result = await self.session.execute(stmt)
        # await self.session.flush() # Ensure changes are persisted before returning rowcount
        return result.rowcount # Number of rows affected by the update
