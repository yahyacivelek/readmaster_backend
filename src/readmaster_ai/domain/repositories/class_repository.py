"""
Abstract repository interface for ClassEntity domain entities.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from uuid import UUID

# Forward declarations for type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.class_entity import ClassEntity
    from readmaster_ai.domain.entities.user import User as DomainUser

class ClassRepository(ABC):
    """
    Defines the interface for interacting with class data storage.
    """
    @abstractmethod
    async def create(self, class_obj: 'ClassEntity') -> 'ClassEntity':
        """Creates a new class."""
        pass

    @abstractmethod
    async def get_by_id(self, class_id: UUID) -> Optional['ClassEntity']:
        """Retrieves a class by its ID. May include associated students/teachers."""
        pass

    @abstractmethod
    async def list_by_teacher_id(self, teacher_id: UUID, page: int = 1, size: int = 20) -> Tuple[List['ClassEntity'], int]:
        """Lists classes created by or assigned to a specific teacher with pagination."""
        pass

    @abstractmethod
    async def update(self, class_obj: 'ClassEntity') -> Optional['ClassEntity']:
        """Updates an existing class. Returns the updated class or None if not found."""
        pass

    @abstractmethod
    async def delete(self, class_id: UUID) -> bool:
        """Deletes a class by its ID. Returns True if successful."""
        pass

    @abstractmethod
    async def add_student_to_class(self, class_id: UUID, student_id: UUID) -> bool:
        """Adds a student to a class. Returns True if successful, False if already exists or error."""
        pass

    @abstractmethod
    async def remove_student_from_class(self, class_id: UUID, student_id: UUID) -> bool:
        """Removes a student from a class. Returns True if successful (student was removed)."""
        pass

    @abstractmethod
    async def get_students_in_class(self, class_id: UUID) -> List['DomainUser']:
        """Retrieves a list of students enrolled in a specific class."""
        pass
