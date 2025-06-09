from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID # Assuming user_id is UUID based on ERD

# Forward declaration if User entity is in a separate file and causes circular import
# from domain.entities.user import User
# For now, using 'Any' or a placeholder if User is not yet defined
from typing import Any

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[Any]: # Later: Optional[User]
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Any]: # Later: Optional[User]
        pass

    @abstractmethod
    async def create(self, user: Any) -> Any: # Later: user: User -> User
        pass

    # Add other methods as they become necessary, e.g.
    # @abstractmethod
    # async def update(self, user: Any) -> Any: pass
    #
    # @abstractmethod
    # async def delete(self, user_id: UUID) -> bool: pass
