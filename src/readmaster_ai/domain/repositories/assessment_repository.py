"""
Abstract repository interface for Assessment entities.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from readmaster_ai.domain.entities.assessment import Assessment

class AssessmentRepository(ABC):
    """
    Defines the interface for interacting with assessment data storage.
    """
    @abstractmethod
    async def get_by_id(self, assessment_id: UUID) -> Optional[Assessment]:
        """Retrieves an assessment by its ID."""
        pass

    @abstractmethod
    async def create(self, assessment: Assessment) -> Assessment:
        """Creates a new assessment."""
        pass

    # Add other necessary methods, for example:
    # @abstractmethod
    # async def list_by_student_id(self, student_id: UUID) -> List[Assessment]:
    #     """Lists all assessments for a given student."""
    #     pass

    @abstractmethod
    async def update(self, assessment: Assessment) -> Optional[Assessment]: # For updating status, audio_url etc.
        """
        Updates an existing assessment.
        Returns the updated assessment or None if not found or update fails.
        """
        pass

    @abstractmethod
    async def list_by_student_ids(self, student_ids: List[UUID]) -> List['Assessment']:
        """
        Retrieves all assessments for a list of student IDs.
        Args:
            student_ids: A list of student UUIDs.
        Returns:
            A list of Assessment domain entities.
        """
        pass
