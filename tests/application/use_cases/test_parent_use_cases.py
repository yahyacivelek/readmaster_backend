# tests/application/use_cases/test_parent_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from src.readmaster_ai.application.use_cases.parent_use_cases import (
    ListParentChildrenUseCase, GetChildProgressForParentUseCase, GetChildAssessmentResultForParentUseCase
)
# Reused Use Cases (these are dependencies of parent use cases, so we mock their instances)
from src.readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase
from src.readmaster_ai.application.use_cases.assessment_use_cases import GetAssessmentResultDetailsUseCase

from src.readmaster_ai.domain.entities.user import User as DomainUser
from src.readmaster_ai.domain.value_objects.common_enums import UserRole # Enum for roles
from src.readmaster_ai.domain.repositories.user_repository import UserRepository
# DTOs for type hinting and verification
from src.readmaster_ai.application.dto.user_dtos import UserResponseDTO
from src.readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from src.readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO
from src.readmaster_ai.shared.exceptions import ForbiddenException, NotFoundException

@pytest.fixture
def mock_user_repo_for_parent() -> MagicMock: # Renamed fixture
    """Fixture for a mocked UserRepository, tailored for parent use case tests."""
    mock = MagicMock(spec=UserRepository)
    mock.list_children_by_parent_id = AsyncMock(return_value=[]) # Default: no children
    mock.is_parent_of_student = AsyncMock(return_value=False) # Default: not a parent of given student
    mock.get_by_id = AsyncMock(return_value=None) # Default: user (child) not found
    return mock

@pytest.fixture
def sample_parent_user() -> DomainUser:
    """Fixture for a sample parent DomainUser."""
    return DomainUser(user_id=uuid4(), email="parent.tests@example.com", password_hash="parent_hash", role=UserRole.PARENT)

@pytest.fixture
def sample_child_user() -> DomainUser:
    """Fixture for a sample child (student) DomainUser."""
    return DomainUser(user_id=uuid4(), email="child.tests@example.com", password_hash="child_hash", role=UserRole.STUDENT)

@pytest.fixture
def mock_student_progress_uc_instance() -> MagicMock: # Renamed fixture
    """Mocks an instance of GetStudentProgressSummaryUseCase."""
    mock = MagicMock(spec=GetStudentProgressSummaryUseCase)
    # This mock's execute method will be called by GetChildProgressForParentUseCase
    # Configure it to return a mock DTO or a real DTO with mock data.
    # For simplicity, returning an AsyncMock that itself returns a MagicMock of the DTO.
    mock_dto_instance = MagicMock(spec=StudentProgressSummaryDTO)
    mock.execute = AsyncMock(return_value=mock_dto_instance)
    return mock

@pytest.fixture
def mock_assessment_details_uc_instance() -> MagicMock: # Renamed fixture
    """Mocks an instance of GetAssessmentResultDetailsUseCase."""
    mock = MagicMock(spec=GetAssessmentResultDetailsUseCase)
    mock_dto_instance = MagicMock(spec=AssessmentResultDetailDTO)
    mock.execute = AsyncMock(return_value=mock_dto_instance)
    return mock


# === ListParentChildrenUseCase Tests ===
@pytest.mark.asyncio
async def test_list_parent_children_success(mock_user_repo_for_parent: MagicMock, sample_parent_user: DomainUser, sample_child_user: DomainUser):
    # Arrange
    mock_user_repo_for_parent.list_children_by_parent_id.return_value = [sample_child_user]
    use_case = ListParentChildrenUseCase(user_repo=mock_user_repo_for_parent)

    # Act
    children_dtos = await use_case.execute(sample_parent_user)

    # Assert
    mock_user_repo_for_parent.list_children_by_parent_id.assert_called_once_with(sample_parent_user.user_id)
    assert len(children_dtos) == 1
    assert isinstance(children_dtos[0], UserResponseDTO) # Use case converts domain to DTO
    assert children_dtos[0].user_id == sample_child_user.user_id

@pytest.mark.asyncio
async def test_list_parent_children_not_parent_role(mock_user_repo_for_parent: MagicMock, sample_child_user: DomainUser):
    # sample_child_user has STUDENT role, not PARENT
    use_case = ListParentChildrenUseCase(user_repo=mock_user_repo_for_parent)

    with pytest.raises(ForbiddenException):
        await use_case.execute(sample_child_user)
    mock_user_repo_for_parent.list_children_by_parent_id.assert_not_called()


# === GetChildProgressForParentUseCase Tests ===
@pytest.mark.asyncio
async def test_get_child_progress_success(
    mock_user_repo_for_parent: MagicMock,
    mock_student_progress_uc_instance: MagicMock, # Use renamed fixture
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.is_parent_of_student.return_value = True # Parent is linked to child

    # The use case constructor for GetChildProgressForParentUseCase instantiates GetStudentProgressSummaryUseCase.
    # We need to inject mocks for the repositories that GetStudentProgressSummaryUseCase needs.
    # This is becoming complex. The alternative is to mock the *instance* of GetStudentProgressSummaryUseCase
    # that GetChildProgressForParentUseCase creates.
    # The current fixture mock_student_progress_uc_instance mocks the instance.

    use_case = GetChildProgressForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        student_progress_uc=mock_student_progress_uc_instance # Pass the mocked use case instance
    )

    # Act
    result_dto = await use_case.execute(sample_parent_user, sample_child_user.user_id)

    # Assert
    mock_user_repo_for_parent.is_parent_of_student.assert_called_once_with(sample_parent_user.user_id, sample_child_user.user_id)
    # Check that the mocked student_progress_uc's execute method was called
    mock_student_progress_uc_instance.execute.assert_called_once_with(
        student_id=sample_child_user.user_id,
        requesting_user=sample_parent_user # parent_user is passed as requesting_user
    )
    assert isinstance(result_dto, MagicMock) # As it returns the mock DTO from the mocked UC
    assert isinstance(result_dto, StudentProgressSummaryDTO) # Also check spec

@pytest.mark.asyncio
async def test_get_child_progress_not_linked(
    mock_user_repo_for_parent: MagicMock,
    mock_student_progress_uc_instance: MagicMock, # Use renamed fixture
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.is_parent_of_student.return_value = False # Parent NOT linked
    use_case = GetChildProgressForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        student_progress_uc=mock_student_progress_uc_instance
    )

    # Act & Assert
    with pytest.raises(ForbiddenException):
        await use_case.execute(sample_parent_user, sample_child_user.user_id)
    mock_student_progress_uc_instance.execute.assert_not_called()


# === GetChildAssessmentResultForParentUseCase Tests ===
@pytest.mark.asyncio
async def test_get_child_assessment_result_success(
    mock_user_repo_for_parent: MagicMock,
    mock_assessment_details_uc_instance: MagicMock, # Use renamed fixture
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.is_parent_of_student.return_value = True # Parent is linked
    mock_user_repo_for_parent.get_by_id.return_value = sample_child_user # Child user found by get_by_id

    assessment_id_to_test = uuid4()
    use_case = GetChildAssessmentResultForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        assessment_details_uc=mock_assessment_details_uc_instance # Pass the mocked use case instance
    )

    # Act
    result_dto = await use_case.execute(sample_parent_user, sample_child_user.user_id, assessment_id_to_test)

    # Assert
    mock_user_repo_for_parent.is_parent_of_student.assert_called_once_with(sample_parent_user.user_id, sample_child_user.user_id)
    mock_user_repo_for_parent.get_by_id.assert_called_once_with(sample_child_user.user_id) # To get child DomainUser
    # Check that the mocked assessment_details_uc's execute method was called
    mock_assessment_details_uc_instance.execute.assert_called_once_with(
        assessment_id=assessment_id_to_test,
        student=sample_child_user # The actual child DomainUser object
    )
    assert isinstance(result_dto, MagicMock) # Returns mock DTO from mocked UC
    assert isinstance(result_dto, AssessmentResultDetailDTO) # Check spec too

@pytest.mark.asyncio
async def test_get_child_assessment_result_child_not_found(
    mock_user_repo_for_parent: MagicMock,
    mock_assessment_details_uc_instance: MagicMock, # Use renamed fixture
    sample_parent_user: DomainUser
):
    # Arrange
    non_existent_child_id = uuid4()
    mock_user_repo_for_parent.is_parent_of_student.return_value = True # Assume link check passes (or is for a different child)
    mock_user_repo_for_parent.get_by_id.return_value = None # Child user NOT found by get_by_id

    use_case = GetChildAssessmentResultForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        assessment_details_uc=mock_assessment_details_uc_instance
    )

    # Act & Assert
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(sample_parent_user, non_existent_child_id, uuid4())
    assert "Student" in exc_info.value.message
    mock_assessment_details_uc_instance.execute.assert_not_called()
