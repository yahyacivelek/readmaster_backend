# tests/infrastructure/database/repositories/test_reading_repository.py
import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from readmaster_ai.domain.entities.reading import Reading as DomainReading
# Use the centralized enum for consistency in tests
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel as DifficultyLevelEnum
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # To create admin user
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # To create admin user
from readmaster_ai.shared.exceptions import ApplicationException # For testing error cases if any

@pytest_asyncio.fixture(scope="function")
async def admin_user_for_readings(db_session: AsyncSession) -> DomainUser:
    """Fixture to create a dedicated admin user for reading tests."""
    user_repo = UserRepositoryImpl(db_session)
    admin_id = uuid4()
    admin_email = f"admin_readings_{admin_id}@example.com"
    # Check if user already exists to handle potential re-runs if DB is not fully clean (though conftest should handle it)
    existing_admin = await user_repo.get_by_email(admin_email)
    if existing_admin:
        return existing_admin

    admin = DomainUser(
        user_id=admin_id, email=admin_email,
        password_hash="admin_password_hash", # Hashing not critical for this test's focus
        role=UserRole.ADMIN,
        first_name="Admin", last_name="Readings"
    )
    created_admin = await user_repo.create(admin)
    return created_admin

@pytest.mark.asyncio
async def test_create_reading(db_session: AsyncSession, admin_user_for_readings: DomainUser):
    repo = ReadingRepositoryImpl(db_session)
    reading_id = uuid4()
    current_time = datetime.now(timezone.utc)
    domain_reading = DomainReading(
        reading_id=reading_id,
        title="The Little Prince",
        content_text="Once upon a time...",
        language="en",
        difficulty=DifficultyLevelEnum.BEGINNER,
        added_by_admin_id=admin_user_for_readings.user_id,
        created_at=current_time,
        updated_at=current_time
    )
    created_reading = await repo.create(domain_reading)
    assert created_reading is not None
    assert created_reading.reading_id == reading_id
    assert created_reading.title == "The Little Prince"
    assert created_reading.difficulty == DifficultyLevelEnum.BEGINNER
    assert created_reading.added_by_admin_id == admin_user_for_readings.user_id

@pytest.mark.asyncio
async def test_get_reading_by_id(db_session: AsyncSession, admin_user_for_readings: DomainUser):
    repo = ReadingRepositoryImpl(db_session)
    reading_id = uuid4()
    new_reading = DomainReading(
        reading_id=reading_id,
        title="Test Get Reading",
        added_by_admin_id=admin_user_for_readings.user_id,
        language="en" # Ensure mandatory fields in domain entity are provided
    )
    await repo.create(new_reading)

    retrieved = await repo.get_by_id(reading_id)
    assert retrieved is not None
    assert retrieved.reading_id == reading_id
    assert retrieved.title == "Test Get Reading"

@pytest.mark.asyncio
async def test_get_reading_by_id_not_found(db_session: AsyncSession):
    repo = ReadingRepositoryImpl(db_session)
    retrieved = await repo.get_by_id(uuid4())
    assert retrieved is None

@pytest.mark.asyncio
async def test_list_all_readings_empty(db_session: AsyncSession):
    repo = ReadingRepositoryImpl(db_session)
    readings, total_count = await repo.list_all()
    assert len(readings) == 0
    assert total_count == 0

@pytest.mark.asyncio
async def test_list_all_readings_with_data_and_filters(db_session: AsyncSession, admin_user_for_readings: DomainUser):
    repo = ReadingRepositoryImpl(db_session)

    r1 = DomainReading(uuid4(), "English Easy Reading", language="en", difficulty=DifficultyLevelEnum.BEGINNER, added_by_admin_id=admin_user_for_readings.user_id, age_category="6-8")
    r2 = DomainReading(uuid4(), "Spanish Easy Reading", language="es", difficulty=DifficultyLevelEnum.BEGINNER, added_by_admin_id=admin_user_for_readings.user_id, age_category="6-8")
    r3 = DomainReading(uuid4(), "English Hard Reading", language="en", difficulty=DifficultyLevelEnum.ADVANCED, added_by_admin_id=admin_user_for_readings.user_id, age_category="9-12")

    await repo.create(r1)
    await repo.create(r2)
    await repo.create(r3)

    # Test no filters (should get all 3)
    all_readings, total_all = await repo.list_all()
    assert total_all == 3

    # Test filter by language
    en_readings, en_total = await repo.list_all(language="en")
    assert en_total == 2
    assert all(r.language == "en" for r in en_readings)

    # Test filter by difficulty
    easy_readings, easy_total = await repo.list_all(difficulty=DifficultyLevelEnum.BEGINNER)
    assert easy_total == 2
    assert all(r.difficulty == DifficultyLevelEnum.BEGINNER for r in easy_readings)

    # Test filter by age_category
    age_6_8_readings, age_6_8_total = await repo.list_all(age_category="6-8")
    assert age_6_8_total == 2
    assert all(r.age_category == "6-8" for r in age_6_8_readings)

    # Test filter by language and difficulty
    en_hard, en_hard_total = await repo.list_all(language="en", difficulty=DifficultyLevelEnum.ADVANCED)
    assert en_hard_total == 1
    assert en_hard[0].title == "English Hard Reading"

    # Test pagination
    page1_size2, total_p1s2 = await repo.list_all(page=1, size=2)
    assert len(page1_size2) == 2
    assert total_p1s2 == 3

    page2_size2, total_p2s2 = await repo.list_all(page=2, size=2)
    assert len(page2_size2) == 1 # Only one remaining on the second page
    assert total_p2s2 == 3

@pytest.mark.asyncio
async def test_update_reading(db_session: AsyncSession, admin_user_for_readings: DomainUser):
    repo = ReadingRepositoryImpl(db_session)
    reading_id = uuid4()
    orig_reading = DomainReading(
        reading_id=reading_id, title="Original Title", language="fr",
        added_by_admin_id=admin_user_for_readings.user_id,
        difficulty=DifficultyLevelEnum.INTERMEDIATE
    )
    await repo.create(orig_reading)

    to_update = await repo.get_by_id(reading_id)
    assert to_update is not None

    to_update.title = "Updated Title"
    to_update.language = "de"
    to_update.difficulty = DifficultyLevelEnum.ADVANCED
    to_update.updated_at = datetime.now(timezone.utc) # Domain entity should handle this, but repo impl uses it

    updated_reading = await repo.update(to_update)
    assert updated_reading is not None
    assert updated_reading.title == "Updated Title"
    assert updated_reading.language == "de"
    assert updated_reading.difficulty == DifficultyLevelEnum.ADVANCED

    # Verify by fetching again
    refetched = await repo.get_by_id(reading_id)
    assert refetched is not None
    assert refetched.title == "Updated Title"

@pytest.mark.asyncio
async def test_update_non_existent_reading(db_session: AsyncSession, admin_user_for_readings: DomainUser):
    repo = ReadingRepositoryImpl(db_session)
    non_existent_id = uuid4()
    reading_update_data = DomainReading(
        reading_id=non_existent_id, title="Non Existent", language="en",
        added_by_admin_id=admin_user_for_readings.user_id # This field is not updated by repo.update
    )
    # The repo.update method returns Optional[DomainReading], None if not found for update.
    updated_reading = await repo.update(reading_update_data)
    assert updated_reading is None


@pytest.mark.asyncio
async def test_delete_reading(db_session: AsyncSession, admin_user_for_readings: DomainUser):
    repo = ReadingRepositoryImpl(db_session)
    reading_id = uuid4()
    await repo.create(DomainReading(reading_id=reading_id, title="To Be Deleted", added_by_admin_id=admin_user_for_readings.user_id))

    # Ensure it exists before delete
    assert await repo.get_by_id(reading_id) is not None

    deleted_success = await repo.delete(reading_id)
    assert deleted_success is True

    # Verify it's gone
    assert await repo.get_by_id(reading_id) is None

@pytest.mark.asyncio
async def test_delete_non_existent_reading(db_session: AsyncSession):
    repo = ReadingRepositoryImpl(db_session)
    non_existent_id = uuid4()
    deleted_success = await repo.delete(non_existent_id)
    assert deleted_success is False
