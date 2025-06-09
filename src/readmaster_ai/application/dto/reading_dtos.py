"""
Data Transfer Objects (DTOs) for Reading material operations.
"""
from pydantic import BaseModel, Field, HttpUrl # HttpUrl for content_image_url
from typing import Optional, List # Removed Dict, Any as not directly used here
from uuid import UUID
from datetime import datetime
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel # Use centralized enum
from .quiz_question_dtos import StudentQuizQuestionResponseDTO # Changed to student-specific DTO

class ReadingBaseDTO(BaseModel):
    """Base DTO for reading material, containing common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Title of the reading material.")
    content_text: Optional[str] = Field(None, description="Text content of the reading material.")
    content_image_url: Optional[HttpUrl] = Field(None, description="URL to an image related to the content.") # Use HttpUrl for validation
    age_category: Optional[str] = Field(None, max_length=50, description="Target age category, e.g., '6-8 years'.")
    difficulty: Optional[DifficultyLevel] = Field(None, description="Difficulty level of the reading.") # Uses DifficultyLevel enum
    language: str = Field(default='en', max_length=10, description="Language code, e.g., 'en', 'es'.")
    genre: Optional[str] = Field(None, max_length=100, description="Genre of the reading material.")

class ReadingCreateDTO(ReadingBaseDTO):
    """DTO for creating a new reading material.
    'added_by_admin_id' will be set by the use case based on the authenticated admin user.
    """
    pass

class ReadingUpdateDTO(BaseModel):
    """DTO for updating an existing reading material. All fields are optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content_text: Optional[str] = None
    content_image_url: Optional[HttpUrl] = None # Allow HttpUrl for update
    age_category: Optional[str] = Field(None, max_length=50)
    difficulty: Optional[DifficultyLevel] = None
    language: Optional[str] = Field(None, max_length=10)
    genre: Optional[str] = Field(None, max_length=100)

class ReadingResponseDTO(ReadingBaseDTO):
    """DTO for representing reading material in API responses."""
    reading_id: UUID
    added_by_admin_id: Optional[UUID] # ID of the admin who added the reading
    created_at: datetime
    updated_at: datetime
    questions: List[StudentQuizQuestionResponseDTO] = [] # Use student-safe DTO

    class Config:
        from_attributes = True # For Pydantic v2 (replaces orm_mode)
        # Ensure enums are serialized as their values for JSON responses
        use_enum_values = True # Add this if enums should be string values in response directly from Pydantic
                               # Otherwise, FastAPI handles it with its jsonable_encoder.
                               # For DTOs that might be used internally, not always needed.
                               # For API responses, FastAPI's default JSON encoding of enums (to their values) is usually fine.
