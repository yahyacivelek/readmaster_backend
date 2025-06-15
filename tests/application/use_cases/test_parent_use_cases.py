# tests/application/use_cases/test_parent_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, date
from dateutil import tz

from readmaster_ai.application.use_cases.parent_use_cases import (
    ListParentChildrenUseCase, GetChildProgressForParentUseCase, GetChildAssessmentResultForParentUseCase,
    CreateChildAccountUseCase, # Added
    ParentAssignReadingUseCase, # Added
    ListChildAssignmentsUseCase, # Added
    UpdateChildAssignmentUseCase, # Added
    DeleteChildAssignmentUseCase # Added
)
# Reused Use Cases (these are dependencies of parent use cases, so we mock their instances)
from readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase
from readmaster_ai.application.use_cases.assessment_use_cases import GetAssessmentResultDetailsUseCase

from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.entities.assessment import Assessment # Added
from readmaster_ai.domain.entities.reading import Reading # Added
from readmaster_ai.domain.value_objects.common_enums import UserRole, AssessmentStatus
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository # Added
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository # Added
# DTOs for type hinting and verification
from readmaster_ai.application.dto.user_dtos import UserResponseDTO, ParentChildCreateRequestDTO, UserCreateDTO
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO, ParentAssignReadingRequestDTO, AssessmentResponseDTO, AssignmentUpdateDTO
from readmaster_ai.application.dto.assessment_list_dto import PaginatedAssessmentListResponseDTO, AssessmentListItemDTO
from readmaster_ai.shared.exceptions import ForbiddenException, NotFoundException, InvalidInputError
# from readmaster_ai.services.password_service import PasswordService # Addsed

@pytest.fixture
def mock_user_repo_for_parent() -> MagicMock: # Renamed fixture
    """Fixture for a mocked UserRepository, tailored for parent use case tests."""
    mock = MagicMock(spec=UserRepository)
    mock.list_children_by_parent_id = AsyncMock(return_value=[])
    mock.is_parent_of_student = AsyncMock(return_value=False)
    mock.get_by_id = AsyncMock(return_value=None)
    mock.get_by_email = AsyncMock(return_value=None) # Added for create child
    mock.create_user_with_role = AsyncMock() # Added for create child
    mock.link_parent_to_student = AsyncMock() # Added for create child
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
def mock_assessment_repo() -> MagicMock: # Updated to be more specific for assignment tests
    """Fixture for a mocked AssessmentRepository."""
    mock = MagicMock(spec=AssessmentRepository)
    mock.create = AsyncMock()
    mock.get_by_id = AsyncMock(return_value=None)
    mock.list_by_child_and_assigner = AsyncMock(return_value=([], 0)) # PaginatedResult format
    mock.update = AsyncMock()
    mock.delete = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_result_repo() -> MagicMock: # Unused by new tests but keep for existing
    """Fixture for a mocked ResultRepository."""
    return MagicMock()

@pytest.fixture
def mock_reading_repo() -> MagicMock: # Updated to be more specific
    """Fixture for a mocked ReadingRepository."""
    mock = MagicMock(spec=ReadingRepository)
    mock.get_by_id = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def mock_password_service() -> MagicMock:
    """Fixture for a mocked PasswordService."""
    mock = MagicMock(spec=PasswordService)
    mock.hash_password = MagicMock(return_value="hashed_password")
    return mock

@pytest.fixture
def mock_student_progress_summary_uc() -> MagicMock: # Unused by new tests but keep for existing
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


# === CreateChildAccountUseCase Tests ===
@pytest.mark.asyncio
async def test_create_child_account_success(
    mock_user_repo_for_parent: MagicMock,
    mock_password_service: MagicMock,
    sample_parent_user: DomainUser
):
    # Arrange
    child_dto = ParentChildCreateRequestDTO(
        email="new.child@example.com",
        password="password123",
        first_name="New",
        last_name="Child"
    )
    created_child_user = DomainUser(
        user_id=uuid4(),
        email=child_dto.email,
        password_hash="hashed_password",
        role=UserRole.STUDENT,
        first_name=child_dto.first_name,
        last_name=child_dto.last_name
    )
    mock_user_repo_for_parent.get_by_id.return_value = sample_parent_user # For parent check
    mock_user_repo_for_parent.get_by_email.return_value = None # No existing user with this email
    mock_user_repo_for_parent.create_user_with_role.return_value = created_child_user

    use_case = CreateChildAccountUseCase(user_repository=mock_user_repo_for_parent) # , password_service=mock_password_service)

    # Act
    result_dto = await use_case.execute(parent_id=sample_parent_user.user_id, child_data=child_dto)

    # Assert
    mock_user_repo_for_parent.get_by_id.assert_called_once_with(sample_parent_user.user_id)
    mock_user_repo_for_parent.get_by_email.assert_called_once_with(child_dto.email)
    mock_password_service.hash_password.assert_called_once_with(child_dto.password)

    # Check that create_user_with_role was called with a UserCreateDTO-like structure
    call_args = mock_user_repo_for_parent.create_user_with_role.call_args[0][0]
    assert call_args.email == child_dto.email
    assert call_args.password == "hashed_password" # Ensure hashed password was passed
    assert call_args.role == UserRole.STUDENT

    mock_user_repo_for_parent.link_parent_to_student.assert_called_once_with(
        parent_id=sample_parent_user.user_id, student_id=created_child_user.user_id
    )
    assert isinstance(result_dto, UserResponseDTO)
    assert result_dto.user_id == created_child_user.user_id
    assert result_dto.email == child_dto.email

@pytest.mark.asyncio
async def test_create_child_account_email_exists(
    mock_user_repo_for_parent: MagicMock,
    mock_password_service: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser # Represents existing user
):
    # Arrange
    child_dto = ParentChildCreateRequestDTO(email=sample_child_user.email, password="password123")
    mock_user_repo_for_parent.get_by_id.return_value = sample_parent_user
    mock_user_repo_for_parent.get_by_email.return_value = sample_child_user # Email already exists

    use_case = CreateChildAccountUseCase(user_repository=mock_user_repo_for_parent) # , password_service=mock_password_service)

    # Act & Assert
    with pytest.raises(InvalidInputError):
        await use_case.execute(parent_id=sample_parent_user.user_id, child_data=child_dto)

# === ParentAssignReadingUseCase Tests ===
@pytest.mark.asyncio
async def test_parent_assign_reading_success(
    mock_assessment_repo: MagicMock,
    mock_user_repo_for_parent: MagicMock,
    mock_reading_repo: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    reading_id = uuid4()
    assign_dto = ParentAssignReadingRequestDTO(reading_id=reading_id, due_date=date.today())

    mock_user_repo_for_parent.get_by_id.return_value = sample_parent_user
    mock_user_repo_for_parent.is_parent_of_student.return_value = True
    mock_reading_repo.get_by_id.return_value = Reading(reading_id=reading_id, title="Test Reading", content_text="...")

    # Mock the assessment created by the repo
    created_assessment = Assessment(
        assessment_id=uuid4(),
        student_id=sample_child_user.user_id,
        reading_id=reading_id,
        assigned_by_parent_id=sample_parent_user.user_id,
        status=AssessmentStatus.PENDING_AUDIO
    )
    mock_assessment_repo.create.return_value = created_assessment # Changed from .add

    use_case = ParentAssignReadingUseCase(
        assessment_repository=mock_assessment_repo,
        user_repository=mock_user_repo_for_parent,
        reading_repository=mock_reading_repo
    )

    # Act
    result_dto = await use_case.execute(
        parent_id=sample_parent_user.user_id,
        child_id=sample_child_user.user_id,
        assign_data=assign_dto
    )

    # Assert
    mock_assessment_repo.create.assert_called_once() # Changed from .add
    call_args = mock_assessment_repo.create.call_args[0][0]
    assert isinstance(call_args, Assessment)
    assert call_args.student_id == sample_child_user.user_id
    assert call_args.reading_id == reading_id
    assert call_args.assigned_by_parent_id == sample_parent_user.user_id
    assert result_dto.assessment_id == created_assessment.assessment_id

# === ListChildAssignmentsUseCase Tests ===
@pytest.mark.asyncio
async def test_list_child_assignments_success(
    mock_assessment_repo: MagicMock,
    mock_user_repo_for_parent: MagicMock,
    mock_reading_repo: MagicMock, # Added
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    mock_user_repo_for_parent.get_by_id.side_effect = [sample_parent_user, sample_child_user] # parent, then child for context
    mock_user_repo_for_parent.is_parent_of_student.return_value = True

    reading_id = uuid4()
    sample_assessment = Assessment(
        assessment_id=uuid4(), student_id=sample_child_user.user_id, reading_id=reading_id,
        assigned_by_parent_id=sample_parent_user.user_id, status=AssessmentStatus.PENDING_AUDIO,
        assessment_date=datetime.now(tz.tzutc()), updated_at=datetime.now(tz.tzutc())
    )
    mock_assessment_repo.list_by_child_and_assigner.return_value = ([sample_assessment], 1)
    mock_reading_repo.get_by_id.return_value = Reading(reading_id=reading_id, title="Test Reading", content_text="...")


    use_case = ListChildAssignmentsUseCase(
        assessment_repository=mock_assessment_repo,
        user_repository=mock_user_repo_for_parent,
        reading_repository=mock_reading_repo # Added
    )

    # Act
    result_paginated_dto = await use_case.execute(sample_parent_user.user_id, sample_child_user.user_id, 1, 10)

    # Assert
    mock_assessment_repo.list_by_child_and_assigner.assert_called_once_with(
        student_id=sample_child_user.user_id, parent_id=sample_parent_user.user_id, page=1, size=10
    )
    assert len(result_paginated_dto.items) == 1
    assert isinstance(result_paginated_dto.items[0], AssessmentListItemDTO)
    assert result_paginated_dto.items[0].assessment_id == sample_assessment.assessment_id
    assert result_paginated_dto.items[0].user_relationship_context == "Your Child"


# === UpdateChildAssignmentUseCase Tests ===
@pytest.mark.asyncio
async def test_update_child_assignment_success(
    mock_assessment_repo: MagicMock,
    mock_user_repo_for_parent: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    assessment_id = uuid4()
    update_dto = AssignmentUpdateDTO(due_date=date.today()) # due_date is no-op for now

    sample_assessment = Assessment(
        assessment_id=assessment_id, student_id=sample_child_user.user_id, reading_id=uuid4(),
        assigned_by_parent_id=sample_parent_user.user_id, status=AssessmentStatus.PENDING_AUDIO
    )
    mock_user_repo_for_parent.get_by_id.return_value = sample_parent_user
    mock_assessment_repo.get_by_id.return_value = sample_assessment
    mock_assessment_repo.update.return_value = sample_assessment # Assume update returns the assessment

    use_case = UpdateChildAssignmentUseCase(
        assessment_repository=mock_assessment_repo,
        user_repository=mock_user_repo_for_parent
    )

    # Act
    result_dto = await use_case.execute(
        parent_id=sample_parent_user.user_id,
        child_id=sample_child_user.user_id,
        assignment_id=assessment_id,
        update_data=update_dto
    )

    # Assert
    mock_assessment_repo.update.assert_called_once_with(sample_assessment)
    assert isinstance(result_dto, AssessmentResponseDTO)
    assert result_dto.assessment_id == assessment_id


# === DeleteChildAssignmentUseCase Tests ===
@pytest.mark.asyncio
async def test_delete_child_assignment_success(
    mock_assessment_repo: MagicMock,
    mock_user_repo_for_parent: MagicMock,
    sample_parent_user: DomainUser,
    sample_child_user: DomainUser
):
    # Arrange
    assessment_id = uuid4()
    sample_assessment = Assessment(
        assessment_id=assessment_id, student_id=sample_child_user.user_id, reading_id=uuid4(),
        assigned_by_parent_id=sample_parent_user.user_id, status=AssessmentStatus.PENDING_AUDIO
    )
    mock_user_repo_for_parent.get_by_id.return_value = sample_parent_user
    mock_assessment_repo.get_by_id.return_value = sample_assessment
    mock_assessment_repo.delete.return_value = True # Assume delete returns True on success

    use_case = DeleteChildAssignmentUseCase(
        assessment_repository=mock_assessment_repo,
        user_repository=mock_user_repo_for_parent
    )

    # Act
    await use_case.execute(
        parent_id=sample_parent_user.user_id,
        child_id=sample_child_user.user_id,
        assignment_id=assessment_id
    )

    # Assert
    mock_assessment_repo.delete.assert_called_once_with(assessment_id)
