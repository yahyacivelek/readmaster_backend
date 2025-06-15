from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus

class AssessmentStudentInfoDTO(BaseModel):
    student_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # Grade is not directly on UserModel. It might come from ClassModel.grade_level.
    # For now, let's make it optional and the use case can try to populate it.
    grade: Optional[str] = None

    class Config:
        from_attributes = True

class AssessmentReadingInfoDTO(BaseModel):
    reading_id: UUID
    title: Optional[str] = None

    class Config:
        from_attributes = True

class AssessmentListItemDTO(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    assessment_date: datetime
    updated_at: datetime
    student: AssessmentStudentInfoDTO
    reading: AssessmentReadingInfoDTO
    user_relationship_context: Optional[str] = None # e.g., class name for teacher, "Child" for parent

    class Config:
        from_attributes = True

class PaginatedAssessmentListResponseDTO(BaseModel):
    items: List[AssessmentListItemDTO]
    page: int
    size: int
    total_count: int

    class Config:
        from_attributes = True
