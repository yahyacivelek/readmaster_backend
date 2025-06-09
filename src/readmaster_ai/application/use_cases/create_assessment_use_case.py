"""
Use case for creating a new assessment.
"""
from readmaster_ai.domain.entities.assessment import Assessment
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.application.dto.assessment_dto import CreateAssessmentDTO

class CreateAssessmentUseCase:
    """
    Orchestrates the creation of a new assessment.
    It takes a DTO, creates an Assessment domain entity,
    and uses the repository to persist it.
    """
    def __init__(self, assessment_repo: AssessmentRepository):
        self.assessment_repo = assessment_repo

    async def execute(self, request_dto: CreateAssessmentDTO) -> Assessment:
        """
        Executes the assessment creation process.
        Args:
            request_dto: Data required to create the assessment.
        Returns:
            The created Assessment domain entity.
        """
        # Business logic to create an assessment
        new_assessment = Assessment(
            student_id=request_dto.student_id,
            reading_id=request_dto.reading_id,
            assigned_by_teacher_id=request_dto.assigned_by_teacher_id
            # The Assessment entity's __init__ handles default status, assessment_date, etc.
        )

        created_assessment = await self.assessment_repo.create(new_assessment)
        # You might want to return a DTO here instead of the domain entity
        # depending on your application's architectural choices.
        return created_assessment
