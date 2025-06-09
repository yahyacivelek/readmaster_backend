"""
Data Transfer Objects (DTOs) for Quiz Question operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class QuizQuestionBaseDTO(BaseModel):
    """Base DTO for quiz questions, containing common fields."""
    question_text: str = Field(..., min_length=1, description="The text of the quiz question.")
    # Options can be a list of dicts or a dict of key-value pairs.
    # Example: [{"id": "A", "text": "Option A"}, {"id": "B", "text": "Option B"}]
    # Or: {"A": "Option A Text", "B": "Option B Text"}
    # For flexibility, using Dict[str, Any] or List[Dict[str, Any]] might be chosen.
    # The ERD shows JSONB, so Dict[str, Any] is a reasonable mapping for simple key-value options.
    # If options are structured (e.g. each option has an id and text), List[Dict] is better.
    # Let's assume options are like: {"A": "Text for A", "B": "Text for B"}
    options: Dict[str, str] = Field(..., description='Key-value pairs for options, e.g., {"A": "Option Text A", "B": "Option Text B"}.')
    correct_option_id: str = Field(..., description='The key corresponding to the correct option in the options dictionary (e.g., "A").')
    language: str = Field(default='en', max_length=10, description="Language code for the question.")

class QuizQuestionCreateDTO(QuizQuestionBaseDTO):
    """DTO for creating a new quiz question. Requires associating with a reading_id."""
    reading_id: UUID = Field(..., description="The ID of the reading this question belongs to.")

class QuizQuestionUpdateDTO(BaseModel):
    """DTO for updating an existing quiz question. All fields are optional."""
    question_text: Optional[str] = Field(None, min_length=1)
    options: Optional[Dict[str, str]] = Field(None, description='Key-value pairs for options.')
    correct_option_id: Optional[str] = Field(None, description='The key of the correct option.')
    language: Optional[str] = Field(None, max_length=10)
    # reading_id and added_by_admin_id are typically not changed during an update.

class QuizQuestionResponseDTO(QuizQuestionBaseDTO):
    """DTO for representing a quiz question in API responses."""
    question_id: UUID
    reading_id: UUID
    added_by_admin_id: Optional[UUID] # ID of the admin who added the question
    created_at: datetime
    # For student-facing views, correct_option_id might be excluded.
    # This DTO is likely for admin or internal use where correct answer is visible.

    class Config:
        from_attributes = True
        # use_enum_values = True # No enums directly in this DTO

class StudentQuizQuestionResponseDTO(QuizQuestionBaseDTO):
    """DTO for representing a quiz question in student-facing views (omits correct answer and admin details)."""
    question_id: UUID
    reading_id: UUID # Student might need this to know context if questions are ever displayed standalone
    # Excluded: correct_option_id (already omitted by inheriting from Base and not Response)
    # Excluded: added_by_admin_id
    # Excluded: created_at (unless relevant for student, e.g. "new question")

    class Config:
        from_attributes = True
