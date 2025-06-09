"""
Abstract repository interface for Notification entities.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from uuid import UUID

# Forward declaration for Notification entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.notification import Notification

class NotificationRepository(ABC):
    """
    Defines the interface for interacting with notification data storage.
    """
    @abstractmethod
    async def create(self, notification: 'Notification') -> 'Notification':
        """Creates a new notification entry in the database."""
        pass

    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> Optional['Notification']:
        """Retrieves a notification by its ID."""
        pass

    @abstractmethod
    async def list_by_user_id(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 20,
        unread_only: bool = False
    ) -> Tuple[List['Notification'], int]:
        """
        Lists notifications for a specific user with pagination.
        Can filter for unread notifications only.
        Returns a tuple: list of notifications and total count.
        """
        pass

    @abstractmethod
    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional['Notification']:
        """
        Marks a specific notification as read for a user.
        Ensures that the notification belongs to the user before marking as read.
        Returns the updated notification or None if not found or not authorized.
        """
        pass

    @abstractmethod
    async def mark_all_as_read(self, user_id: UUID) -> int:
        """
        Marks all unread notifications as read for a specific user.
        Returns the count of notifications that were marked as read.
        """
        pass

    # Optional future methods:
    # @abstractmethod
    # async def count_unread_by_user_id(self, user_id: UUID) -> int:
    #     """Counts unread notifications for a user."""
    #     pass
