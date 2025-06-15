from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from readmaster_ai.domain.entities.user import DomainUser

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[DomainUser]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[DomainUser]:
        pass

    @abstractmethod
    async def create(self, user: DomainUser) -> DomainUser:
        pass

    @abstractmethod
    async def create_user_with_role(self, user_dto: 'UserCreateDTO') -> DomainUser: # Added UserCreateDTO type hint
        """Creates a new user with a specific role, potentially from a DTO."""
        pass

    @abstractmethod
    async def update(self, user: DomainUser) -> DomainUser:
        """Updates an existing user's details in the storage."""
        pass

    @abstractmethod
    async def link_parent_to_student(self, parent_id: UUID, student_id: UUID, relationship_type: str) -> bool:
        """Links a parent user to a student user."""
        pass

    @abstractmethod
    async def list_children_by_parent_id(self, parent_id: UUID) -> List[DomainUser]:
        """Lists all students (children) linked to a specific parent ID."""
        pass

    @abstractmethod
    async def is_parent_of_student(self, parent_id: UUID, student_id: UUID) -> bool:
        """Checks if a user is a parent of a given student."""
        pass

    @abstractmethod
    async def get_student_ids_for_parent(self, parent_id: UUID) -> List[UUID]:
        """Retrieves a list of student UUIDs linked to a specific parent ID."""
        pass

    # Add other methods as they become necessary, e.g.,
    # @abstractmethod
    # async def delete(self, user_id: UUID) -> bool: pass
