"""
Data Transfer Objects (DTOs) for Progress Monitoring features.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

# Assuming UserResponseDTO is already defined and accessible for student_info
# If not, it would need to be defined or imported, e.g.:
# from .user_dtos import UserResponseDTO
# For now, using a placeholder if UserResponseDTO is not yet refactored into user_dtos.py
# For the purpose of this DTO, let's define a minimal UserResponseDTO if not available.
try:
    from .user_dtos import UserResponseDTO
except ImportError:
    # Minimal placeholder if user_dtos.py or UserResponseDTO isn't created/exported yet
    class UserResponseDTO(BaseModel):
        user_id: UUID
        email: str
        first_name: Optional[str] = None
        last_name: Optional[str] = None
        # role: Optional[str] = None # Role might be relevant

        class Config:
            from_attributes = True


class AssessmentAttemptSummaryDTO(BaseModel):
    """Summary of a single assessment attempt for progress tracking views."""
    assessment_id: UUID
    reading_title: Optional[str] = Field(None, description="Title of the reading material.")
    assessment_date: datetime
    status: str = Field(..., description="Status of the assessment, e.g., COMPLETED, PENDING_AUDIO.")
    comprehension_score: Optional[float] = Field(None, description="Comprehension score if available (0-100).")
    fluency_score: Optional[float] = Field(None, description="Overall fluency score from AI analysis, if available.")
    # Add other key metrics like words_per_minute, accuracy_score if desired.

    class Config:
        from_attributes = True


class StudentProgressSummaryDTO(BaseModel):
    """Detailed progress summary for a single student."""
    student_info: UserResponseDTO
    total_assessments_assigned: int = Field(0, description="Total number of assessments assigned or started by the student.")
    total_assessments_completed: int = Field(0, description="Total number of assessments marked as COMPLETED.")
    average_comprehension_score: Optional[float] = Field(None, description="Average comprehension score over completed assessments.")
    average_fluency_score: Optional[float] = Field(None, description="Average fluency score over completed assessments.")
    recent_assessments: List[AssessmentAttemptSummaryDTO] = Field(default_factory=list, description="Summary of a few recent assessment attempts.")
    # Potential future additions:
    # - Progress trends (e.g., scores over time for specific metrics)
    # - Areas of strength/weakness based on aggregated AI feedback

    class Config:
        from_attributes = True


class ClassProgressReportDTO(BaseModel):
    """Comprehensive progress report for an entire class."""
    class_id: UUID
    class_name: str
    teacher_info: Optional[UserResponseDTO] = Field(None, description="Information about the class teacher (creator).")
    student_progress_summaries: List[StudentProgressSummaryDTO] = Field(default_factory=list)
    class_average_comprehension: Optional[float] = Field(None, description="Average comprehension score for the entire class.")
    class_average_fluency: Optional[float] = Field(None, description="Average fluency score for the entire class.")
    # Potential future additions:
    # - Distribution of scores
    # - Students needing attention

    class Config:
        from_attributes = True
