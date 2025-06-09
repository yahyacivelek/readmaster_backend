"""
Abstract repository interface for Reading entities.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from uuid import UUID
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel # Use centralized enum

# Forward declaration for Reading entity to avoid circular import if Reading uses this repo in its methods (not typical)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.reading import Reading


class ReadingRepository(ABC):
    """
    Defines the interface for interacting with reading material data storage.
    """
    @abstractmethod
    async def create(self, reading: 'Reading') -> 'Reading':
        """Creates a new reading material entry."""
        pass

    @abstractmethod
    async def get_by_id(self, reading_id: UUID) -> Optional['Reading']:
        """Retrieves a reading material by its ID."""
        pass

    @abstractmethod
    async def list_all(
        self,
        page: int = 1,
        size: int = 20,
        language: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        age_category: Optional[str] = None
    ) -> Tuple[List['Reading'], int]:
        """
        Lists all reading materials with pagination and optional filters.
        Returns a tuple containing the list of readings and the total count.
        """
        pass

    @abstractmethod
    async def update(self, reading: 'Reading') -> Optional['Reading']:
        """
        Updates an existing reading material.
        Returns the updated reading or None if not found.
        """
        pass

    @abstractmethod
    async def delete(self, reading_id: UUID) -> bool:
        """
        Deletes a reading material by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        pass
