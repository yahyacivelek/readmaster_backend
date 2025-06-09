# tests/application/use_cases/test_notification_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timezone

from src.readmaster_ai.application.use_cases.notification_use_cases import (
    ListUserNotificationsUseCase, MarkNotificationAsReadUseCase, MarkAllNotificationsAsReadUseCase
)
from src.readmaster_ai.domain.entities.notification import Notification as DomainNotification
from src.readmaster_ai.domain.value_objects.common_enums import NotificationType as NotificationTypeEnum # Enum for type
from src.readmaster_ai.domain.entities.user import User as DomainUser
from src.readmaster_ai.domain.value_objects.common_enums import UserRole # Enum for user role
from src.readmaster_ai.domain.repositories.notification_repository import NotificationRepository
from src.readmaster_ai.shared.exceptions import NotFoundException, ForbiddenException


@pytest.fixture
def mock_notification_repo() -> MagicMock:
    """Fixture for a mocked NotificationRepository."""
    mock = MagicMock(spec=NotificationRepository)
    # Default behaviors for repository methods
    mock.list_by_user_id = AsyncMock(return_value=([], 0)) # (items, total_count)
    mock.get_by_id = AsyncMock(return_value=None) # Default: notification not found
    mock.mark_as_read = AsyncMock(return_value=None) # Default: not found or failed
    mock.mark_all_as_read = AsyncMock(return_value=0) # Default: 0 notifications updated
    return mock

@pytest.fixture
def sample_user_for_notifications() -> DomainUser:
    """Fixture for a sample user to whom notifications belong."""
    return DomainUser(
        user_id=uuid4(),
        email="notification.user@example.com",
        password_hash="test_hash",
        role=UserRole.STUDENT # Role can be any, just need a user
    )

@pytest.fixture
def sample_notification(sample_user_for_notifications: DomainUser) -> DomainNotification:
    """Fixture for a sample DomainNotification object."""
    return DomainNotification(
        notification_id=uuid4(),
        user_id=sample_user_for_notifications.user_id,
        type=NotificationTypeEnum.RESULT, # Use the enum member
        message="Your assessment results are ready.",
        is_read=False,
        created_at=datetime.now(timezone.utc) # Ensure timezone-aware
    )

@pytest.fixture
def sample_read_notification(sample_user_for_notifications: DomainUser) -> DomainNotification:
    """Fixture for an already read DomainNotification object."""
    return DomainNotification(
        notification_id=uuid4(),
        user_id=sample_user_for_notifications.user_id,
        type=NotificationTypeEnum.FEEDBACK,
        message="Feedback received.",
        is_read=True, # Already read
        created_at=datetime.now(timezone.utc) - timezone.timedelta(days=1) # Older
    )

# === ListUserNotificationsUseCase Tests ===
@pytest.mark.asyncio
async def test_list_user_notifications_success_empty(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser):
    # Repo default is ([], 0)
    use_case = ListUserNotificationsUseCase(notification_repo=mock_notification_repo)

    notifications, total = await use_case.execute(current_user=sample_user_for_notifications, page=1, size=10, unread_only=False)

    mock_notification_repo.list_by_user_id.assert_called_once_with(
        user_id=sample_user_for_notifications.user_id, page=1, size=10, unread_only=False
    )
    assert len(notifications) == 0
    assert total == 0

@pytest.mark.asyncio
async def test_list_user_notifications_with_data(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser, sample_notification: DomainNotification):
    mock_notification_repo.list_by_user_id.return_value = ([sample_notification], 1)
    use_case = ListUserNotificationsUseCase(notification_repo=mock_notification_repo)

    notifications, total = await use_case.execute(current_user=sample_user_for_notifications, page=1, size=10, unread_only=True)

    mock_notification_repo.list_by_user_id.assert_called_once_with(
        user_id=sample_user_for_notifications.user_id, page=1, size=10, unread_only=True
    )
    assert len(notifications) == 1
    assert total == 1
    assert notifications[0] == sample_notification

# === MarkNotificationAsReadUseCase Tests ===
@pytest.mark.asyncio
async def test_mark_notification_as_read_success(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser, sample_notification: DomainNotification):
    # Ensure the notification is initially unread
    sample_notification.is_read = False
    # Simulate that the repository's mark_as_read returns the updated notification
    # In a real scenario, the mock would change sample_notification.is_read to True
    updated_mock_notification = DomainNotification(**sample_notification.model_dump()) # Create a copy
    updated_mock_notification.is_read = True
    mock_notification_repo.mark_as_read.return_value = updated_mock_notification

    use_case = MarkNotificationAsReadUseCase(notification_repo=mock_notification_repo)

    result_notification = await use_case.execute(sample_notification.notification_id, sample_user_for_notifications)

    mock_notification_repo.mark_as_read.assert_called_once_with(sample_notification.notification_id, sample_user_for_notifications.user_id)
    assert result_notification is not None
    assert result_notification.is_read is True
    assert result_notification.notification_id == sample_notification.notification_id

@pytest.mark.asyncio
async def test_mark_notification_as_read_already_read(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser, sample_read_notification: DomainNotification):
    # sample_read_notification is already is_read=True
    # The repo's mark_as_read should return the notification as is if already read (or updated if it wasn't)
    mock_notification_repo.mark_as_read.return_value = sample_read_notification

    use_case = MarkNotificationAsReadUseCase(notification_repo=mock_notification_repo)

    result_notification = await use_case.execute(sample_read_notification.notification_id, sample_user_for_notifications)

    mock_notification_repo.mark_as_read.assert_called_once_with(sample_read_notification.notification_id, sample_user_for_notifications.user_id)
    assert result_notification.is_read is True # Remains true

@pytest.mark.asyncio
async def test_mark_notification_as_read_not_found(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser):
    # repo.mark_as_read returns None if not found or auth failed (auth handled by repo)
    mock_notification_repo.mark_as_read.return_value = None
    # To trigger NotFoundException from use case, get_by_id (called inside use case's exception handler) must also return None
    mock_notification_repo.get_by_id.return_value = None


    use_case = MarkNotificationAsReadUseCase(notification_repo=mock_notification_repo)

    non_existent_id = uuid4()
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(non_existent_id, sample_user_for_notifications)
    assert str(non_existent_id) in exc_info.value.message

@pytest.mark.asyncio
async def test_mark_notification_as_read_forbidden(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser, sample_notification: DomainNotification):
    # Simulate repository raising ForbiddenException (e.g., user_id mismatch)
    mock_notification_repo.mark_as_read.side_effect = ForbiddenException("User not authorized.")

    use_case = MarkNotificationAsReadUseCase(notification_repo=mock_notification_repo)

    with pytest.raises(ForbiddenException):
        await use_case.execute(sample_notification.notification_id, sample_user_for_notifications)


# === MarkAllNotificationsAsReadUseCase Tests ===
@pytest.mark.asyncio
async def test_mark_all_notifications_as_read_success(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser):
    # Simulate that 5 notifications were updated by the repository method
    mock_notification_repo.mark_all_as_read.return_value = 5
    use_case = MarkAllNotificationsAsReadUseCase(notification_repo=mock_notification_repo)

    count_updated = await use_case.execute(sample_user_for_notifications)

    mock_notification_repo.mark_all_as_read.assert_called_once_with(sample_user_for_notifications.user_id)
    assert count_updated == 5

@pytest.mark.asyncio
async def test_mark_all_notifications_as_read_no_unread(mock_notification_repo: MagicMock, sample_user_for_notifications: DomainUser):
    mock_notification_repo.mark_all_as_read.return_value = 0 # No notifications were updated
    use_case = MarkAllNotificationsAsReadUseCase(notification_repo=mock_notification_repo)

    count_updated = await use_case.execute(sample_user_for_notifications)
    assert count_updated == 0
