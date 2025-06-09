# tests/application/use_cases/test_system_config_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4 # Not strictly needed here, but often useful in tests
from datetime import datetime, timezone

from src.readmaster_ai.application.use_cases.system_config_use_cases import (
    GetSystemConfigurationUseCase, UpdateSystemConfigurationUseCase, ListSystemConfigurationsUseCase
)
from src.readmaster_ai.domain.entities.system_configuration import SystemConfiguration as DomainSystemConfig
from src.readmaster_ai.domain.repositories.system_configuration_repository import SystemConfigurationRepository
from src.readmaster_ai.application.dto.system_config_dtos import SystemConfigUpdateDTO
from src.readmaster_ai.shared.exceptions import NotFoundException

@pytest.fixture
def mock_config_repo() -> MagicMock: # Renamed to avoid conflict if running all tests together
    """Fixture for a mocked SystemConfigurationRepository."""
    mock = MagicMock(spec=SystemConfigurationRepository) # Use MagicMock for general spec
    # Make repository methods async mocks
    mock.get_by_key = AsyncMock(return_value=None) # Default: config not found
    mock.set_config = AsyncMock(side_effect=lambda cfg: cfg) # Default: returns the config passed to it
    mock.get_all_configs = AsyncMock(return_value=[]) # Default: empty list of configs
    return mock

@pytest.fixture
def sample_sys_config() -> DomainSystemConfig:
    """Fixture for a sample DomainSystemConfig object."""
    return DomainSystemConfig(
        key="TEST_CONFIG_KEY",
        value={"feature_enabled": True, "max_users": 1000},
        description="A sample test configuration setting.",
        updated_at=datetime.now(timezone.utc)
    )

# === GetSystemConfigurationUseCase Tests ===
@pytest.mark.asyncio
async def test_get_system_config_success(mock_config_repo: MagicMock, sample_sys_config: DomainSystemConfig):
    # Arrange
    mock_config_repo.get_by_key.return_value = sample_sys_config
    use_case = GetSystemConfigurationUseCase(config_repo=mock_config_repo)

    # Act
    config = await use_case.execute("TEST_CONFIG_KEY")

    # Assert
    mock_config_repo.get_by_key.assert_called_once_with("TEST_CONFIG_KEY")
    assert config == sample_sys_config
    assert config.value == {"feature_enabled": True, "max_users": 1000}

@pytest.mark.asyncio
async def test_get_system_config_not_found(mock_config_repo: MagicMock):
    # Arrange
    mock_config_repo.get_by_key.return_value = None # Simulate config not found
    use_case = GetSystemConfigurationUseCase(config_repo=mock_config_repo)

    non_existent_key = "NON_EXISTENT_KEY"
    # Act & Assert
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(non_existent_key)
    assert exc_info.value.resource_name == "SystemConfiguration"
    assert exc_info.value.resource_id == non_existent_key

# === UpdateSystemConfigurationUseCase Tests ===
@pytest.mark.asyncio
async def test_update_system_config_success_creating_new_key(mock_config_repo: MagicMock):
    # Arrange
    mock_config_repo.get_by_key.return_value = None # Simulate key does not exist initially
    # mock_config_repo.set_config is set to return the passed config object by default

    use_case = UpdateSystemConfigurationUseCase(config_repo=mock_config_repo)
    new_key = "NEW_FEATURE_FLAG"
    update_dto = SystemConfigUpdateDTO(value=True, description="Enable new experimental feature.")

    # Act
    updated_config = await use_case.execute(key=new_key, update_dto=update_dto)

    # Assert
    mock_config_repo.get_by_key.assert_called_once_with(new_key) # Called to check if exists
    mock_config_repo.set_config.assert_called_once()

    call_args = mock_config_repo.set_config.call_args[0][0] # Get the DomainSystemConfig object passed to set_config
    assert isinstance(call_args, DomainSystemConfig)
    assert call_args.key == new_key
    assert call_args.value is True
    assert call_args.description == "Enable new experimental feature."

    assert updated_config.value is True # Check returned object from use case

@pytest.mark.asyncio
async def test_update_system_config_success_updating_existing_key(mock_config_repo: MagicMock, sample_sys_config: DomainSystemConfig):
    # Arrange
    mock_config_repo.get_by_key.return_value = sample_sys_config # Simulate key exists

    use_case = UpdateSystemConfigurationUseCase(config_repo=mock_config_repo)
    # Update only the value, description should be preserved by use case logic
    update_dto = SystemConfigUpdateDTO(value="new_value_for_key")
                                     # description is None in DTO, so old one should be kept

    original_description = sample_sys_config.description
    original_updated_at = sample_sys_config.updated_at

    # Act
    updated_config = await use_case.execute(key=sample_sys_config.key, update_dto=update_dto)

    # Assert
    mock_config_repo.get_by_key.assert_called_once_with(sample_sys_config.key)
    mock_config_repo.set_config.assert_called_once()

    call_args = mock_config_repo.set_config.call_args[0][0]
    assert call_args.value == "new_value_for_key"
    assert call_args.description == original_description # Description should be preserved
    assert call_args.updated_at > original_updated_at # Timestamp should be updated by use case

    assert updated_config.value == "new_value_for_key"
    assert updated_config.description == original_description

@pytest.mark.asyncio
async def test_update_system_config_explicitly_clearing_description(mock_config_repo: MagicMock, sample_sys_config: DomainSystemConfig):
    # Arrange
    mock_config_repo.get_by_key.return_value = sample_sys_config
    use_case = UpdateSystemConfigurationUseCase(config_repo=mock_config_repo)
    # Update value and explicitly set description to an empty string (or None if DTO allows clearing that way)
    update_dto = SystemConfigUpdateDTO(value={"cleared": True}, description="")

    # Act
    updated_config = await use_case.execute(key=sample_sys_config.key, update_dto=update_dto)

    # Assert
    call_args = mock_config_repo.set_config.call_args[0][0]
    assert call_args.description == "" # Description should be updated to empty string
    assert updated_config.description == ""


# === ListSystemConfigurationsUseCase Tests ===
@pytest.mark.asyncio
async def test_list_system_configs_success(mock_config_repo: MagicMock, sample_sys_config: DomainSystemConfig):
    # Arrange
    mock_config_repo.get_all_configs.return_value = [sample_sys_config] # Simulate one config item
    use_case = ListSystemConfigurationsUseCase(config_repo=mock_config_repo)

    # Act
    configs = await use_case.execute()

    # Assert
    mock_config_repo.get_all_configs.assert_called_once()
    assert len(configs) == 1
    assert configs[0] == sample_sys_config

@pytest.mark.asyncio
async def test_list_system_configs_empty(mock_config_repo: MagicMock):
    # Arrange
    mock_config_repo.get_all_configs.return_value = [] # Simulate no configs
    use_case = ListSystemConfigurationsUseCase(config_repo=mock_config_repo)

    # Act
    configs = await use_case.execute()

    # Assert
    assert len(configs) == 0
