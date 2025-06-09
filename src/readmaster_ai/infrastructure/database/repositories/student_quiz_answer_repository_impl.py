"""
Concrete implementation of the StudentQuizAnswerRepository interface using SQLAlchemy.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
# from sqlalchemy.dialects.postgresql import insert as pg_insert # Not used for simple bulk add

from readmaster_ai.domain.entities.student_quiz_answer import StudentQuizAnswer as DomainStudentQuizAnswer
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository
from readmaster_ai.infrastructure.database.models import StudentQuizAnswerModel

def _quiz_answer_model_to_domain(model: StudentQuizAnswerModel) -> Optional[DomainStudentQuizAnswer]:
    """Converts a StudentQuizAnswerModel SQLAlchemy object to a DomainStudentQuizAnswer domain entity."""
    if not model:
        return None
    return DomainStudentQuizAnswer(
        answer_id=model.answer_id,
        assessment_id=model.assessment_id,
        question_id=model.question_id,
        student_id=model.student_id,
        selected_option_id=model.selected_option_id,
        is_correct=model.is_correct,
        answered_at=model.answered_at
    )

class StudentQuizAnswerRepositoryImpl(StudentQuizAnswerRepository):
    """SQLAlchemy implementation of the student quiz answer repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create(self, answers: List[DomainStudentQuizAnswer]) -> List[DomainStudentQuizAnswer]:
        """
        Creates multiple student quiz answer entries in the database using `add_all`.
        """
        models_to_create = [
            StudentQuizAnswerModel(
                answer_id=ans.answer_id, # Domain entity should generate UUID
                assessment_id=ans.assessment_id,
                question_id=ans.question_id,
                student_id=ans.student_id,
                selected_option_id=ans.selected_option_id,
                is_correct=ans.is_correct,
                answered_at=ans.answered_at # Domain entity sets this
            ) for ans in answers
        ]

        self.session.add_all(models_to_create)
        await self.session.flush() # Flush to persist all and handle potential DB errors.
                                   # Also populates any server-side defaults if models were to be refreshed.

        # Refreshing each model individually after add_all can be inefficient if not needed.
        # If IDs are client-generated (as in domain entity) and no other server defaults are critical
        # to get back immediately, returning the original domain objects is fine.
        # For now, we assume answer_id is generated in domain and passed.

        # Convert back to domain objects if there's a need to return objects with DB state (e.g. server defaults)
        # For this simple case, returning the input list of domain objects.
        # If models needed refreshing:
        # created_domain_answers = []
        # for model in models_to_create:
        #     await self.session.refresh(model) # If there are server-side defaults to fetch
        #     created_domain_answers.append(_quiz_answer_model_to_domain(model))
        # return created_domain_answers

        return answers

    async def list_by_assessment_id(self, assessment_id: UUID) -> List[DomainStudentQuizAnswer]:
        """Retrieves all student quiz answers for a given assessment ID."""
        stmt = select(StudentQuizAnswerModel)\
            .where(StudentQuizAnswerModel.assessment_id == assessment_id)\
            .order_by(StudentQuizAnswerModel.answered_at) # Optional: order by when answered

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        domain_answers = [_quiz_answer_model_to_domain(m) for m in models if _quiz_answer_model_to_domain(m) is not None]
        return domain_answers
