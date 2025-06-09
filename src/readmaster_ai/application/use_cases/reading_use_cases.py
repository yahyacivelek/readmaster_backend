"""
Use cases for managing Reading materials.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from readmaster_ai.domain.entities.reading import Reading as DomainReading
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.application.dto.reading_dtos import ReadingCreateDTO, ReadingUpdateDTO, ReadingResponseDTO
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel
from readmaster_ai.shared.exceptions import ApplicationException, NotFoundException

# New import for SystemConfigurationRepository
from readmaster_ai.domain.repositories.system_configuration_repository import SystemConfigurationRepository

DEFAULT_FALLBACK_LANGUAGE = "en" # Fallback if config not set or invalid
DEFAULT_LANGUAGE_CONFIG_KEY = "DEFAULT_READING_LANGUAGE"

class CreateReadingUseCase:
    """Use case for creating a new reading material."""
    def __init__(self,
                 reading_repo: ReadingRepository,
                 config_repo: Optional[SystemConfigurationRepository] = None): # Add config_repo, make optional
        self.reading_repo = reading_repo
        self.config_repo = config_repo # Store it

    async def execute(self, reading_data: ReadingCreateDTO, admin_user: DomainUser) -> DomainReading:
        """
        Executes the reading creation process.
        Args:
            reading_data: DTO containing data for the new reading.
            admin_user: The authenticated admin user performing the action.
        Returns:
            The created DomainReading entity.
        """
        effective_language = reading_data.language

        if not effective_language and self.config_repo: # If language not provided in DTO and repo is available
            try:
                default_lang_config = await self.config_repo.get_by_key(DEFAULT_LANGUAGE_CONFIG_KEY)
                if default_lang_config and isinstance(default_lang_config.value, str) and default_lang_config.value:
                    effective_language = default_lang_config.value
                    print(f"Using system default language: {effective_language} from config.")
                else:
                    effective_language = DEFAULT_FALLBACK_LANGUAGE
                    print(f"System default language config '{DEFAULT_LANGUAGE_CONFIG_KEY}' not found or invalid, using fallback: {effective_language}")
            except NotFoundException: # Key not found
                effective_language = DEFAULT_FALLBACK_LANGUAGE
                print(f"System default language config '{DEFAULT_LANGUAGE_CONFIG_KEY}' not found, using fallback: {effective_language}")
            except Exception as e: # Other errors fetching config
                print(f"Error fetching system default language config: {e}. Using fallback: {DEFAULT_FALLBACK_LANGUAGE}")
                effective_language = DEFAULT_FALLBACK_LANGUAGE
        elif not effective_language: # Language not in DTO and no config_repo provided
            effective_language = DEFAULT_FALLBACK_LANGUAGE
            print(f"Language not provided and no config repo, using fallback: {effective_language}")

        new_reading = DomainReading(
            reading_id=uuid4(),
            title=reading_data.title,
            content_text=reading_data.content_text,
            content_image_url=str(reading_data.content_image_url) if reading_data.content_image_url else None,
            age_category=reading_data.age_category,
            difficulty=reading_data.difficulty,
            language=effective_language, # Use the determined language
            genre=reading_data.genre,
            added_by_admin_id=admin_user.user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        created_reading = await self.reading_repo.create(new_reading)
        return created_reading

class GetReadingUseCase:
    """Use case for retrieving a single reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_id: UUID) -> Optional[DomainReading]: # Return type should be DomainReading, not Optional if raising NotFound
        reading = await self.reading_repo.get_by_id(reading_id)
        if not reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(reading_id))
        return reading

class ListReadingsUseCase:
    """Use case for listing reading materials with pagination and filters."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(
        self,
        page: int = 1,
        size: int = 20,
        language: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        age_category: Optional[str] = None
    ) -> Tuple[List[DomainReading], int]:
        return await self.reading_repo.list_all(
            page=page, size=size, language=language, difficulty=difficulty, age_category=age_category
        )

class UpdateReadingUseCase:
    """Use case for updating an existing reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_id: UUID, update_data: ReadingUpdateDTO, admin_user: DomainUser) -> DomainReading:
        existing_reading = await self.reading_repo.get_by_id(reading_id)
        if not existing_reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(reading_id))

        update_values = update_data.model_dump(exclude_unset=True)
        for key, value in update_values.items():
            if hasattr(existing_reading, key):
                if key == "content_image_url" and value is not None:
                    setattr(existing_reading, key, str(value))
                else:
                    setattr(existing_reading, key, value)

        existing_reading.updated_at = datetime.now(timezone.utc)

        updated_reading = await self.reading_repo.update(existing_reading)
        if not updated_reading:
             raise ApplicationException(f"Failed to update reading with ID {reading_id}.", status_code=500)
        return updated_reading

class DeleteReadingUseCase:
    """Use case for deleting a reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_id: UUID, admin_user: DomainUser) -> bool:
        existing_reading = await self.reading_repo.get_by_id(reading_id)
        if not existing_reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(reading_id))
        return await self.reading_repo.delete(reading_id)
