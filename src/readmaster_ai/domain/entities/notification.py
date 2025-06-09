from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime

# Enums are now in value_objects
# from enum import Enum # No longer needed here
from readmaster_ai.domain.value_objects.common_enums import NotificationType


class Notification:
    notification_id: UUID
    user_id: UUID # FK
    type: NotificationType # Imported Enum
    message: str
    related_entity_id: Optional[UUID] # e.g., assessment_id, class_id
    is_read: bool
    created_at: datetime

    def __init__(self, user_id: UUID, type: Optional[NotificationType] = None, message: str = "", # Type can be None, default set below
                 notification_id: Optional[UUID] = None,
                 related_entity_id: Optional[UUID] = None,
                 is_read: bool = False,
                 created_at: Optional[datetime] = None):
        self.notification_id = notification_id if notification_id else uuid4()
        self.user_id = user_id
        self.type = type if type is not None else NotificationType.SYSTEM # Default type
        self.message = message
        self.related_entity_id = related_entity_id
        self.is_read = is_read
        self.created_at = created_at if created_at else datetime.utcnow()

    def mark_as_read(self):
        self.is_read = True
        print(f"Notification {self.notification_id} marked as read.")


    def mark_as_unread(self): # In case needed
        self.is_read = False
        print(f"Notification {self.notification_id} marked as unread.")
