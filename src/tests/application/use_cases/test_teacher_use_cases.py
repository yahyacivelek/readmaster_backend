import pytest
import uuid
from unittest.mock import AsyncMock, patch

from readmaster_ai.application.use_cases.user_use_cases import CreateStudentByTeacherUseCase # Use case location
from readmaster_ai.presentation.schemas.user_schemas import TeacherStudentCreateRequestSchema
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.shared.exceptions import ApplicationException, ForbiddenException
# from readmaster_ai.application.use_cases.user_use_cases import pwd_context # pwd_context is in the same file as use case

@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def teacher_user():
    return DomainUser(
        user_id=uuid.uuid4(),
        email="teacher@example.com",
        role=UserRole.TEACHER,
        password_hash="teacher_hashed_password"
    )

@pytest.fixture
def student_create_data(): # Renamed from child_create_data for clarity
    return TeacherStudentCreateRequestSchema(
        email="newstudent@example.com",
        password="student_password",
        first_name="New",
        last_name="Student",
        preferred_language="fr"
        # role is fixed to "student" in the schema
    )

@pytest.mark.asyncio
async def test_create_student_by_teacher_success(mock_user_repo, teacher_user, student_create_data):
    use_case = CreateStudentByTeacherUseCase(user_repo=mock_user_repo)
    mock_user_repo.get_by_email.return_value = None # No existing user

    created_student_id = uuid.uuid4()

    async def mock_create_user(user: DomainUser):
        assert user.email == student_create_data.email
        assert user.role == UserRole.STUDENT
        assert user.password_hash != student_create_data.password # Check it's hashed
        user.user_id = created_student_id # Ensure ID for return consistency
        return user

    mock_user_repo.create.side_effect = mock_create_user

    # Patch uuid.uuid4 used by DomainUser's init
    with patch('uuid.uuid4', return_value=created_student_id):
        result_student = await use_case.execute(teacher_user=teacher_user, student_data=student_create_data)

    mock_user_repo.get_by_email.assert_called_once_with(student_create_data.email)
    mock_user_repo.create.assert_called_once()
    # args, _ = mock_user_repo.create.call_args
    # created_user_arg = args[0]
    # assert created_user_arg.email == student_create_data.email
    # assert created_user_arg.role == UserRole.STUDENT

    mock_user_repo.link_parent_to_student.assert_not_called() # Important check

    assert result_student is not None
    assert result_student.email == student_create_data.email
    assert result_student.role == UserRole.STUDENT
    assert result_student.user_id == created_student_id

@pytest.mark.asyncio
async def test_create_student_by_teacher_email_exists(mock_user_repo, teacher_user, student_create_data):
    use_case = CreateStudentByTeacherUseCase(user_repo=mock_user_repo)
    mock_user_repo.get_by_email.return_value = DomainUser(email="newstudent@example.com", role=UserRole.STUDENT)

    with pytest.raises(ApplicationException) as exc_info:
        await use_case.execute(teacher_user=teacher_user, student_data=student_create_data)

    assert exc_info.value.status_code == 409
    assert "email already exists" in str(exc_info.value.message).lower()
    mock_user_repo.create.assert_not_called()

@pytest.mark.asyncio
async def test_create_student_by_teacher_not_a_teacher_role(mock_user_repo, student_create_data):
    use_case = CreateStudentByTeacherUseCase(user_repo=mock_user_repo)
    non_teacher_user = DomainUser(user_id=uuid.uuid4(), email="notteacher@example.com", role=UserRole.PARENT)

    # The use case CreateStudentByTeacherUseCase uses ApplicationException(..., status_code=403)
    # if ForbiddenException is not available, or if it's the chosen pattern in that file.
    # Let's expect ForbiddenException as per the use case code structure,
    # but the subtask report for adding the use case mentioned it might use ApplicationException(status_code=403).
    # For this test, we'll aim for ForbiddenException if it's imported in user_use_cases.py, otherwise ApplicationException.
    # The use case file user_use_cases.py currently does not import ForbiddenException.
    # So we should expect ApplicationException with status_code=403.

    # Forcing consistency: If ForbiddenException is the standard, it should be imported and used.
    # Assuming the subtask report was an observation and the intention is to use ForbiddenException where appropriate.
    # If `user_use_cases.py` was *not* updated to include `from readmaster_ai.shared.exceptions import ForbiddenException`
    # and use it, this test would need to expect `ApplicationException` and check status_code and message.
    # For now, let's write it assuming ForbiddenException *should* be used.
    # If the subtask for use case creation did not add ForbiddenException to user_use_cases.py, this test might fail
    # and would need adjustment to expect ApplicationException.

    # Re-checking the subtask report for step 2:
    # "A comment was added regarding ForbiddenException not being imported in this file; ApplicationException with status 403 was used instead for consistency with the existing code in the file."
    # OK, so we expect ApplicationException with status 403.

    with pytest.raises(ApplicationException) as exc_info: # Changed from ForbiddenException
        await use_case.execute(teacher_user=non_teacher_user, student_data=student_create_data)

    assert exc_info.value.status_code == 403 # Check status code
    assert "not authorized to create a student account" in str(exc_info.value.message).lower() # Check message

    mock_user_repo.get_by_email.assert_not_called()
    mock_user_repo.create.assert_not_called()
