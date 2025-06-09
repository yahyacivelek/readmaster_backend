"""
Concrete implementation of the QuizQuestionRepository interface using SQLAlchemy.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete

from readmaster_ai.domain.entities.quiz_question import QuizQuestion as DomainQuizQuestion
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.infrastructure.database.models import QuizQuestionModel
from readmaster_ai.shared.exceptions import ApplicationException # For error handling if needed


def _quiz_model_to_domain(model: QuizQuestionModel) -> Optional[DomainQuizQuestion]:
    """Converts a QuizQuestionModel SQLAlchemy object to a DomainQuizQuestion domain entity."""
    if not model:
        return None
    return DomainQuizQuestion(
        question_id=model.question_id,
        reading_id=model.reading_id,
        question_text=model.question_text,
        options=model.options, # Assuming JSONB from DB is compatible with Dict[str, Any] in domain
        correct_option_id=model.correct_option_id,
        language=model.language,
        added_by_admin_id=model.added_by_admin_id,
        created_at=model.created_at
        # Note: QuizQuestion domain entity currently doesn't have updated_at.
        # If it were added, it would be mapped here from model.updated_at.
    )

class QuizQuestionRepositoryImpl(QuizQuestionRepository):
    """SQLAlchemy implementation of the quiz question repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, question: DomainQuizQuestion) -> DomainQuizQuestion:
        """Creates a new quiz question in the database."""
        model = QuizQuestionModel(
            question_id=question.question_id, # Application generates ID
            reading_id=question.reading_id,
            question_text=question.question_text,
            options=question.options,
            correct_option_id=question.correct_option_id,
            language=question.language,
            added_by_admin_id=question.added_by_admin_id,
            created_at=question.created_at # Domain entity sets this
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        domain_entity = _quiz_model_to_domain(model)
        if not domain_entity: # Should not happen if model creation and refresh succeeded
            raise ApplicationException("Failed to map created QuizQuestionModel back to domain entity.", status_code=500)
        return domain_entity

    async def get_by_id(self, question_id: UUID) -> Optional[DomainQuizQuestion]:
        """Retrieves a quiz question by its ID."""
        stmt = select(QuizQuestionModel).where(QuizQuestionModel.question_id == question_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return _quiz_model_to_domain(model)

    async def list_by_reading_id(self, reading_id: UUID) -> List[DomainQuizQuestion]:
        """Lists all quiz questions for a given reading ID."""
        stmt = select(QuizQuestionModel).where(QuizQuestionModel.reading_id == reading_id).order_by(QuizQuestionModel.created_at)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        # Ensure that mapping failures don't stop the entire list, but filter out None results
        return [dq for m in models if (dq := _quiz_model_to_domain(m)) is not None]


    async def update(self, question: DomainQuizQuestion) -> Optional[DomainQuizQuestion]:
        """Updates an existing quiz question."""
        if not question.question_id:
            raise ValueError("Question ID must be provided for an update operation.")

        update_data = {
            "question_text": question.question_text,
            "options": question.options,
            "correct_option_id": question.correct_option_id,
            "language": question.language,
            # reading_id and added_by_admin_id are typically not updatable.
            # If QuizQuestionModel had an 'updated_at', it would be set here:
            # "updated_at": datetime.now(timezone.utc)
        }
        stmt = (
            sqlalchemy_update(QuizQuestionModel)
            .where(QuizQuestionModel.question_id == question.question_id)
            .values(**update_data)
            .returning(QuizQuestionModel)
        )
        result = await self.session.execute(stmt)
        updated_model = result.scalar_one_or_none()

        if not updated_model:
            return None # Question not found for update

        await self.session.flush()
        domain_entity = _quiz_model_to_domain(updated_model)
        if not domain_entity: # Should not happen
            raise ApplicationException("Failed to map updated QuizQuestionModel back to domain entity.", status_code=500)
        return domain_entity

    async def delete(self, question_id: UUID) -> bool:
        """Deletes a quiz question by its ID."""
        stmt = sqlalchemy_delete(QuizQuestionModel).where(QuizQuestionModel.question_id == question_id)
        result = await self.session.execute(stmt)
        # await self.session.flush() # See note in ReadingRepositoryImpl about flush for delete
        return result.rowcount > 0
