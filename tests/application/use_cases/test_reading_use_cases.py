# tests/application/use_cases/test_reading_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, ANY # ANY for comparing objects partially
from uuid import uuid4, UUID
from datetime import datetime, timezone

from readmaster_ai.application.use_cases.reading_use_cases import (
    CreateReadingUseCase, GetReadingUseCase, ListReadingsUseCase,
    UpdateReadingUseCase, DeleteReadingUseCase
)
from readmaster_ai.domain.entities.reading import Reading as DomainReading
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel as DifficultyLevelEnum # Use centralized
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # For admin_user
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.system_configuration_repository import SystemConfigurationRepository # For CreateReading
from readmaster_ai.domain.entities.system_configuration import SystemConfiguration as DomainSystemConfig
from readmaster_ai.application.dto.reading_dtos import ReadingCreateDTO, ReadingUpdateDTO
from readmaster_ai.shared.exceptions import NotFoundException


@pytest.fixture
def mock_reading_repo() -> MagicMock:
    """Fixture for a mocked ReadingRepository."""
    mock = MagicMock(spec=ReadingRepository) # Use MagicMock for general spec
    # Make repository methods async mocks
    mock.create = AsyncMock(side_effect=lambda reading: reading) # Default: returns the reading passed
    mock.get_by_id = AsyncMock(return_value=None) # Default: not found
    mock.update = AsyncMock(side_effect=lambda reading: reading) # Default: returns updated reading
    mock.delete = AsyncMock(return_value=True) # Default: delete successful
    mock.list_all = AsyncMock(return_value=([], 0)) # Default: empty list and zero total count
    return mock

@pytest.fixture
def mock_config_repo() -> MagicMock:
    """Fixture for a mocked SystemConfigurationRepository, used by CreateReadingUseCase."""
    mock = MagicMock(spec=SystemConfigurationRepository)
    # Default behavior: config key for default language not found
    mock.get_by_key = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def sample_admin_user() -> DomainUser:
    """Fixture for a sample admin DomainUser."""
    return DomainUser(
        user_id=uuid4(),
        email="admin.readingtests@example.com",
        password_hash="admin_hash", # Not used by these use cases directly
        role=UserRole.ADMIN
    )

@pytest.fixture
def sample_reading_domain(sample_admin_user: DomainUser) -> DomainReading:
    """Fixture for a sample DomainReading object."""
    return DomainReading(
        reading_id=uuid4(),
        title="Sample Reading Title",
        content_text="This is some sample content for the reading.",
        language="en",
        difficulty=DifficultyLevelEnum.INTERMEDIATE,
        added_by_admin_id=sample_admin_user.user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# === CreateReadingUseCase Tests ===
@pytest.mark.asyncio
async def test_create_reading_success(mock_reading_repo: MagicMock, mock_config_repo: MagicMock, sample_admin_user: DomainUser):
    use_case = CreateReadingUseCase(reading_repo=mock_reading_repo, config_repo=mock_config_repo)
    create_dto = ReadingCreateDTO(
        title="New Awesome Reading",
        content_text="Exciting content here.",
        language="fr", # Language explicitly provided
        difficulty=DifficultyLevelEnum.BEGINNER
    )

    created_reading = await use_case.execute(create_dto, sample_admin_user)

    mock_reading_repo.create.assert_called_once()
    # Get the DomainReading object passed to repo.create
    call_args = mock_reading_repo.create.call_args[0][0]
    assert isinstance(call_args, DomainReading)
    assert call_args.title == "New Awesome Reading"
    assert call_args.language == "fr" # Language from DTO should be used
    assert call_args.difficulty == DifficultyLevelEnum.BEGINNER
    assert call_args.added_by_admin_id == sample_admin_user.user_id

    assert created_reading.title == "New Awesome Reading" # Check returned object

@pytest.mark.asyncio
async def test_create_reading_uses_default_lang_from_config(mock_reading_repo: MagicMock, mock_config_repo: MagicMock, sample_admin_user: DomainUser):
    # Simulate config repo returning a default language
    mock_config_repo.get_by_key.return_value = DomainSystemConfig(
        key="DEFAULT_READING_LANGUAGE", value="es", description="Default Spanish"
    )
    use_case = CreateReadingUseCase(reading_repo=mock_reading_repo, config_repo=mock_config_repo)
    # Language is NOT provided in DTO, so config should be used
    create_dto = ReadingCreateDTO(title="Config Language Reading", content_text="Content in Spanish.", difficulty=DifficultyLevelEnum.EASY)

    created_reading = await use_case.execute(create_dto, sample_admin_user)

    mock_config_repo.get_by_key.assert_called_once_with("DEFAULT_READING_LANGUAGE")
    assert created_reading.language == "es" # Language from config

@pytest.mark.asyncio
async def test_create_reading_uses_fallback_lang_if_config_missing(mock_reading_repo: MagicMock, mock_config_repo: MagicMock, sample_admin_user: DomainUser):
    # Config repo returns None (default mock behavior for get_by_key)
    use_case = CreateReadingUseCase(reading_repo=mock_reading_repo, config_repo=mock_config_repo)
    # Language is NOT provided in DTO
    create_dto = ReadingCreateDTO(title="Fallback Language Reading", difficulty=DifficultyLevelEnum.INTERMEDIATE)

    created_reading = await use_case.execute(create_dto, sample_admin_user)

    mock_config_repo.get_by_key.assert_called_once_with("DEFAULT_READING_LANGUAGE")
    assert created_reading.language == "en" # Default fallback "en" from use case

# === GetReadingUseCase Tests ===
@pytest.mark.asyncio
async def test_get_reading_success(mock_reading_repo: MagicMock, sample_reading_domain: DomainReading):
    mock_reading_repo.get_by_id.return_value = sample_reading_domain
    use_case = GetReadingUseCase(reading_repo=mock_reading_repo)

    reading = await use_case.execute(sample_reading_domain.reading_id)

    mock_reading_repo.get_by_id.assert_called_once_with(sample_reading_domain.reading_id)
    assert reading == sample_reading_domain # Check if the correct domain object is returned

@pytest.mark.asyncio
async def test_get_reading_not_found(mock_reading_repo: MagicMock):
    mock_reading_repo.get_by_id.return_value = None # Simulate reading not found
    use_case = GetReadingUseCase(reading_repo=mock_reading_repo)

    non_existent_id = uuid4()
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(non_existent_id)
    assert str(non_existent_id) in exc_info.value.message
    assert "Reading" in exc_info.value.message

# === ListReadingsUseCase Tests ===
@pytest.mark.asyncio
async def test_list_readings_success(mock_reading_repo: MagicMock, sample_reading_domain: DomainReading):
    # Simulate repository returning a list with one reading and total count of 1
    mock_reading_repo.list_all.return_value = ([sample_reading_domain], 1)
    use_case = ListReadingsUseCase(reading_repo=mock_reading_repo)

    # Call use case with some example filter parameters
    readings, total = await use_case.execute(page=1, size=10, language="en", difficulty=DifficultyLevelEnum.INTERMEDIATE)

    # Assert that the repository's list_all method was called with the correct parameters
    mock_reading_repo.list_all.assert_called_once_with(
        page=1, size=10, language="en", difficulty=DifficultyLevelEnum.INTERMEDIATE, age_category=None
    )
    assert len(readings) == 1
    assert total == 1
    assert readings[0] == sample_reading_domain

# === UpdateReadingUseCase Tests ===
@pytest.mark.asyncio
async def test_update_reading_success(mock_reading_repo: MagicMock, sample_reading_domain: DomainReading, sample_admin_user: DomainUser):
    # Simulate get_by_id returning the existing reading
    mock_reading_repo.get_by_id.return_value = sample_reading_domain
    # The mock_reading_repo.update already returns the passed object by default (side_effect=lambda reading: reading)

    use_case = UpdateReadingUseCase(reading_repo=mock_reading_repo)
    update_dto = ReadingUpdateDTO(title="Updated Reading Title", language="es")

    # Create a copy for the use case to modify, to avoid altering fixture state directly if it's mutable
    # For domain entities, if they are simple data classes, direct use might be okay,
    # but copying is safer if methods modify state.
    # In this use case, attributes are set on the fetched existing_reading.

    original_updated_at = sample_reading_domain.updated_at

    updated_reading = await use_case.execute(
        reading_id=sample_reading_domain.reading_id,
        update_data=update_dto,
        admin_user=sample_admin_user # admin_user is for potential auth checks not yet in UC
    )

    mock_reading_repo.get_by_id.assert_called_once_with(sample_reading_domain.reading_id)
    mock_reading_repo.update.assert_called_once()

    # Get the DomainReading object that was passed to repo.update
    updated_reading_arg_to_repo = mock_reading_repo.update.call_args[0][0]
    assert updated_reading_arg_to_repo.title == "Updated Reading Title"
    assert updated_reading_arg_to_repo.language == "es"
    assert updated_reading_arg_to_repo.updated_at > original_updated_at # Check timestamp updated

    assert updated_reading.title == "Updated Reading Title" # Check returned object

@pytest.mark.asyncio
async def test_update_reading_not_found(mock_reading_repo: MagicMock, sample_admin_user: DomainUser):
    mock_reading_repo.get_by_id.return_value = None # Simulate reading not found
    use_case = UpdateReadingUseCase(reading_repo=mock_reading_repo)
    update_dto = ReadingUpdateDTO(title="A New Title")

    non_existent_id = uuid4()
    with pytest.raises(NotFoundException):
        await use_case.execute(non_existent_id, update_dto, sample_admin_user)
    mock_reading_repo.update.assert_not_called() # Ensure update was not called

# === DeleteReadingUseCase Tests ===
@pytest.mark.asyncio
async def test_delete_reading_success(mock_reading_repo: MagicMock, sample_reading_domain: DomainReading, sample_admin_user: DomainUser):
    mock_reading_repo.get_by_id.return_value = sample_reading_domain # Simulate reading exists
    mock_reading_repo.delete.return_value = True # Simulate delete successful

    use_case = DeleteReadingUseCase(reading_repo=mock_reading_repo)

    result = await use_case.execute(sample_reading_domain.reading_id, sample_admin_user) # Pass admin_user

    mock_reading_repo.get_by_id.assert_called_once_with(sample_reading_domain.reading_id)
    mock_reading_repo.delete.assert_called_once_with(sample_reading_domain.reading_id)
    assert result is True

@pytest.mark.asyncio
async def test_delete_reading_not_found(mock_reading_repo: MagicMock, sample_admin_user: DomainUser):
    mock_reading_repo.get_by_id.return_value = None # Simulate reading not found
    use_case = DeleteReadingUseCase(reading_repo=mock_reading_repo)

    non_existent_id = uuid4()
    with pytest.raises(NotFoundException):
        await use_case.execute(non_existent_id, sample_admin_user) # Pass admin_user
    mock_reading_repo.delete.assert_not_called() # Ensure delete was not called
