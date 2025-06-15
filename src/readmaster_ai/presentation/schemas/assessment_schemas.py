"""
API Schemas for Assessment-related endpoints.
"""
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import List, Optional, Dict, Any # Added Dict, Any for analysis_data, options in SubmittedAnswerDetailSchema

# Attempt to import AssessmentStatus from domain entities
# If this causes circular dependency issues in a real setup, consider moving enums to a common value_objects location
try:
    from readmaster_ai.domain.entities.assessment import AssessmentStatus
except ImportError:
    # Fallback or define locally if domain entity import is problematic at this layer
    # For now, assuming it's resolvable or will be handled by restructuring if needed.
    # This might happen if domain entities also import from application DTOs or vice-versa indirectly.
    # A cleaner approach is often to have enums in a `domain.value_objects` or similar common place.
    # Assuming common_enums.py as per previous DTO structure:
    from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus


class AssessmentStudentInfoSchema(BaseModel):
    student_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    grade: Optional[str] = None

    class Config:
        from_attributes = True


class AssessmentReadingInfoSchema(BaseModel):
    reading_id: UUID
    title: Optional[str] = None

    class Config:
        from_attributes = True


class AssessmentListItemSchema(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    assessment_date: datetime
    updated_at: datetime
    student: AssessmentStudentInfoSchema
    reading: AssessmentReadingInfoSchema
    user_relationship_context: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = True


class PaginatedAssessmentListResponseSchema(BaseModel):
    items: List[AssessmentListItemSchema]
    page: int
    size: int
    total_count: int # Matches swagger

    class Config:
        from_attributes = True


class AssessmentResponseSchema(BaseModel):
    assessment_id: UUID
    student_id: UUID
    reading_id: UUID
    status: AssessmentStatus
    assessment_date: datetime
    updated_at: datetime
    audio_file_url: Optional[str] = None
    audio_duration: Optional[int] = None
    ai_raw_speech_to_text: Optional[str] = None
    assigned_by_teacher_id: Optional[UUID] = None
    assigned_by_parent_id: Optional[UUID] = None # Added

    class Config:
        from_attributes = True
        use_enum_values = True


class SubmittedAnswerDetailSchema(BaseModel): # Mirrored from DTO for consistency
    """Schema for individual student answer review, including question context."""
    question_id: UUID
    question_text: str = Field(..., description="The text of the quiz question.")
    selected_option_id: str = Field(..., description="The option ID selected by the student.")
    is_correct: bool = Field(..., description="Whether the selected option was correct.")
    correct_option_id: str = Field(..., description="The ID of the correct option for this question.")
    options: Dict[str, Any] = Field(..., description="All available options for this question.")

    class Config:
        from_attributes = True


class AssessmentResultDetailSchema(AssessmentResponseSchema): # Inherits fields
    reading_title: Optional[str] = None
    analysis_data: Optional[Dict[str, Any]] = None # Changed from 'dict' to 'Dict[str, Any]'
    comprehension_score: Optional[float] = None
    submitted_answers: List[SubmittedAnswerDetailSchema] = Field([], description="Detailed list of submitted quiz answers for review.")


    class Config:
        from_attributes = True # Ensure this is inherited if not automatically
        use_enum_values = True # Ensure this is inherited


class ParentAssignReadingRequestSchema(BaseModel):
    reading_id: UUID = Field(..., description="The ID of the reading material to assign.")
    due_date: Optional[date] = Field(None, description="Optional due date for the assignment.")

    class Config:
        from_attributes = True


class AssignmentUpdateSchema(BaseModel):
    due_date: Optional[date] = Field(None, description="New due date for the assignment.")
    # other updatable fields can be added here

    class Config:
        from_attributes = True
