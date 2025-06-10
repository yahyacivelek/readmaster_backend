# tests/application/use_cases/test_parent_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from dateutil import tz

from readmaster_ai.application.use_cases.parent_use_cases import (
    ListParentChildrenUseCase, GetChildProgressForParentUseCase, GetChildAssessmentResultForParentUseCase
)
# Reused Use Cases (these are dependencies of parent use cases, so we mock their instances)
from readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase
from readmaster_ai.application.use_cases.assessment_use_cases import GetAssessmentResultDetailsUseCase

from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # Enum for roles
from readmaster_ai.domain.repositories.user_repository import UserRepository
# DTOs for type hinting and verification
from readmaster_ai.application.dto.user_dtos import UserResponseDTO
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO
from readmaster_ai.shared.exceptions import ForbiddenException, NotFoundException
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus

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
def mock_assessment_repo() -> MagicMock:
    """Fixture for a mocked AssessmentRepository."""
    return MagicMock()

@pytest.fixture
def mock_result_repo() -> MagicMock:
    """Fixture for a mocked ResultRepository."""
    return MagicMock()

@pytest.fixture
def mock_reading_repo() -> MagicMock:
    """Fixture for a mocked ReadingRepository."""
    return MagicMock()

@pytest.fixture
def mock_student_progress_summary_uc() -> MagicMock:
    """Mocks an instance of GetStudentProgressSummaryUseCase."""
    mock = MagicMock()
    # Create a mock DTO for the progress summary
    mock_dto = MagicMock(spec=StudentProgressSummaryDTO)
    mock.execute = AsyncMock(return_value=mock_dto)
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
    mock_assessment_repo: MagicMock,
    mock_result_repo: MagicMock,
    mock_reading_repo: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.is_parent_of_student.return_value = True # Parent is linked to child
    mock_user_repo_for_parent.get_by_id.return_value = sample_child_user # Mock the child user fetch

    # Create a mock DTO for the progress summary
    mock_dto = StudentProgressSummaryDTO(
        student_info=UserResponseDTO(
            user_id=sample_child_user.user_id,
            email=sample_child_user.email,
            role=UserRole.STUDENT
        ),
        total_assessments_assigned=5,
        total_assessments_completed=3,
        average_comprehension_score=85.5,
        average_fluency_score=90.0,
        recent_assessments=[]
    )

    # Create a mock GetStudentProgressSummaryUseCase that returns our DTO
    mock_student_progress_uc = MagicMock()
    mock_student_progress_uc.execute = AsyncMock(return_value=mock_dto)

    # Create the use case with the mock repositories
    use_case = GetChildProgressForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        assessment_repo=mock_assessment_repo,
        result_repo=mock_result_repo,
        reading_repo=mock_reading_repo
    )

    # Replace the student_progress_uc with our mock
    use_case.student_progress_uc = mock_student_progress_uc

    # Act
    result_dto = await use_case.execute(sample_parent_user, sample_child_user.user_id)

    # Assert
    mock_user_repo_for_parent.is_parent_of_student.assert_called_once_with(sample_parent_user.user_id, sample_child_user.user_id)
    mock_user_repo_for_parent.get_by_id.assert_called_once_with(sample_child_user.user_id)
    mock_student_progress_uc.execute.assert_called_once_with(
        student_id=sample_child_user.user_id,
        requesting_user=sample_parent_user
    )
    assert result_dto == mock_dto

@pytest.mark.asyncio
async def test_get_child_progress_not_linked(
    mock_user_repo_for_parent: MagicMock,
    mock_assessment_repo: MagicMock,
    mock_result_repo: MagicMock,
    mock_reading_repo: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.is_parent_of_student.return_value = False # Parent NOT linked
    use_case = GetChildProgressForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        assessment_repo=mock_assessment_repo,
        result_repo=mock_result_repo,
        reading_repo=mock_reading_repo
    )

    # Act & Assert
    with pytest.raises(ForbiddenException):
        await use_case.execute(sample_parent_user, sample_child_user.user_id)


# === GetChildAssessmentResultForParentUseCase Tests ===
@pytest.mark.asyncio
async def test_get_child_assessment_result_success(
    mock_user_repo_for_parent: MagicMock,
    mock_assessment_repo: MagicMock,
    mock_result_repo: MagicMock,
    mock_reading_repo: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.is_parent_of_student.return_value = True # Parent is linked
    mock_user_repo_for_parent.get_by_id.return_value = sample_child_user # Child user found by get_by_id

    assessment_id_to_test = uuid4()
    reading_id = uuid4()
    
    # Create a mock DTO for the assessment result
    mock_dto = AssessmentResultDetailDTO(
        assessment_id=assessment_id_to_test,
        student_id=sample_child_user.user_id,
        reading_id=reading_id,
        status=AssessmentStatus.COMPLETED,
        assessment_date=datetime.now(tz.tzutc()),
        updated_at=datetime.now(tz.tzutc()),
        student_info=UserResponseDTO(
            user_id=sample_child_user.user_id,
            email=sample_child_user.email,
            role=UserRole.STUDENT
        ),
        reading_title="Test Reading",
        analysis_data={"fluency_score": 90.0},
        comprehension_score=85.5,
        submitted_answers=[],
        audio_file_url=None,
        audio_duration=None,
        ai_raw_speech_to_text=None,
        assigned_by_teacher_id=None
    )

    # Create a mock GetAssessmentResultDetailsUseCase
    mock_assessment_details_uc = MagicMock()
    mock_assessment_details_uc.execute = AsyncMock(return_value=mock_dto)

    # Create the use case with the mock repositories
    use_case = GetChildAssessmentResultForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        assessment_repo=mock_assessment_repo,
        assessment_result_repo=mock_result_repo,
        student_answer_repo=MagicMock(),  
        quiz_question_repo=MagicMock(),   
        reading_repo=mock_reading_repo
    )
    # Replace the internal use case with our mock
    use_case.assessment_details_uc = mock_assessment_details_uc

    # Act
    result_dto = await use_case.execute(sample_parent_user, sample_child_user.user_id, assessment_id_to_test)

    # Assert
    mock_user_repo_for_parent.is_parent_of_student.assert_called_once_with(sample_parent_user.user_id, sample_child_user.user_id)
    mock_user_repo_for_parent.get_by_id.assert_called_once_with(sample_child_user.user_id)
    mock_assessment_details_uc.execute.assert_called_once_with(
        assessment_id=assessment_id_to_test,
        student=sample_child_user
    )
    assert result_dto == mock_dto

@pytest.mark.asyncio
async def test_get_child_assessment_result_child_not_found(
    mock_user_repo_for_parent: MagicMock,
    mock_assessment_repo: MagicMock,
    mock_result_repo: MagicMock,
    mock_reading_repo: MagicMock,
    sample_parent_user: DomainUser
):
    # Arrange
    non_existent_child_id = uuid4()
    mock_user_repo_for_parent.is_parent_of_student.return_value = True # Assume link check passes (or is for a different child)
    mock_user_repo_for_parent.get_by_id.return_value = None # Child user NOT found by get_by_id

    use_case = GetChildAssessmentResultForParentUseCase(
        user_repo=mock_user_repo_for_parent,
        assessment_repo=mock_assessment_repo,
        assessment_result_repo=mock_result_repo,
        student_answer_repo=MagicMock(),  
        quiz_question_repo=MagicMock(),   
        reading_repo=mock_reading_repo
    )

    # Act & Assert
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(sample_parent_user, non_existent_child_id, uuid4())
    assert "Student" in exc_info.value.message
