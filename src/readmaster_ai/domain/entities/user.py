from __future__ import annotations # For type hinting classes not yet defined
from typing import List, TYPE_CHECKING, Optional
from uuid import UUID, uuid4
from datetime import datetime
# Assuming UserRole enum will be defined, perhaps in value_objects
# from ..value_objects.common import UserRole # Example path

if TYPE_CHECKING:
    # Import dependent classes for type hinting only to avoid circular imports at runtime
    from .assessment import Assessment
    from .class_entity import ClassEntity # Renamed from Class to ClassEntity to avoid keyword clash
    # Parent, Student are subclasses, not typically needed for User base class hints here
    # from .parent import Parent
    # from .student import Student
    from .progress_tracking import ProgressTracking # Assuming ProgressTracking entity
    from .reading import Reading # For takeAssessment method in Student
    # Enums are now in value_objects
    # from enum import Enum # No longer needed here

from readmaster_ai.domain.value_objects.common_enums import UserRole


class DomainUser:
    user_id: UUID
    email: str
    password_hash: str  # This should not be directly accessible in many cases
    first_name: Optional[str]
    last_name: Optional[str]
    role: UserRole # Now imported
    created_at: datetime
    updated_at: datetime
    preferred_language: str
    is_active: bool # Added is_active field

    def __init__(self, user_id: Optional[UUID] = None, email: str = "", password_hash: str = "", role: Optional[UserRole] = None, # Role can be None, default set below
                 first_name: Optional[str] = None, last_name: Optional[str] = None,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None,
                 preferred_language: str = 'en', is_active: bool = True): # Added is_active to constructor
        self.user_id = user_id if user_id else uuid4()
        self.email = email
        self.password_hash = password_hash # Handle securely
        self.first_name = first_name
        self.last_name = last_name
        self.role = role if role is not None else UserRole.STUDENT # Default role if not provided
        self.created_at = created_at if created_at else datetime.utcnow()
        self.updated_at = updated_at if updated_at else datetime.utcnow()
        self.preferred_language = preferred_language

    def login(self):
        # This method would typically be handled by an auth service, not directly on User entity
        print(f"User {self.email} attempting login.")
        # Actual login logic (e.g., password verification) happens in an application service.
        pass

    def update_profile(self, first_name: Optional[str] = None, last_name: Optional[str] = None, preferred_language: Optional[str] = None):
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if preferred_language is not None:
            self.preferred_language = preferred_language
        self.updated_at = datetime.utcnow()
        print(f"Profile updated for user {self.email}.")

    def change_password(self, new_password_hash: str):
        # Password change logic, ensuring old password might be verified first by a service
        self.password_hash = new_password_hash
        self.updated_at = datetime.utcnow()
        print(f"Password changed for user {self.email}.")

    # Add from_orm method for Pydantic compatibility if needed later
    # @classmethod
    # def from_orm(cls, model):
    #     return cls(...)
