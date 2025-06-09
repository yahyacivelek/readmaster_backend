"""
Abstract repository interface for AssessmentResult entities.
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

# Forward declaration for AssessmentResult entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.assessment_result import AssessmentResult

class AssessmentResultRepository(ABC):
    """
    Defines the interface for interacting with assessment result data storage.
    """
    @abstractmethod
    async def create_or_update(self, result: 'AssessmentResult') -> 'AssessmentResult':
        """
        Creates a new assessment result or updates an existing one.
        An "upsert" operation based on a unique constraint (e.g., assessment_id).
        Args:
            result: The AssessmentResult domain entity to create or update.
        Returns:
            The created or updated AssessmentResult domain entity.
        """
        pass

    @abstractmethod
    async def get_by_assessment_id(self, assessment_id: UUID) -> Optional['AssessmentResult']:
        """
        Retrieves an assessment result by its associated assessment_id.
        Args:
            assessment_id: The UUID of the assessment.
        Returns:
            The AssessmentResult domain entity if found, otherwise None.
        """
        pass

    # Future methods might include:
    # @abstractmethod
    # async def get_by_id(self, result_id: UUID) -> Optional['AssessmentResult']:
    #     """Retrieves an assessment result by its own primary key (result_id)."""
    #     pass
    #
    # @abstractmethod
    # async def delete_by_assessment_id(self, assessment_id: UUID) -> bool:
    #     """Deletes an assessment result by its associated assessment_id."""
    #     pass

    @abstractmethod
    async def list_by_assessment_ids(self, assessment_ids: List[UUID]) -> List['AssessmentResult']:
        """
        Retrieves all assessment results for a list of assessment IDs.
        Args:
            assessment_ids: A list of assessment UUIDs.
        Returns:
            A list of AssessmentResult domain entities.
        """
        pass
