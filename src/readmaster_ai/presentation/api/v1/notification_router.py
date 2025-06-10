"""
API Router for User Notification operations.
Allows authenticated users to list their notifications and mark them as read.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession # For DI context
from typing import List
from uuid import UUID

# Infrastructure (Database session for DI)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities for type hinting)
from readmaster_ai.domain.entities.user import DomainUser

# Presentation (Dependencies, Schemas - DTOs are imported from Application)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
from readmaster_ai.application.dto.notification_dtos import (
    NotificationResponseDTO, MarkReadResponseDTO, MarkAllReadResponseDTO
)
from readmaster_ai.presentation.schemas.pagination import PaginatedResponse # Reusing existing pagination schema

# Repositories (Abstract for DI)
from readmaster_ai.domain.repositories.notification_repository import NotificationRepository

# Infrastructure (Concrete Repositories for DI)
from readmaster_ai.infrastructure.database.repositories.notification_repository_impl import NotificationRepositoryImpl

# Application (Use Cases)
from readmaster_ai.application.use_cases.notification_use_cases import (
    ListUserNotificationsUseCase, MarkNotificationAsReadUseCase, MarkAllNotificationsAsReadUseCase
)

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException, ForbiddenException, ApplicationException


router = APIRouter(
    prefix="/notifications",
    tags=["User Notifications"],
    dependencies=[Depends(get_current_user)] # All notification routes require user authentication
)

# --- Repository Dependency Provider Function ---
def get_notification_repo(session: AsyncSession = Depends(get_db)) -> NotificationRepository:
    """Dependency provider for NotificationRepository."""
    return NotificationRepositoryImpl(session)


# --- Notification Endpoints ---
@router.get("", response_model=PaginatedResponse[NotificationResponseDTO])
async def list_my_notifications(
    current_user: DomainUser = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    page: int = Query(1, ge=1, description="Page number for pagination."),
    size: int = Query(20, ge=1, le=100, description="Number of items per page."),
    unread_only: bool = Query(False, description="Set to true to fetch only unread notifications.")
):
    """
    Retrieves a paginated list of notifications for the authenticated user.
    Can be filtered to show only unread notifications.
    """
    use_case = ListUserNotificationsUseCase(notification_repo)
    try:
        domain_notifications, total_count = await use_case.execute(
            current_user=current_user,
            page=page,
            size=size,
            unread_only=unread_only
        )
        # Convert domain entities to DTOs for the response
        items = [NotificationResponseDTO.model_validate(n) for n in domain_notifications]

        return PaginatedResponse[NotificationResponseDTO](
            items=items,
            total=total_count,
            page=page,
            size=size
        )
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error listing notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notifications due to an unexpected error."
        )


@router.patch("/{notification_id}/read", response_model=MarkReadResponseDTO)
async def mark_one_notification_as_read(
    notification_id: UUID = Path(..., description="The ID of the notification to mark as read."),
    current_user: DomainUser = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repo)
):
    """
    Marks a specific notification as read for the authenticated user.
    """
    use_case = MarkNotificationAsReadUseCase(notification_repo)
    try:
        updated_notification_domain = await use_case.execute(
            notification_id=notification_id,
            current_user=current_user
        )
        return MarkReadResponseDTO(notification=NotificationResponseDTO.model_validate(updated_notification_domain))
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: # If repository explicitly raises this for auth failure
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        print(f"Unexpected error marking notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read due to an unexpected error."
        )

@router.post("/mark-all-read", response_model=MarkAllReadResponseDTO)
async def mark_all_my_notifications_as_read(
    current_user: DomainUser = Depends(get_current_user),
    notification_repo: NotificationRepository = Depends(get_notification_repo)
):
    """
    Marks all unread notifications as read for the authenticated user.
    """
    use_case = MarkAllNotificationsAsReadUseCase(notification_repo)
    try:
        count_marked = await use_case.execute(current_user)
        return MarkAllReadResponseDTO(notifications_marked_read=count_marked)
    except Exception as e:
        print(f"Unexpected error marking all notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read due to an unexpected error."
        )
