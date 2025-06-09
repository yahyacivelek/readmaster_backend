"""
Use cases for managing Reading materials.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List, Tuple # For list_all return type

from readmaster_ai.domain.entities.reading import Reading as DomainReading
from readmaster_ai.domain.entities.user import DomainUser # For admin_id context
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.application.dto.reading_dtos import ReadingCreateDTO, ReadingUpdateDTO, ReadingResponseDTO # ReadingResponseDTO for return types
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel # For type hinting if needed
from readmaster_ai.shared.exceptions import ApplicationException, NotFoundException


class CreateReadingUseCase:
    """Use case for creating a new reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_data: ReadingCreateDTO, admin_user: DomainUser) -> DomainReading:
        """
        Executes the reading creation process.
        Args:
            reading_data: DTO containing data for the new reading.
            admin_user: The authenticated admin user performing the action.
        Returns:
            The created DomainReading entity.
        """
        new_reading = DomainReading(
            reading_id=uuid4(), # Application generates ID
            title=reading_data.title,
            content_text=reading_data.content_text,
            content_image_url=str(reading_data.content_image_url) if reading_data.content_image_url else None, # Ensure HttpUrl is stringified
            age_category=reading_data.age_category,
            difficulty=reading_data.difficulty, # DTO should already use the Enum
            language=reading_data.language,
            genre=reading_data.genre,
            added_by_admin_id=admin_user.user_id, # Set admin ID from context
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        created_reading = await self.reading_repo.create(new_reading)
        return created_reading

class GetReadingUseCase:
    """Use case for retrieving a single reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_id: UUID) -> Optional[DomainReading]:
        """
        Executes the reading retrieval process.
        Args:
            reading_id: The ID of the reading to retrieve.
        Returns:
            The DomainReading entity if found, otherwise None.
        """
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
        """
        Executes the reading listing process.
        Args:
            page: Page number for pagination.
            size: Number of items per page.
            language: Filter by language.
            difficulty: Filter by difficulty level.
            age_category: Filter by age category.
        Returns:
            A tuple containing a list of DomainReading entities and the total count of matching readings.
        """
        return await self.reading_repo.list_all(
            page=page, size=size, language=language, difficulty=difficulty, age_category=age_category
        )

class UpdateReadingUseCase:
    """Use case for updating an existing reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_id: UUID, update_data: ReadingUpdateDTO, admin_user: DomainUser) -> DomainReading:
        """
        Executes the reading update process.
        Args:
            reading_id: ID of the reading to update.
            update_data: DTO containing updated data.
            admin_user: The authenticated admin user.
        Returns:
            The updated DomainReading entity.
        Raises:
            NotFoundException: If the reading is not found.
            ApplicationException: If the update fails.
        """
        existing_reading = await self.reading_repo.get_by_id(reading_id)
        if not existing_reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(reading_id))

        # Optionally: Check if admin_user is authorized to update this reading.
        # (e.g., if existing_reading.added_by_admin_id != admin_user.user_id and admin_user.role != UserRole.ADMIN)
        # This depends on business rules for "super admin" vs "creator admin".

        update_values = update_data.model_dump(exclude_unset=True)
        for key, value in update_values.items():
            if hasattr(existing_reading, key):
                # Special handling for HttpUrl to str if needed by domain entity upon update
                if key == "content_image_url" and value is not None:
                    setattr(existing_reading, key, str(value))
                else:
                    setattr(existing_reading, key, value)

        existing_reading.updated_at = datetime.now(timezone.utc)

        updated_reading = await self.reading_repo.update(existing_reading)
        if not updated_reading:
             # This implies the update failed at the repository level after finding the entity.
             raise ApplicationException(f"Failed to update reading with ID {reading_id}.", status_code=500)
        return updated_reading

class DeleteReadingUseCase:
    """Use case for deleting a reading material."""
    def __init__(self, reading_repo: ReadingRepository):
        self.reading_repo = reading_repo

    async def execute(self, reading_id: UUID, admin_user: DomainUser) -> bool:
        """
        Executes the reading deletion process.
        Args:
            reading_id: ID of the reading to delete.
            admin_user: The authenticated admin user.
        Returns:
            True if deletion was successful, False otherwise.
        Raises:
            NotFoundException: If the reading is not found.
        """
        existing_reading = await self.reading_repo.get_by_id(reading_id)
        if not existing_reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(reading_id))

        # Optionally: Check authorization for deletion.

        return await self.reading_repo.delete(reading_id)
