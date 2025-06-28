from __future__ import annotations
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field

from readmaster_ai.domain.value_objects import AssessmentStatus

class StudentAssignmentItemDTO(BaseModel):
    assessment_id: UUID = Field(..., description="The unique identifier for this specific assignment attempt/assessment.")
    reading_id: UUID = Field(..., description="The identifier of the reading material.")
    reading_title: str = Field(..., description="The title of the reading material.")
    status: AssessmentStatus
    assigned_date: datetime = Field(..., description="The date and time when the assignment was created/assigned.")
    due_date: Optional[date] = Field(None, description="The due date for the assignment, if set.")
    assigned_by_teacher_id: Optional[UUID] = Field(None, description="ID of the teacher who assigned this, if applicable.")
    assigned_by_parent_id: Optional[UUID] = Field(None, description="ID of the parent who assigned this, if applicable.")

    class Config:
        orm_mode = True # Enable ORM mode for easier conversion from domain objects
        use_enum_values = True # Ensure enum values are used in serialization

class PaginatedStudentAssignmentResponseDTO(BaseModel):
    items: List[StudentAssignmentItemDTO]
    total: int
    page: int
    size: int

    class Config:
        orm_mode = True
        use_enum_values = True
