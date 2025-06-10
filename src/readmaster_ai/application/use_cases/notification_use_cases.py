"""
Use cases related to managing and retrieving user Notifications.
"""
from typing import List, Tuple, Optional
from uuid import UUID

# Domain Entities and Repositories
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.entities.notification import Notification as DomainNotification
from readmaster_ai.domain.repositories.notification_repository import NotificationRepository

# Application DTOs (NotificationResponseDTO is not directly returned by use cases here,
# as use cases typically return domain entities. DTO conversion happens at presentation layer.)
# from readmaster_ai.application.dto.notification_dtos import NotificationResponseDTO

# Shared Exceptions
from readmaster_ai.shared.exceptions import NotFoundException, ForbiddenException, ApplicationException


class ListUserNotificationsUseCase:
    """Use case for listing notifications for the current user."""
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def execute(
        self,
        current_user: DomainUser,
        page: int,
        size: int,
        unread_only: bool
    ) -> Tuple[List[DomainNotification], int]:
        """
        Retrieves a paginated list of notifications for the authenticated user.

        Args:
            current_user: The authenticated user (DomainUser).
            page: Page number for pagination.
            size: Number of items per page.
            unread_only: If True, only unread notifications are returned.

        Returns:
            A tuple containing a list of DomainNotification entities and the total count.
        """
        # The repository method list_by_user_id is responsible for fetching
        # notifications specifically for the given user_id.
        notifications, total_count = await self.notification_repo.list_by_user_id(
            user_id=current_user.user_id,
            page=page,
            size=size,
            unread_only=unread_only
        )
        return notifications, total_count

class MarkNotificationAsReadUseCase:
    """Use case for marking a specific notification as read for the current user."""
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def execute(self, notification_id: UUID, current_user: DomainUser) -> DomainNotification:
        """
        Marks a notification as read.

        Args:
            notification_id: The ID of the notification to mark as read.
            current_user: The authenticated user (DomainUser).

        Returns:
            The updated DomainNotification entity.

        Raises:
            NotFoundException: If the notification is not found.
            ForbiddenException: If the user is not authorized to modify the notification
                                (should be handled by repository's user_id check).
        """
        # The repository's mark_as_read method handles the user_id check
        # to ensure a user can only mark their own notifications as read.
        updated_notification = await self.notification_repo.mark_as_read(
            notification_id=notification_id,
            user_id=current_user.user_id
        )

        if not updated_notification:
            # This can happen if:
            # 1. Notification with notification_id does not exist.
            # 2. Notification exists but does not belong to current_user.user_id (ForbiddenException should be raised by repo ideally).
            # 3. Notification was already read (repo returns it as is).
            # For a clearer API, repo's mark_as_read should raise NotFound or Forbidden.
            # If it returns None only when not found after auth check, then NotFoundException is appropriate.
            # Let's assume repo's mark_as_read returns None if not found OR if already read and no change made,
            # but raises ForbiddenException if user mismatch.

            # To distinguish "not found" from "already read", we can fetch it again.
            # However, the current repo impl for mark_as_read returns the object if already read.
            # So, if it's None, it means it was not found or (if repo logic changes) not authorized.
            # The repo implementation already raises ForbiddenException if user_id doesn't match.
            # And it returns the existing (already read) notification if no change was made.
            # So, if `updated_notification` is None here, it strictly means "not found".
            raise NotFoundException(resource_name="Notification", resource_id=str(notification_id))

        return updated_notification

class MarkAllNotificationsAsReadUseCase:
    """Use case for marking all unread notifications as read for the current user."""
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def execute(self, current_user: DomainUser) -> int:
        """
        Marks all unread notifications for the current user as read.

        Args:
            current_user: The authenticated user (DomainUser).

        Returns:
            The count of notifications that were marked as read.
        """
        # The repository method handles scoping this operation to the current_user.user_id.
        count_marked_as_read = await self.notification_repo.mark_all_as_read(current_user.user_id)
        return count_marked_as_read
