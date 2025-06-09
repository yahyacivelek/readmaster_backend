"""
Data Transfer Objects (DTOs) for Notification operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
# Assuming NotificationType enum is correctly defined and accessible
from readmaster_ai.domain.value_objects.common_enums import NotificationType

class NotificationResponseDTO(BaseModel):
    """DTO for representing a notification in API responses."""
    notification_id: UUID
    user_id: UUID # ID of the user to whom the notification belongs
    type: NotificationType # Uses the NotificationType enum
    message: str
    related_entity_id: Optional[UUID] = Field(None, description="ID of an entity related to the notification, e.g., assessment_id.")
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True # For Pydantic v2 (replaces orm_mode)
        use_enum_values = True # Ensures enum values are used in serialization for JSON


class MarkReadResponseDTO(BaseModel):
    """DTO for the response when a single notification is marked as read."""
    notification: NotificationResponseDTO # The updated notification details

class MarkAllReadResponseDTO(BaseModel):
    """DTO for the response when all unread notifications for a user are marked as read."""
    notifications_marked_read: int = Field(..., description="The number of notifications that were marked as read.")
    message: str = "All unread notifications marked as read."

# Future DTOs might include:
# class NotificationCreateDTO (if notifications can be created via API by some privileged user/system)
# class NotificationUpdateDTO (if content of notifications can be updated - less common)
