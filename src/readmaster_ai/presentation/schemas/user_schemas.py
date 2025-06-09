from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional # For optional fields

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # Add other common fields from User entity if needed

class UserCreateRequest(UserBase):
    password: str
    # role: Optional[str] = "student" # Example: default role

class UserUpdateRequest(BaseModel): # Separate schema for updates
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # password: Optional[str] = None # Password updates should be handled separately

class UserResponse(UserBase):
    user_id: UUID
    role: Optional[str] = None # Assuming role is part of User entity
    # preferred_language: Optional[str] = None

    class Config:
        from_attributes = True # Changed from orm_mode = True for Pydantic v2
