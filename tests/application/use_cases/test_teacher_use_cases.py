import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from readmaster_ai.application.use_cases.teacher_use_cases import CreateStudentByTeacherUseCase
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.application.dto.user_dtos import TeacherStudentCreateRequestDTO, UserResponseDTO, UserCreateDTO
from readmaster_ai.shared.exceptions import NotAuthorizedError, InvalidInputError
from readmaster_ai.services.password_service import PasswordService

@pytest.fixture
def mock_user_repo_for_teacher() -> MagicMock:
    mock = MagicMock(spec=UserRepository)
    mock.get_by_id = AsyncMock(return_value=None)
    mock.get_by_email = AsyncMock(return_value=None)
    mock.create_user_with_role = AsyncMock()
    return mock

@pytest.fixture
def mock_password_service_for_teacher() -> MagicMock:
    mock = MagicMock(spec=PasswordService)
    mock.hash_password = MagicMock(return_value="hashed_password_for_student")
    return mock

@pytest.fixture
def sample_teacher_user() -> DomainUser:
    return DomainUser(user_id=uuid4(), email="teacher.test@example.com", password_hash="teacher_hash", role=UserRole.TEACHER)

@pytest.mark.asyncio
async def test_create_student_by_teacher_success(
    mock_user_repo_for_teacher: MagicMock,
    mock_password_service_for_teacher: MagicMock,
    sample_teacher_user: DomainUser
):
    # Arrange
    student_data_dto = TeacherStudentCreateRequestDTO(
        email="new.student.by.teacher@example.com",
        password="studentpassword",
        first_name="Student",
        last_name="ByTeacher"
    )

    created_student_domain = DomainUser(
        user_id=uuid4(),
        email=student_data_dto.email,
        password_hash="hashed_password_for_student", # from mock_password_service
        role=UserRole.STUDENT,
        first_name=student_data_dto.first_name,
        last_name=student_data_dto.last_name
    )

    mock_user_repo_for_teacher.get_by_id.return_value = sample_teacher_user # Teacher found
    mock_user_repo_for_teacher.get_by_email.return_value = None # New student email is unique
    mock_user_repo_for_teacher.create_user_with_role.return_value = created_student_domain

    use_case = CreateStudentByTeacherUseCase(
        user_repository=mock_user_repo_for_teacher,
        password_service=mock_password_service_for_teacher
    )

    # Act
    result_dto = await use_case.execute(teacher_id=sample_teacher_user.user_id, student_data=student_data_dto)

    # Assert
    mock_user_repo_for_teacher.get_by_id.assert_called_once_with(sample_teacher_user.user_id)
    mock_user_repo_for_teacher.get_by_email.assert_called_once_with(student_data_dto.email)
    mock_password_service_for_teacher.hash_password.assert_called_once_with(student_data_dto.password)

    # Check call to create_user_with_role
    create_call_args = mock_user_repo_for_teacher.create_user_with_role.call_args[0][0]
    assert isinstance(create_call_args, UserCreateDTO)
    assert create_call_args.email == student_data_dto.email
    assert create_call_args.password == "hashed_password_for_student"
    assert create_call_args.role == UserRole.STUDENT

    assert isinstance(result_dto, UserResponseDTO)
    assert result_dto.user_id == created_student_domain.user_id
    assert result_dto.email == created_student_domain.email
    assert result_dto.role == UserRole.STUDENT

@pytest.mark.asyncio
async def test_create_student_by_teacher_unauthorized(
    mock_user_repo_for_teacher: MagicMock,
    mock_password_service_for_teacher: MagicMock,
    sample_teacher_user: DomainUser # But we'll make get_by_id return a student
):
    # Arrange
    student_data_dto = TeacherStudentCreateRequestDTO(email="test@example.com", password="pw")

    # Simulate the user calling this is NOT a teacher
    non_teacher_user = DomainUser(user_id=sample_teacher_user.user_id, email="student@example.com", role=UserRole.STUDENT, password_hash="hash")
    mock_user_repo_for_teacher.get_by_id.return_value = non_teacher_user

    use_case = CreateStudentByTeacherUseCase(
        user_repository=mock_user_repo_for_teacher,
        password_service=mock_password_service_for_teacher
    )

    # Act & Assert
    with pytest.raises(NotAuthorizedError):
        await use_case.execute(teacher_id=sample_teacher_user.user_id, student_data=student_data_dto)

@pytest.mark.asyncio
async def test_create_student_by_teacher_email_exists(
    mock_user_repo_for_teacher: MagicMock,
    mock_password_service_for_teacher: MagicMock,
    sample_teacher_user: DomainUser
):
    # Arrange
    student_data_dto = TeacherStudentCreateRequestDTO(email="existing.student@example.com", password="pw")

    mock_user_repo_for_teacher.get_by_id.return_value = sample_teacher_user
    # Simulate email already exists
    mock_user_repo_for_teacher.get_by_email.return_value = DomainUser(user_id=uuid4(), email=student_data_dto.email, role=UserRole.STUDENT, password_hash="hash")

    use_case = CreateStudentByTeacherUseCase(
        user_repository=mock_user_repo_for_teacher,
        password_service=mock_password_service_for_teacher
    )

    # Act & Assert
    with pytest.raises(InvalidInputError):
        await use_case.execute(teacher_id=sample_teacher_user.user_id, student_data=student_data_dto)
