"""
Data Transfer Objects (DTOs) for Class (ClassEntity) management operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
# Import UserResponseDTO for nesting student details within class responses
from .user_dtos import UserResponseDTO

class ClassBaseDTO(BaseModel):
    """Base DTO for class information, containing common fields."""
    class_name: str = Field(..., min_length=1, max_length=100, description="Name of the class.")
    grade_level: Optional[str] = Field(None, max_length=50, description="Grade level of the class, e.g., 'Grade 5', 'Secondary II'.")

class ClassCreateDTO(ClassBaseDTO):
    """DTO for creating a new class.
    'created_by_teacher_id' will be derived from the authenticated teacher user in the use case.
    """
    pass

class ClassUpdateDTO(BaseModel):
    """DTO for updating an existing class. All fields are optional."""
    class_name: Optional[str] = Field(None, min_length=1, max_length=100)
    grade_level: Optional[str] = Field(None, max_length=50)

class ClassResponseDTO(ClassBaseDTO):
    """DTO for representing a class in API responses."""
    class_id: UUID
    created_by_teacher_id: UUID # ID of the teacher who created the class
    created_at: datetime
    updated_at: datetime
    # List of students enrolled in the class. This will be populated by the use case.
    students: List[UserResponseDTO] = Field([], description="List of students enrolled in the class.")

    class Config:
        from_attributes = True # For Pydantic v2
        use_enum_values = True # If any enums were used directly in this DTO (none currently)

class AddStudentToClassRequestDTO(BaseModel):
    """DTO for adding a student to a class."""
    student_id: UUID = Field(..., description="The ID of the student to be added to the class.")

# No specific DTO for removing a student, as IDs are typically passed as path/query params.
# No specific DTO for listing students in a class, as response is List[UserResponseDTO].
