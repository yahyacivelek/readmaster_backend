from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from readmaster_ai.domain.entities.user import User as DomainUser

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

    # Add other methods as they become necessary, e.g.,
    # @abstractmethod
    # async def update(self, user: DomainUser) -> DomainUser: pass
    #
    # @abstractmethod
    # async def delete(self, user_id: UUID) -> bool: pass
