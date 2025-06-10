from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional
from .user import DomainUser, UserRole

if TYPE_CHECKING:
    from .student import Student
    from .progress_tracking import ProgressTracking # Added for return type hint clarity

class Parent(DomainUser):
    # children: List[Student] # Managed by repository

    def __init__(self, *args, **kwargs):
        kwargs['role'] = UserRole.PARENT
        super().__init__(*args, **kwargs)
        # self.children = [] # Initialized by repository

    def view_child_progress(self, child: Student) -> Optional[ProgressTracking]: # Return type: ProgressTracking or DTO
        # Logic to view a child's progress
        print(f"Parent {self.email} is viewing progress for child {child.email if child else 'N/A'}.")
        # Fetched via repository
        return None # Placeholder

    def receive_notifications(self, notification_message: str): # This seems like a system action, not a method on Parent
        # This method seems more like a system capability.
        # Parents would have notifications associated with them, viewable through a service.
        print(f"Parent {self.email} received notification: {notification_message}")
        pass
