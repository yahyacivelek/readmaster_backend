import pytest
import uuid
from unittest.mock import AsyncMock, patch

from readmaster_ai.application.use_cases.parent_use_cases import CreateStudentByParentUseCase
from readmaster_ai.presentation.schemas.user_schemas import ParentChildCreateRequestSchema
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.shared.exceptions import ApplicationException, ForbiddenException
# Assuming pwd_context is accessible for checking hash, or mock it if it's complex
# from readmaster_ai.application.use_cases.user_use_cases import pwd_context


@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def parent_user():
    return DomainUser(
        user_id=uuid.uuid4(),
        email="parent@example.com",
        role=UserRole.PARENT,
        password_hash="parent_hashed_password" # Actual hash not important for this test
    )

@pytest.fixture
def child_create_data():
    return ParentChildCreateRequestSchema(
        email="child@example.com",
        password="child_password",
        first_name="Child",
        last_name="User",
        preferred_language="en"
        # role is fixed to "student" in the schema
    )

@pytest.mark.asyncio
async def test_create_student_by_parent_success(mock_user_repo, parent_user, child_create_data):
    use_case = CreateStudentByParentUseCase(user_repo=mock_user_repo)

    mock_user_repo.get_by_email.return_value = None # No existing user with this email

    # Mock the created student user that repo.create would return
    created_student_id = uuid.uuid4()
    # We need to capture the DomainUser passed to create to check its attributes
    # For simplicity, we'll assume repo.create returns a user with the generated ID and data
    # and that link_parent_to_student succeeds.

    async def mock_create_user(user: DomainUser):
        # Simulate DB setting the ID if it wasn't passed or just return the input user
        # For this test, let's assume the use case generates the ID.
        assert user.email == child_create_data.email
        assert user.role == UserRole.STUDENT
        # In a real scenario, you'd check pwd_context.verify("child_password", user.password_hash)
        # For now, just check it's not plain password
        assert user.password_hash != child_create_data.password
        user.user_id = created_student_id # Ensure it has an ID for linking
        return user

    mock_user_repo.create.side_effect = mock_create_user
    mock_user_repo.link_parent_to_student.return_value = True # Assume linking is successful

    # Patch uuid.uuid4 used inside the use case to control the generated student_id
    # This is tricky because uuid4 is called inside DomainUser's init if no ID is passed,
    # and also potentially by the use case if it were to generate ID explicitly.
    # The current use case relies on DomainUser's default ID generation.
    # Let's assume the DomainUser created inside the use case will have a generated ID.

    with patch('uuid.uuid4', return_value=created_student_id): # If DomainUser init is patched
        result_student = await use_case.execute(parent_user=parent_user, child_data=child_create_data)

    mock_user_repo.get_by_email.assert_called_once_with(child_create_data.email)
    mock_user_repo.create.assert_called_once()
    # args, _ = mock_user_repo.create.call_args
    # created_user_arg = args[0]
    # assert created_user_arg.email == child_create_data.email
    # assert created_user_arg.role == UserRole.STUDENT
    # assert created_user_arg.password_hash != child_create_data.password # Check it's hashed

    mock_user_repo.link_parent_to_student.assert_called_once_with(
        parent_id=parent_user.user_id,
        student_id=created_student_id, # This needs to be the ID of the student *as created*
        relationship_type="parent"
    )

    assert result_student is not None
    assert result_student.email == child_create_data.email
    assert result_student.role == UserRole.STUDENT
    assert result_student.user_id == created_student_id

@pytest.mark.asyncio
async def test_create_student_by_parent_email_exists(mock_user_repo, parent_user, child_create_data):
    use_case = CreateStudentByParentUseCase(user_repo=mock_user_repo)
    mock_user_repo.get_by_email.return_value = DomainUser(email="child@example.com", role=UserRole.STUDENT) # Existing user

    with pytest.raises(ApplicationException) as exc_info:
        await use_case.execute(parent_user=parent_user, child_data=child_create_data)

    assert exc_info.value.status_code == 409
    assert "email already exists" in str(exc_info.value.message).lower()
    mock_user_repo.create.assert_not_called()
    mock_user_repo.link_parent_to_student.assert_not_called()

@pytest.mark.asyncio
async def test_create_student_by_parent_not_a_parent_role(mock_user_repo, child_create_data):
    use_case = CreateStudentByParentUseCase(user_repo=mock_user_repo)
    non_parent_user = DomainUser(user_id=uuid.uuid4(), email="notparent@example.com", role=UserRole.TEACHER)

    with pytest.raises(ForbiddenException) as exc_info:
        await use_case.execute(parent_user=non_parent_user, child_data=child_create_data)

    assert "not authorized to create a child account" in str(exc_info.value.message).lower()
    mock_user_repo.get_by_email.assert_not_called()
    mock_user_repo.create.assert_not_called()
    mock_user_repo.link_parent_to_student.assert_not_called()

# To run these tests (conceptual):
# 1. Ensure pytest and pytest-asyncio are installed.
# 2. Navigate to the root of the project (or where `src` is).
# 3. Run `pytest src/tests/application/use_cases/test_parent_use_cases.py`
# This assumes that Python path is set up correctly for imports from `readmaster_ai`.
