"""
Data Transfer Objects (DTOs) for User related operations,
primarily for representing user information in other DTOs or API responses
where a slimmed-down or specific user representation is needed.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
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
