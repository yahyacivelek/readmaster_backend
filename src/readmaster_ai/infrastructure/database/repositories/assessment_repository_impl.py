"""
Concrete implementation of the AssessmentRepository interface using SQLAlchemy.
"""
from typing import Optional, List, Tuple # List might be needed for future list methods, Tuple for new method
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, func, and_, or_, desc, join
from sqlalchemy.orm import aliased
from datetime import datetime, timezone

from readmaster_ai.domain.entities.assessment import Assessment as DomainAssessment
# Import AssessmentStatus from domain entities for consistency with the entity definition
from readmaster_ai.domain.entities.assessment import AssessmentStatus
from readmaster_ai.domain.value_objects.common_enums import UserRole # Added UserRole
# Or, if you prefer the centralized one for all repository/infra logic:
# from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus as AssessmentStatusEnum
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.infrastructure.database.models import ( # Added more models
    AssessmentModel,
    UserModel,
    ReadingModel,
    ClassModel,
    StudentsClassesAssociation,
    TeachersClassesAssociation,
    ParentsStudentsAssociation
)
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
        updated_at=model.updated_at,
        # result and quiz_answers are relationships, typically loaded separately or via specific use case logic
    )

class AssessmentRepositoryImpl(AssessmentRepository):
    """SQLAlchemy implementation of the assessment repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, assessment: DomainAssessment) -> DomainAssessment:
        """Creates a new assessment entry in the database."""
        # Ensure datetimes are timezone-aware UTC
        assessment_date = assessment.assessment_date
        updated_at = assessment.updated_at

        if assessment_date and assessment_date.tzinfo is None:
            assessment_date = assessment_date.replace(tzinfo=timezone.utc)
        if updated_at and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        model = AssessmentModel(
            assessment_id=assessment.assessment_id, # Application/use case generates ID
            student_id=assessment.student_id,
            reading_id=assessment.reading_id,
            assigned_by_teacher_id=assessment.assigned_by_teacher_id,
            audio_file_url=assessment.audio_file_url,
            audio_duration_seconds=assessment.audio_duration, # Map domain field to DB field
            status=assessment.status.value, # Convert Enum to its string value for DB
            assessment_date=assessment_date, # Use timezone-aware datetime
            ai_raw_speech_to_text=assessment.ai_raw_speech_to_text,
            updated_at=updated_at, # Use timezone-aware datetime

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

    async def list_by_reading_id(self, reading_id: UUID, user_id: UUID, role: UserRole, page: int, size: int) -> Tuple[List[DomainAssessment], int]:
        """
        Retrieves assessments associated with a specific reading_id,
        filtered by the user's role and ownership, with pagination.
        Returns a tuple containing a list of Assessment entities and the total count.
        """
        StudentModel = aliased(UserModel, name="student_user")

        query = (
            select(AssessmentModel)
            .join(ReadingModel, AssessmentModel.reading_id == ReadingModel.reading_id)
            .join(StudentModel, AssessmentModel.student_id == StudentModel.user_id)
        )

        if role == UserRole.TEACHER:
            query = (
                query
                .join(StudentsClassesAssociation, StudentModel.user_id == StudentsClassesAssociation.c.student_id)
                .join(ClassModel, StudentsClassesAssociation.c.class_id == ClassModel.class_id)
                .join(TeachersClassesAssociation, ClassModel.class_id == TeachersClassesAssociation.c.class_id)
                .where(TeachersClassesAssociation.c.teacher_id == user_id)
            )
        elif role == UserRole.PARENT:
            query = (
                query
                .join(ParentsStudentsAssociation, StudentModel.user_id == ParentsStudentsAssociation.c.student_id)
                .where(ParentsStudentsAssociation.c.parent_id == user_id)
            )
        else:
            # For roles not explicitly handled (e.g. ADMIN, STUDENT),
            # this specific listing logic might not apply or might need different rules.
            # Returning empty list as a safe default if no specific logic for the role.
            # Or, this could be an assertion error if such roles should not reach this point.
            return [], 0

        # Common filter for reading_id, applied after role-specific joins
        query = query.where(AssessmentModel.reading_id == reading_id)

        # Count query: built from the filtered query before ordering and pagination
        # Clearing any previous order_by is important for count subqueries.
        count_stmt = select(func.count(AssessmentModel.assessment_id)).select_from(query.order_by(None).subquery())

        total_count_result = await self.session.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        if total_count == 0:
            return [], 0

        # Main query for items with ordering and pagination
        query = query.order_by(AssessmentModel.assessment_date.desc()).offset((page - 1) * size).limit(size)

        result = await self.session.execute(query)
        assessment_models = result.scalars().all()

        domain_assessments = []
        for model in assessment_models:
            domain_assessment = _assessment_model_to_domain(model)
            if domain_assessment:
                domain_assessments.append(domain_assessment)

        return domain_assessments, total_count

    async def list_by_child_and_assigner(self, student_id: UUID, parent_id: UUID, page: int, size: int) -> Tuple[List[DomainAssessment], int]:
        """Lists assessments for a specific child assigned by a specific parent."""
        query_base = select(AssessmentModel).where(
            AssessmentModel.student_id == student_id,
            AssessmentModel.assigned_by_parent_id == parent_id
        )

        # Count statement
        count_stmt = select(func.count(AssessmentModel.assessment_id)).select_from(query_base.order_by(None).alias("count_subquery"))
        total_count_result = await self.session.execute(count_stmt)
        total_count = total_count_result.scalar_one()

        if total_count == 0:
            return [], 0

        # Main query for items
        results_stmt = query_base.order_by(AssessmentModel.assessment_date.desc()).offset((page - 1) * size).limit(size)
        result = await self.session.execute(results_stmt)
        assessment_models = result.scalars().all()

        domain_assessments = [_assessment_model_to_domain(model) for model in assessment_models if _assessment_model_to_domain(model) is not None]
        return domain_assessments, total_count

    async def delete(self, assessment_id: UUID) -> bool:
        """Deletes an assessment by its ID."""
        stmt = sqlalchemy_delete(AssessmentModel).where(AssessmentModel.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        # No explicit flush or commit here; handled by UoW or service layer
        return result.rowcount > 0

from sqlalchemy import delete as sqlalchemy_delete # Ensure this is imported at the top if not already
