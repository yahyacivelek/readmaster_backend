from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional, Literal # Import Literal

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # Add other common fields from User entity if needed
    preferred_language: Optional[str] = 'en'


class UserCreateRequest(UserBase):
    password: str
    role: Optional[str] = None # Examples: "student", "teacher", "parent", "admin". Processed in use case.


class UserUpdateRequest(BaseModel): # Separate schema for updates
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_language: Optional[str] = None # Added for profile update
    # password: Optional[str] = None # Password updates should be handled separately

class UserResponse(UserBase):
    user_id: UUID
    role: str # Role should be string representation of UserRole enum
    # preferred_language is in UserBase, so it's inherited.

    class Config:
        from_attributes = True # Changed from orm_mode = True for Pydantic v2

# New Schemas for Parent and Teacher creating Student accounts
class ParentChildCreateRequestSchema(UserCreateRequest):
    # Inherits email, password, first_name, last_name, preferred_language from UserCreateRequest
    # Role is fixed to 'student' and not settable by the parent user.
    role: Literal["student"] = "student"

class TeacherStudentCreateRequestSchema(UserCreateRequest):
    # Inherits email, password, first_name, last_name, preferred_language from UserCreateRequest
    # Role is fixed to 'student' and not settable by the teacher user.
    role: Literal["student"] = "student"
