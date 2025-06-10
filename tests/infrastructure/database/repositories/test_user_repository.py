# tests/infrastructure/database/repositories/test_user_repository.py
import pytest
import pytest_asyncio # For async fixtures
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone # Ensure timezone is imported

from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # Correct import for UserRole enum
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from readmaster_ai.infrastructure.database.models import UserModel # For direct verification if needed
from readmaster_ai.shared.exceptions import NotFoundException # For testing link_parent_to_student

# Fixtures from conftest.py like db_session and test_user will be automatically available.

@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    repo = UserRepositoryImpl(db_session)
    user_id = uuid4()
    domain_user = DomainUser(
        user_id=user_id,
        email="create.test@example.com",
        password_hash="hashed_password", # Actual hashing is done by use case / service
        first_name="Create",
        last_name="Test",
        role=UserRole.STUDENT, # Use the imported enum
        created_at=datetime.now(timezone.utc), # Set explicitly or let domain entity default
        updated_at=datetime.now(timezone.utc)
    )
    created_user = await repo.create(domain_user)
    assert created_user is not None
    assert created_user.user_id == user_id
    assert created_user.email == "create.test@example.com"
    assert created_user.role == UserRole.STUDENT

    # Optional: verify directly in DB
    # model = await db_session.get(UserModel, user_id)
    # await db_session.refresh(model) # Ensure all attributes are loaded
    # assert model is not None
    # assert model.email == "create.test@example.com"
    # assert UserRole(model.role) == UserRole.STUDENT

@pytest.mark.asyncio
async def test_get_user_by_id(db_session: AsyncSession, test_user: DomainUser): # test_user fixture from conftest.py
    repo = UserRepositoryImpl(db_session)
    retrieved_user = await repo.get_by_id(test_user.user_id)
    assert retrieved_user is not None
    assert retrieved_user.user_id == test_user.user_id
    assert retrieved_user.email == test_user.email
    assert retrieved_user.role == test_user.role

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(db_session: AsyncSession):
    repo = UserRepositoryImpl(db_session)
    retrieved_user = await repo.get_by_id(uuid4()) # Random non-existent UUID
    assert retrieved_user is None

@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession, test_user: DomainUser):
    repo = UserRepositoryImpl(db_session)
    retrieved_user = await repo.get_by_email(test_user.email)
    assert retrieved_user is not None
    assert retrieved_user.user_id == test_user.user_id
    assert retrieved_user.email == test_user.email

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(db_session: AsyncSession):
    repo = UserRepositoryImpl(db_session)
    retrieved_user = await repo.get_by_email("nonexistent.email@example.com")
    assert retrieved_user is None

@pytest.mark.asyncio
async def test_update_user(db_session: AsyncSession, test_user: DomainUser):
    repo = UserRepositoryImpl(db_session)

    # Modify domain entity attributes for update
    test_user.first_name = "UpdatedFirstName"
    test_user.preferred_language = "es"
    test_user.updated_at = datetime.now(timezone.utc) # Important to update this for onupdate triggers/logic

    updated_user_domain = await repo.update(test_user)

    assert updated_user_domain is not None
    assert updated_user_domain.user_id == test_user.user_id
    assert updated_user_domain.first_name == "UpdatedFirstName"
    assert updated_user_domain.preferred_language == "es"

    # Verify the update by fetching again
    refetched_user_domain = await repo.get_by_id(test_user.user_id)
    assert refetched_user_domain is not None
    assert refetched_user_domain.first_name == "UpdatedFirstName"
    assert refetched_user_domain.preferred_language == "es"
    # Check if updated_at was indeed updated (it should be close to now)
    assert (datetime.now(timezone.utc) - refetched_user_domain.updated_at).total_seconds() < 5

@pytest.mark.asyncio
async def test_link_parent_to_student_and_verify(db_session: AsyncSession):
    repo = UserRepositoryImpl(db_session)

    parent_id = uuid4()
    parent_user = DomainUser(user_id=parent_id, email=f"parent.link.{parent_id}@example.com", password_hash="p", role=UserRole.PARENT)
    await repo.create(parent_user)

    student_id = uuid4()
    student_user = DomainUser(user_id=student_id, email=f"student.link.{student_id}@example.com", password_hash="s", role=UserRole.STUDENT)
    await repo.create(student_user)

    relationship = "Mother"
    link_success = await repo.link_parent_to_student(parent_id, student_id, relationship)
    assert link_success is True

    is_linked = await repo.is_parent_of_student(parent_id, student_id)
    assert is_linked is True

    children = await repo.list_children_by_parent_id(parent_id)
    assert len(children) == 1
    assert children[0].user_id == student_id
    assert children[0].email == f"student.link.{student_id}@example.com"

    # Test linking again (should be idempotent)
    link_again_success = await repo.link_parent_to_student(parent_id, student_id, "Father") # Diff relationship type
    assert link_again_success is True # Still true, as link exists (repo does not update type for now)

@pytest.mark.asyncio
async def test_is_parent_of_student_not_linked(db_session: AsyncSession, test_user: DomainUser):
    repo = UserRepositoryImpl(db_session)
    random_parent_id = uuid4()
    is_linked = await repo.is_parent_of_student(random_parent_id, test_user.user_id)
    assert is_linked is False

@pytest.mark.asyncio
async def test_link_parent_to_non_student_raises_error(db_session: AsyncSession):
    repo = UserRepositoryImpl(db_session)
    parent = await repo.create(DomainUser(user_id=uuid4(), email="p1.error@example.com", password_hash="p", role=UserRole.PARENT))
    not_a_student = await repo.create(DomainUser(user_id=uuid4(), email="t1.error@example.com", password_hash="p", role=UserRole.TEACHER))

    with pytest.raises(NotFoundException, match=f"Student user with ID '{not_a_student.user_id}' not found."):
        await repo.link_parent_to_student(parent.user_id, not_a_student.user_id, "guardian")

@pytest.mark.asyncio
async def test_link_non_parent_to_student_raises_error(db_session: AsyncSession, test_user: DomainUser):
    repo = UserRepositoryImpl(db_session)
    not_a_parent = await repo.create(DomainUser(user_id=uuid4(), email="t2.error@example.com", password_hash="p", role=UserRole.TEACHER))

    with pytest.raises(NotFoundException, match=f"Parent user with ID '{not_a_parent.user_id}' not found."):
        await repo.link_parent_to_student(not_a_parent.user_id, test_user.user_id, "guardian")


@pytest.mark.asyncio
async def test_list_children_no_children(db_session: AsyncSession):
    repo = UserRepositoryImpl(db_session)
    parent = await repo.create(DomainUser(user_id=uuid4(), email="p2.nochildren@example.com", password_hash="p", role=UserRole.PARENT))
    children = await repo.list_children_by_parent_id(parent.user_id)
    assert len(children) == 0
