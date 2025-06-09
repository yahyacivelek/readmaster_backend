"""
Data Transfer Objects (DTOs) for assessment-related operations.
"""
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
# from datetime import datetime # If needed for DTO fields like assessment_date

class CreateAssessmentDTO(BaseModel):
    """
    DTO for creating a new assessment.
    Specifies the data required from the client or presentation layer.
    """
    student_id: UUID
    reading_id: UUID
    assigned_by_teacher_id: Optional[UUID] = None
    # Add other relevant fields for creating an assessment, for example:
    # audio_file_url: Optional[str] = None # Might be set later in the process
    # assessment_date: Optional[datetime] = None # Might default in the entity or be set by system

    class Config:
        from_attributes = True # For Pydantic v2, ensures compatibility with ORM models if needed later
        # orm_mode = True # For Pydantic v1
