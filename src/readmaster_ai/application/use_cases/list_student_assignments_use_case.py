from __future__ import annotations
from uuid import UUID
from typing import List, Tuple, Optional

from readmaster_ai.application.dto.student_dto import StudentAssignmentItemDTO
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.value_objects import AssessmentStatus
from readmaster_ai.domain.entities import Assessment, Reading # Assuming Assessment has due_date

class ListStudentAssignmentsUseCase:
    def __init__(self, assessment_repository: AssessmentRepository, reading_repository: ReadingRepository):
        self.assessment_repository = assessment_repository
        self.reading_repository = reading_repository

    async def execute(
        self,
        student_id: UUID,
        page: int,
        size: int,
        status: Optional[AssessmentStatus] = None,
    ) -> Tuple[List[StudentAssignmentItemDTO], int]:
        """
        Fetches a paginated list of assignments for a given student.
        An assignment is an assessment linked to the student.
        """
        assessments, total_count = await self.assessment_repository.list_by_student_id_paginated(
            student_id=student_id,
            page=page,
            size=size,
            status=status,
            # We might need to add more filters here if "assignment" has specific criteria,
            # e.g., only those with assigned_by_teacher_id or assigned_by_parent_id.
            # For now, listing all assessments for the student.
        )

        student_assignment_dtos: List[StudentAssignmentItemDTO] = []
        for assessment in assessments:
            reading: Optional[Reading] = None
            if assessment.reading_id:
                reading = await self.reading_repository.get_by_id(assessment.reading_id)

            # Assuming Assessment entity has 'assessment_date' for 'assigned_date'
            # and an optional 'due_date' field.
            # If Assessment entity doesn't have due_date, this will need adjustment.
            student_assignment_dtos.append(
                StudentAssignmentItemDTO(
                    assessment_id=assessment.assessment_id, # Corrected field name
                    reading_id=assessment.reading_id,
                    reading_title=reading.title if reading else "Unknown Reading",
                    status=assessment.status,
                    assigned_date=assessment.assessment_date, # Or assessment.created_at
                    due_date=assessment.due_date, # Access due_date directly
                    assigned_by_teacher_id=assessment.assigned_by_teacher_id,
                    assigned_by_parent_id=assessment.assigned_by_parent_id,
                )
            )

        return student_assignment_dtos, total_count
