"""
Concrete implementation of the AssessmentResultRepository interface using SQLAlchemy.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from readmaster_ai.domain.entities.assessment_result import AssessmentResult as DomainAssessmentResult
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.infrastructure.database.models import AssessmentResultModel
# from readmaster_ai.shared.exceptions import ApplicationException # Not used yet, but for future

def _result_model_to_domain(model: AssessmentResultModel) -> Optional[DomainAssessmentResult]:
    """Converts an AssessmentResultModel SQLAlchemy object to a DomainAssessmentResult domain entity."""
    if not model:
        return None
    return DomainAssessmentResult(
        result_id=model.result_id,
        assessment_id=model.assessment_id,
        analysis_data=model.analysis_data, # Assumes JSONB from DB maps to Dict/JSON in domain
        comprehension_score=model.comprehension_score,
        created_at=model.created_at
    )

class AssessmentResultRepositoryImpl(AssessmentResultRepository):
    """SQLAlchemy implementation of the assessment result repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_update(self, result: DomainAssessmentResult) -> DomainAssessmentResult:
        """
        Creates a new assessment result or updates an existing one based on assessment_id.
        Uses PostgreSQL's ON CONFLICT DO UPDATE (upsert) feature.
        """
        # Values for insertion or on conflict for excluded
        values_to_insert = {
            "result_id": result.result_id, # Domain entity should generate this UUID
            "assessment_id": result.assessment_id,
            "analysis_data": result.analysis_data,
            "comprehension_score": result.comprehension_score
            # created_at has a default in the model, and is set in domain entity.
            # If we want DB to always set created_at on insert, don't include it here.
            # For an upsert, usually you don't update created_at.
        }
        if result.created_at: # Pass created_at if domain entity has it set
            values_to_insert["created_at"] = result.created_at

        stmt = pg_insert(AssessmentResultModel).values(**values_to_insert)

        # Define what to do on conflict (when assessment_id already exists)
        # We update analysis_data and comprehension_score. result_id and assessment_id remain the same.
        # created_at should not be updated on conflict.
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=[AssessmentResultModel.assessment_id], # Constraint that causes conflict
            set_={
                "analysis_data": stmt.excluded.analysis_data,
                "comprehension_score": stmt.excluded.comprehension_score,
                # "result_id": AssessmentResultModel.result_id, # Keep existing result_id (corrected from original prompt)
                                                            # This is actually not needed as pk should not be updated.
                                                            # PKs are part of index_elements or inferred.
                # "created_at": AssessmentResultModel.created_at # Keep existing created_at
            }
        ).returning(AssessmentResultModel) # Return the inserted or updated row

        db_execution_result = await self.session.execute(upsert_stmt)
        # self.session.flush() # Not typically needed with .returning() and execute
        updated_or_inserted_model = db_execution_result.scalar_one()
        # self.session.refresh(updated_or_inserted_model) # Not typically needed with .returning()

        domain_entity = _result_model_to_domain(updated_or_inserted_model)
        if not domain_entity: # Should not happen if upsert succeeded
            raise Exception("Failed to map AssessmentResultModel after upsert.") # More specific error
        return domain_entity


    async def get_by_assessment_id(self, assessment_id: UUID) -> Optional[DomainAssessmentResult]:
        """Retrieves an assessment result by its associated assessment_id."""
        stmt = select(AssessmentResultModel).where(AssessmentResultModel.assessment_id == assessment_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _result_model_to_domain(model)

    async def list_by_assessment_ids(self, assessment_ids: List[UUID]) -> List[DomainAssessmentResult]:
        """Retrieves all assessment results for a given list of assessment IDs."""
        if not assessment_ids: # Avoid empty IN clause error
            return []

        stmt = select(AssessmentResultModel)\
            .where(AssessmentResultModel.assessment_id.in_(assessment_ids))

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        domain_results = [_result_model_to_domain(m) for m in models if _result_model_to_domain(m) is not None]
        return domain_results
