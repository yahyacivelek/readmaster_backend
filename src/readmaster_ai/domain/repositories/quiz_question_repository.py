"""
Abstract repository interface for QuizQuestion entities.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

# Forward declaration for QuizQuestion entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.quiz_question import QuizQuestion

class QuizQuestionRepository(ABC):
    """
    Defines the interface for interacting with quiz question data storage.
    """
    @abstractmethod
    async def create(self, question: 'QuizQuestion') -> 'QuizQuestion':
        """Creates a new quiz question."""
        pass

    @abstractmethod
    async def get_by_id(self, question_id: UUID) -> Optional['QuizQuestion']:
        """Retrieves a quiz question by its ID."""
        pass

    @abstractmethod
    async def list_by_reading_id(self, reading_id: UUID) -> List['QuizQuestion']:
        """Lists all quiz questions associated with a specific reading ID."""
        pass

    @abstractmethod
    async def update(self, question: 'QuizQuestion') -> Optional['QuizQuestion']:
        """
        Updates an existing quiz question.
        Returns the updated question or None if not found.
        """
        pass

    @abstractmethod
    async def delete(self, question_id: UUID) -> bool:
        """
        Deletes a quiz question by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        pass
