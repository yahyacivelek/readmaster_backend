"""
Abstract repository interface for SystemConfiguration entities.
"""
from abc import ABC, abstractmethod
from typing import Optional, List # Added List for get_all_configs

# Forward declaration for SystemConfiguration entity
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from readmaster_ai.domain.entities.system_configuration import SystemConfiguration

class SystemConfigurationRepository(ABC):
    """
    Defines the interface for interacting with system configuration data storage.
    """
    @abstractmethod
    async def get_by_key(self, key: str) -> Optional['SystemConfiguration']:
        """
        Retrieves a system configuration setting by its unique key.
        Args:
            key: The unique key of the configuration setting.
        Returns:
            The SystemConfiguration domain entity if found, otherwise None.
        """
        pass

    @abstractmethod
    async def set_config(self, config: 'SystemConfiguration') -> 'SystemConfiguration':
        """
        Creates a new system configuration setting or updates an existing one (upsert).
        Args:
            config: The SystemConfiguration domain entity to create or update.
        Returns:
            The created or updated SystemConfiguration domain entity.
        """
        pass

    @abstractmethod
    async def get_all_configs(self) -> List['SystemConfiguration']:
        """
        Retrieves all system configuration settings.
        Returns:
            A list of SystemConfiguration domain entities.
        """
        pass

    # Optional future methods:
    # @abstractmethod
    # async def delete_config(self, key: str) -> bool:
    #     """Deletes a configuration setting by its key. Returns True if successful."""
    #     pass
