"""
Abstract repository interface for StudentQuizAnswer entities.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

# Forward declaration for StudentQuizAnswer entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.student_quiz_answer import StudentQuizAnswer

class StudentQuizAnswerRepository(ABC):
    """
    Defines the interface for interacting with student quiz answer data storage.
    """
    @abstractmethod
    async def bulk_create(self, answers: List['StudentQuizAnswer']) -> List['StudentQuizAnswer']:
        """
        Creates multiple student quiz answer entries in bulk.
        Args:
            answers: A list of StudentQuizAnswer domain entities to create.
        Returns:
            A list of the created StudentQuizAnswer domain entities (potentially with DB-assigned fields).
        """
        pass

    @abstractmethod
    async def list_by_assessment_id(self, assessment_id: UUID) -> List['StudentQuizAnswer']:
        """
        Retrieves all student quiz answers associated with a specific assessment ID.
        Args:
            assessment_id: The UUID of the assessment.
        Returns:
            A list of StudentQuizAnswer domain entities.
        """
        pass

    # Optional future methods:
    # @abstractmethod
    # async def get_by_id(self, answer_id: UUID) -> Optional['StudentQuizAnswer']:
    #     """Retrieves a specific answer by its ID."""
    #     pass
    #
    # @abstractmethod
    # async def delete_by_assessment_id(self, assessment_id: UUID) -> int:
    #     """Deletes all answers associated with an assessment. Returns count of deleted."""
    #     pass
