"""
Concrete implementation of the AssessmentRepository interface using SQLAlchemy.
"""
from typing import Optional, List # List might be needed for future list methods
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update

from readmaster_ai.domain.entities.assessment import Assessment as DomainAssessment
# Import AssessmentStatus from domain entities for consistency with the entity definition
from readmaster_ai.domain.entities.assessment import AssessmentStatus
# Or, if you prefer the centralized one for all repository/infra logic:
# from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus as AssessmentStatusEnum
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.infrastructure.database.models import AssessmentModel
from readmaster_ai.shared.exceptions import ApplicationException # For error handling

def _assessment_model_to_domain(model: AssessmentModel) -> Optional[DomainAssessment]:
    """Converts an AssessmentModel SQLAlchemy object to a DomainAssessment domain entity."""
    if not model:
        return None

    status_enum_member = None
    if model.status:
        try:
            status_enum_member = AssessmentStatus(model.status) # Use AssessmentStatus from domain.entities
        except ValueError:
            # Log error: data in DB doesn't match Enum definition for AssessmentStatus
            # This indicates a data integrity issue or mismatch between enum definitions.
            print(f"Warning: Invalid assessment status '{model.status}' in DB for assessment {model.assessment_id}")
            # Depending on policy, either raise an error or default to a specific status.
            # For now, let it be None and potentially be caught by domain validation if status is mandatory.
            pass

    return DomainAssessment(
        assessment_id=model.assessment_id,
        student_id=model.student_id,
        reading_id=model.reading_id,
        assigned_by_teacher_id=model.assigned_by_teacher_id,
        audio_file_url=model.audio_file_url,
        audio_duration=model.audio_duration_seconds, # Mapping DB field name to domain entity field name
        status=status_enum_member if status_enum_member else AssessmentStatus.ERROR, # Default to ERROR if conversion failed
        assessment_date=model.assessment_date,
        ai_raw_speech_to_text=model.ai_raw_speech_to_text,
        updated_at=model.updated_at
        # result and quiz_answers are relationships, typically loaded separately or via specific use case logic
    )

class AssessmentRepositoryImpl(AssessmentRepository):
    """SQLAlchemy implementation of the assessment repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, assessment: DomainAssessment) -> DomainAssessment:
        """Creates a new assessment entry in the database."""
        model = AssessmentModel(
            assessment_id=assessment.assessment_id, # Application/use case generates ID
            student_id=assessment.student_id,
            reading_id=assessment.reading_id,
            assigned_by_teacher_id=assessment.assigned_by_teacher_id,
            audio_file_url=assessment.audio_file_url,
            audio_duration_seconds=assessment.audio_duration, # Map domain field to DB field
            status=assessment.status.value, # Convert Enum to its string value for DB
            assessment_date=assessment.assessment_date, # Domain entity sets this
            ai_raw_speech_to_text=assessment.ai_raw_speech_to_text,
            updated_at=assessment.updated_at # Domain entity sets this
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        domain_entity = _assessment_model_to_domain(model)
        if not domain_entity: # Should not happen if model creation and refresh succeeded
            raise ApplicationException("Failed to map created AssessmentModel back to domain entity.", status_code=500)
        return domain_entity

    async def get_by_id(self, assessment_id: UUID) -> Optional[DomainAssessment]:
        """Retrieves an assessment by its ID."""
        stmt = select(AssessmentModel).where(AssessmentModel.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _assessment_model_to_domain(model)

    async def update(self, assessment: DomainAssessment) -> Optional[DomainAssessment]:
        """Updates an existing assessment."""
        if not assessment.assessment_id:
            raise ValueError("Assessment ID must be provided for an update operation.")

        update_data = {
            "audio_file_url": assessment.audio_file_url,
            "audio_duration_seconds": assessment.audio_duration,
            "status": assessment.status.value, # Enum to string value
            "ai_raw_speech_to_text": assessment.ai_raw_speech_to_text,
            "updated_at": assessment.updated_at, # Domain entity should have updated this
        }
        # Filter out None values for fields that should not be set to NULL if not provided,
        # unless None is a valid value to clear the field.
        # For example, audio_file_url and ai_raw_speech_to_text can be explicitly set to None.
        # Status should always have a value.
        # update_data = {k: v for k, v in update_data.items() if v is not None} # Too broad

        # More specific filtering if needed:
        # filtered_update_data = {}
        # for k, v in update_data.items():
        #     if k in ["audio_file_url", "ai_raw_speech_to_text"]: # Fields that can be explicitly set to None
        #         filtered_update_data[k] = v
        #     elif v is not None: # Other fields only updated if a value is provided
        #         filtered_update_data[k] = v
        # if not filtered_update_data: # Avoid empty update
        #     return assessment # Or raise error if no updatable fields provided

        stmt = (
            sqlalchemy_update(AssessmentModel)
            .where(AssessmentModel.assessment_id == assessment.assessment_id)
            .values(**update_data) # Use original update_data which includes potential Nones for nullable fields
            .returning(AssessmentModel)
        )
        result = await self.session.execute(stmt)
        updated_model = result.scalar_one_or_none()

        if not updated_model:
            # Assessment with the given ID was not found.
            return None

        await self.session.flush()
        domain_entity = _assessment_model_to_domain(updated_model)
        if not domain_entity: # Should not happen if model is valid
             raise ApplicationException("Failed to map updated AssessmentModel back to domain entity.", status_code=500)
        return domain_entity

    async def list_by_student_ids(self, student_ids: List[UUID]) -> List[DomainAssessment]:
        """Retrieves all assessments for a given list of student IDs, ordered by date descending."""
        if not student_ids: # Avoid empty IN clause error
            return []

        stmt = select(AssessmentModel)\
            .where(AssessmentModel.student_id.in_(student_ids))\
            .order_by(AssessmentModel.assessment_date.desc())

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        domain_assessments = [_assessment_model_to_domain(m) for m in models if _assessment_model_to_domain(m) is not None]
        return domain_assessments
