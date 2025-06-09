"""
Use cases for managing System Configuration settings.
These are typically administrative operations.
"""
from typing import Any, Optional, List
from datetime import datetime, timezone # Ensure timezone is imported for updated_at

from readmaster_ai.domain.entities.system_configuration import SystemConfiguration as DomainSystemConfiguration
from readmaster_ai.domain.repositories.system_configuration_repository import SystemConfigurationRepository
from readmaster_ai.application.dto.system_config_dtos import SystemConfigUpdateDTO # For update operation
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException # ApplicationException for general errors

class GetSystemConfigurationUseCase:
    """Use case to retrieve a specific system configuration setting by its key."""
    def __init__(self, config_repo: SystemConfigurationRepository):
        self.config_repo = config_repo

    async def execute(self, key: str) -> DomainSystemConfiguration: # Return Domain entity
        """
        Retrieves a system configuration.
        Args:
            key: The unique key of the configuration.
        Returns:
            The DomainSystemConfiguration entity.
        Raises:
            NotFoundException: If no configuration with the given key exists.
        """
        config = await self.config_repo.get_by_key(key)
        if not config:
            raise NotFoundException(resource_name="SystemConfiguration", resource_id=key)
        return config

class UpdateSystemConfigurationUseCase:
    """Use case to update (or create if not exists) a system configuration setting."""
    def __init__(self, config_repo: SystemConfigurationRepository):
        self.config_repo = config_repo

    async def execute(self, key: str, update_dto: SystemConfigUpdateDTO) -> DomainSystemConfiguration:
        """
        Updates or creates a system configuration setting.
        Args:
            key: The unique key of the configuration to update/create.
            update_dto: DTO containing the new value and optional description.
        Returns:
            The updated or created DomainSystemConfiguration entity.
        """
        # The repository's set_config method handles upsert logic.
        # We need to decide how to handle the description: if DTO's description is None,
        # should it clear an existing description or keep it?

        # Option 1: If DTO.description is None, keep existing (if any).
        # This requires fetching the current config first.
        current_config = await self.config_repo.get_by_key(key)

        new_description = update_dto.description
        if update_dto.description is None: # If explicitly set to None in DTO, it means clear it.
                                           # If not present in DTO (exclude_unset), then keep old.
                                           # Pydantic model_dump(exclude_unset=True) would handle this.
                                           # For now, assume if DTO field is None, it's intentional.
            if current_config and update_dto.model_fields_set.get("description") is None : # If description was not in request body
                 new_description = current_config.description


        # Construct the domain entity for setting/upserting
        config_to_set = DomainSystemConfiguration(
            key=key,
            value=update_dto.value, # The DTO ensures 'value' is provided
            description=new_description, # Use potentially preserved description
            updated_at=datetime.now(timezone.utc) # Use case sets/updates the timestamp
        )

        try:
            updated_config = await self.config_repo.set_config(config_to_set)
            return updated_config
        except Exception as e:
            # Log error e
            # This could be due to DB issues or other unexpected problems in repo.
            raise ApplicationException(f"Failed to update system configuration for key '{key}': {e}", status_code=500)

class ListSystemConfigurationsUseCase:
    """Use case to retrieve all system configuration settings."""
    def __init__(self, config_repo: SystemConfigurationRepository):
        self.config_repo = config_repo

    async def execute(self) -> List[DomainSystemConfiguration]:
        """
        Retrieves all system configurations.
        Returns:
            A list of DomainSystemConfiguration entities.
        """
        return await self.config_repo.get_all_configs()
