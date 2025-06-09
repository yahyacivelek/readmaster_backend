"""
Use cases for managing Quiz Questions related to Reading materials.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List # For list return type

from readmaster_ai.domain.entities.quiz_question import QuizQuestion as DomainQuizQuestion
from readmaster_ai.domain.entities.user import DomainUser # For admin_id context
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository # To check reading existence
from readmaster_ai.application.dto.quiz_question_dtos import QuizQuestionCreateDTO, QuizQuestionUpdateDTO, QuizQuestionResponseDTO
from readmaster_ai.shared.exceptions import ApplicationException, NotFoundException


class AddQuizQuestionToReadingUseCase:
    """Use case for adding a new quiz question to a reading."""
    def __init__(self, quiz_repo: QuizQuestionRepository, reading_repo: ReadingRepository):
        self.quiz_repo = quiz_repo
        self.reading_repo = reading_repo

    async def execute(self, question_data: QuizQuestionCreateDTO, admin_user: DomainUser) -> DomainQuizQuestion:
        """
        Executes the quiz question creation process.
        Args:
            question_data: DTO containing data for the new quiz question.
            admin_user: The authenticated admin user performing the action.
        Returns:
            The created DomainQuizQuestion entity.
        Raises:
            NotFoundException: If the associated reading does not exist.
        """
        # Validate that the reading exists before adding a question to it
        reading = await self.reading_repo.get_by_id(question_data.reading_id)
        if not reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(question_data.reading_id))

        new_question = DomainQuizQuestion(
            question_id=uuid4(), # Application generates ID
            reading_id=question_data.reading_id,
            question_text=question_data.question_text,
            options=question_data.options, # DTO should ensure this is Dict[str, str]
            correct_option_id=question_data.correct_option_id,
            language=question_data.language,
            added_by_admin_id=admin_user.user_id, # Set admin ID
            created_at=datetime.now(timezone.utc)
            # QuizQuestion domain entity does not have updated_at currently
        )
        created_question = await self.quiz_repo.create(new_question)
        return created_question

class GetQuizQuestionUseCase:
    """Use case for retrieving a single quiz question."""
    def __init__(self, quiz_repo: QuizQuestionRepository):
        self.quiz_repo = quiz_repo

    async def execute(self, question_id: UUID) -> Optional[DomainQuizQuestion]:
        """
        Retrieves a quiz question by its ID.
        Args:
            question_id: The ID of the quiz question.
        Returns:
            The DomainQuizQuestion entity if found.
        Raises:
            NotFoundException: If the quiz question is not found.
        """
        question = await self.quiz_repo.get_by_id(question_id)
        if not question:
            raise NotFoundException(resource_name="QuizQuestion", resource_id=str(question_id))
        return question

class ListQuizQuestionsByReadingUseCase:
    """Use case for listing all quiz questions for a specific reading."""
    def __init__(self, quiz_repo: QuizQuestionRepository):
        self.quiz_repo = quiz_repo

    async def execute(self, reading_id: UUID) -> List[DomainQuizQuestion]:
        """
        Retrieves all quiz questions for a given reading ID.
        Args:
            reading_id: The ID of the reading.
        Returns:
            A list of DomainQuizQuestion entities.
        """
        # Optionally, could also check if reading_id exists via ReadingRepository first.
        return await self.quiz_repo.list_by_reading_id(reading_id)


class UpdateQuizQuestionUseCase:
    """Use case for updating an existing quiz question."""
    def __init__(self, quiz_repo: QuizQuestionRepository):
        self.quiz_repo = quiz_repo

    async def execute(self, question_id: UUID, update_data: QuizQuestionUpdateDTO, admin_user: DomainUser) -> DomainQuizQuestion:
        """
        Executes the quiz question update process.
        Args:
            question_id: ID of the quiz question to update.
            update_data: DTO containing updated data.
            admin_user: The authenticated admin user.
        Returns:
            The updated DomainQuizQuestion entity.
        Raises:
            NotFoundException: If the quiz question is not found.
            ApplicationException: If the update fails.
        """
        existing_question = await self.quiz_repo.get_by_id(question_id)
        if not existing_question:
            raise NotFoundException(resource_name="QuizQuestion", resource_id=str(question_id))

        # Optionally: Check admin authorization.

        update_values = update_data.model_dump(exclude_unset=True)
        for key, value in update_values.items():
            if hasattr(existing_question, key):
                setattr(existing_question, key, value)

        # If QuizQuestion domain entity had updated_at:
        # existing_question.updated_at = datetime.now(timezone.utc)

        updated_question = await self.quiz_repo.update(existing_question)
        if not updated_question:
             raise ApplicationException(f"Failed to update quiz question with ID {question_id}.", status_code=500)
        return updated_question

class DeleteQuizQuestionUseCase:
    """Use case for deleting a quiz question."""
    def __init__(self, quiz_repo: QuizQuestionRepository):
        self.quiz_repo = quiz_repo

    async def execute(self, question_id: UUID, admin_user: DomainUser) -> bool:
        """
        Executes the quiz question deletion process.
        Args:
            question_id: ID of the quiz question to delete.
            admin_user: The authenticated admin user.
        Returns:
            True if deletion was successful.
        Raises:
            NotFoundException: If the quiz question is not found.
        """
        existing_question = await self.quiz_repo.get_by_id(question_id)
        if not existing_question:
            raise NotFoundException(resource_name="QuizQuestion", resource_id=str(question_id))

        # Optionally: Check admin authorization.

        return await self.quiz_repo.delete(question_id)
