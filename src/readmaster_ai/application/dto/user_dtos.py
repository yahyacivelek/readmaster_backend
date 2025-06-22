"""
Data Transfer Objects (DTOs) for User related operations,
primarily for representing user information in other DTOs or API responses
where a slimmed-down or specific user representation is needed.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
# Ensure UserRole is imported from the centralized location
from readmaster_ai.domain.value_objects.common_enums import UserRole

class UserResponseDTO(BaseModel):
    """
    A DTO for representing basic user details, often nested in other responses
    (e.g., details of students in a class list).
    It omits sensitive information like password_hash.
    """
    user_id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole # Use the UserRole enum for type safety and consistency

    class Config:
        from_attributes = True # For Pydantic v2 (replaces orm_mode)
        use_enum_values = True # Ensures enum values are used in serialization if needed by client
                               # FastAPI usually handles this correctly for JSON responses.


class AdminUserResponseDTO(UserResponseDTO):
    """
    Extended UserResponseDTO for admin view, including timestamps.
    """
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


class PaginatedAdminUserResponseDTO(BaseModel):
    """
    Paginated response for listing users in the admin panel.
    """
    items: List[AdminUserResponseDTO]
    total: int
    page: int
    size: int

    class Config:
        from_attributes = True


class UserCreateDTO(BaseModel): # More generic DTO, can be used by use cases
    email: EmailStr
    password: str # Plain password, hashing happens in use case or service
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_language: Optional[str] = 'en'
    role: UserRole # Use the enum

    class Config:
        from_attributes = True


class TeacherStudentCreateRequestDTO(BaseModel):
    """DTO for a teacher creating a student account."""
    email: EmailStr
    password: str # Plain password
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_language: Optional[str] = 'en'
    # Role is implicitly 'student' for this use case, will be set by the use case.

    class Config:
        from_attributes = True


class ParentChildCreateRequestDTO(BaseModel):
    """DTO for a parent creating a child (student) account."""
    email: EmailStr
    password: str # Plain password
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_language: Optional[str] = 'en'
    # Role is implicitly 'student' for this use case, will be set by the use case.

    class Config:
        from_attributes = True
