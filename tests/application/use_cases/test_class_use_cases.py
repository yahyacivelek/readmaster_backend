# tests/application/use_cases/test_class_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, ANY
from uuid import uuid4, UUID
from datetime import datetime, timezone

from readmaster_ai.application.use_cases.class_use_cases import (
    CreateClassUseCase, GetClassDetailsUseCase, ListClassesByTeacherUseCase,
    UpdateClassUseCase, DeleteClassUseCase, AddStudentToClassUseCase, RemoveStudentFromClassUseCase,
    ListStudentsInClassUseCase
)
from readmaster_ai.domain.entities.class_entity import ClassEntity as DomainClassEntity
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.domain.repositories.class_repository import ClassRepository
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.application.dto.class_dtos import ClassCreateDTO, ClassUpdateDTO, AddStudentToClassRequestDTO
from readmaster_ai.shared.exceptions import NotFoundException, ForbiddenException, ApplicationException

@pytest.fixture
def mock_class_repo() -> MagicMock:
    mock = MagicMock(spec=ClassRepository)
    mock.create = AsyncMock(side_effect=lambda cls: cls)
    mock.get_by_id = AsyncMock(return_value=None)
    mock.update = AsyncMock(side_effect=lambda cls: cls)
    mock.delete = AsyncMock(return_value=True)
    mock.list_by_teacher_id = AsyncMock(return_value=([], 0))
    mock.add_student_to_class = AsyncMock(return_value=True)
    mock.remove_student_from_class = AsyncMock(return_value=True)
    mock.get_students_in_class = AsyncMock(return_value=[])
    return mock

@pytest.fixture
def mock_user_repo_for_class() -> MagicMock:
    mock = MagicMock(spec=UserRepository)
    mock.get_by_id = AsyncMock(
        return_value=DomainUser(user_id=uuid4(), email="student.class@example.com", password_hash="s", role=UserRole.STUDENT)
    )
    return mock

@pytest.fixture
def sample_teacher_user() -> DomainUser:
    return DomainUser(user_id=uuid4(), email="teacher.class@example.com", password_hash="teacher_hash", role=UserRole.TEACHER)

@pytest.fixture
def sample_student_for_class(mock_user_repo_for_class: MagicMock) -> DomainUser:
    return mock_user_repo_for_class.get_by_id.return_value

@pytest.fixture
def sample_class_domain(sample_teacher_user: DomainUser) -> DomainClassEntity:
    return DomainClassEntity(
        class_id=uuid4(),
        class_name="Advanced Reading Group",
        grade_level="10",
        created_by_teacher_id=sample_teacher_user.user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# === CreateClassUseCase Tests ===
@pytest.mark.asyncio
async def test_create_class_success(mock_class_repo: MagicMock, sample_teacher_user: DomainUser):
    use_case = CreateClassUseCase(class_repo=mock_class_repo)
    create_dto = ClassCreateDTO(class_name="Creative Writing Workshop", grade_level="11-12")
    created_class = await use_case.execute(create_dto, sample_teacher_user)
    mock_class_repo.create.assert_called_once()
    call_args = mock_class_repo.create.call_args[0][0]
    assert isinstance(call_args, DomainClassEntity)
    assert call_args.class_name == "Creative Writing Workshop"
    assert call_args.created_by_teacher_id == sample_teacher_user.user_id
    assert created_class.class_name == "Creative Writing Workshop"

@pytest.mark.asyncio
async def test_create_class_by_student_forbidden(mock_class_repo: MagicMock, sample_student_for_class: DomainUser):
    use_case = CreateClassUseCase(class_repo=mock_class_repo)
    create_dto = ClassCreateDTO(class_name="Student's Secret Class")
    with pytest.raises(ForbiddenException):
        await use_case.execute(create_dto, sample_student_for_class)
    mock_class_repo.create.assert_not_called()

# === GetClassDetailsUseCase Tests ===
@pytest.mark.asyncio
async def test_get_class_details_success(mock_class_repo: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    use_case = GetClassDetailsUseCase(class_repo=mock_class_repo)
    class_details = await use_case.execute(sample_class_domain.class_id, sample_teacher_user)
    mock_class_repo.get_by_id.assert_called_once_with(sample_class_domain.class_id)
    assert class_details == sample_class_domain

@pytest.mark.asyncio
async def test_get_class_details_not_found(mock_class_repo: MagicMock, sample_teacher_user: DomainUser):
    mock_class_repo.get_by_id.return_value = None
    use_case = GetClassDetailsUseCase(class_repo=mock_class_repo)
    with pytest.raises(NotFoundException):
        await use_case.execute(uuid4(), sample_teacher_user)

@pytest.mark.asyncio
async def test_get_class_details_forbidden_not_owner(mock_class_repo: MagicMock, sample_class_domain: DomainClassEntity):
    other_teacher = DomainUser(user_id=uuid4(), email="other.teacher@example.com", password_hash="hash", role=UserRole.TEACHER)
    mock_class_repo.get_by_id.return_value = sample_class_domain
    use_case = GetClassDetailsUseCase(class_repo=mock_class_repo)
    with pytest.raises(ForbiddenException):
        await use_case.execute(sample_class_domain.class_id, other_teacher)

# === AddStudentToClassUseCase Tests ===
@pytest.mark.asyncio
async def test_add_student_to_class_success(mock_class_repo: MagicMock, mock_user_repo_for_class: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser, sample_student_for_class: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    mock_user_repo_for_class.get_by_id.return_value = sample_student_for_class
    use_case = AddStudentToClassUseCase(class_repo=mock_class_repo, user_repo=mock_user_repo_for_class)
    result = await use_case.execute(sample_class_domain.class_id, sample_student_for_class.user_id, sample_teacher_user)
    assert result is True
    mock_class_repo.add_student_to_class.assert_called_once_with(sample_class_domain.class_id, sample_student_for_class.user_id)

@pytest.mark.asyncio
async def test_add_student_to_class_student_not_found(mock_class_repo: MagicMock, mock_user_repo_for_class: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    mock_user_repo_for_class.get_by_id.return_value = None
    use_case = AddStudentToClassUseCase(class_repo=mock_class_repo, user_repo=mock_user_repo_for_class)
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(sample_class_domain.class_id, uuid4(), sample_teacher_user)
    assert "Student" in exc_info.value.message
    mock_class_repo.add_student_to_class.assert_not_called()

# === ListClassesByTeacherUseCase Tests ===
@pytest.mark.asyncio
async def test_list_classes_by_teacher_success(mock_class_repo: MagicMock, sample_teacher_user: DomainUser, sample_class_domain: DomainClassEntity):
    mock_class_repo.list_by_teacher_id.return_value = ([sample_class_domain], 1)
    use_case = ListClassesByTeacherUseCase(class_repo=mock_class_repo)
    classes, total = await use_case.execute(teacher=sample_teacher_user, page=1, size=10)
    mock_class_repo.list_by_teacher_id.assert_called_once_with(sample_teacher_user.user_id, 1, 10)
    assert len(classes) == 1
    assert total == 1
    assert classes[0] == sample_class_domain

@pytest.mark.asyncio
async def test_list_classes_by_teacher_forbidden_not_teacher_or_admin(mock_class_repo: MagicMock):
    non_authorized_user = DomainUser(user_id=uuid4(), email="student@example.com", password_hash="s", role=UserRole.STUDENT)
    use_case = ListClassesByTeacherUseCase(class_repo=mock_class_repo)
    with pytest.raises(ForbiddenException):
        await use_case.execute(teacher=non_authorized_user, page=1, size=10)
    mock_class_repo.list_by_teacher_id.assert_not_called()

# === UpdateClassUseCase Tests ===
@pytest.mark.asyncio
async def test_update_class_success(mock_class_repo: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    use_case = UpdateClassUseCase(class_repo=mock_class_repo)
    update_dto = ClassUpdateDTO(class_name="Updated Class Name", grade_level="11")
    class_to_update = DomainClassEntity(
        class_id=sample_class_domain.class_id,
        class_name=sample_class_domain.class_name,
        grade_level=sample_class_domain.grade_level,
        created_by_teacher_id=sample_class_domain.created_by_teacher_id,
        created_at=sample_class_domain.created_at,
        updated_at=sample_class_domain.updated_at
    )
    class_to_update.updated_at = sample_class_domain.updated_at
    original_updated_at = class_to_update.updated_at
    updated_class = await use_case.execute(class_to_update.class_id, update_dto, sample_teacher_user)
    mock_class_repo.get_by_id.assert_called_once_with(class_to_update.class_id)
    mock_class_repo.update.assert_called_once()
    updated_class_arg_to_repo = mock_class_repo.update.call_args[0][0]
    assert updated_class_arg_to_repo.class_name == "Updated Class Name"
    assert updated_class_arg_to_repo.grade_level == "11"
    assert updated_class_arg_to_repo.updated_at > original_updated_at
    assert updated_class.class_name == "Updated Class Name"

# === DeleteClassUseCase Tests ===
@pytest.mark.asyncio
async def test_delete_class_success(mock_class_repo: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    mock_class_repo.delete.return_value = True
    use_case = DeleteClassUseCase(class_repo=mock_class_repo)
    result = await use_case.execute(sample_class_domain.class_id, sample_teacher_user)
    assert result is True
    mock_class_repo.delete.assert_called_once_with(sample_class_domain.class_id)

# === RemoveStudentFromClassUseCase Tests ===
@pytest.mark.asyncio
async def test_remove_student_from_class_success(mock_class_repo: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser, sample_student_for_class: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    mock_class_repo.remove_student_from_class.return_value = True
    use_case = RemoveStudentFromClassUseCase(class_repo=mock_class_repo)
    result = await use_case.execute(sample_class_domain.class_id, sample_student_for_class.user_id, sample_teacher_user)
    assert result is True
    mock_class_repo.get_by_id.assert_called_once_with(sample_class_domain.class_id)
    mock_class_repo.remove_student_from_class.assert_called_once_with(sample_class_domain.class_id, sample_student_for_class.user_id)

# === ListStudentsInClassUseCase Tests ===
@pytest.mark.asyncio
async def test_list_students_in_class_success(mock_class_repo: MagicMock, sample_class_domain: DomainClassEntity, sample_teacher_user: DomainUser, sample_student_for_class: DomainUser):
    sample_class_domain.created_by_teacher_id = sample_teacher_user.user_id
    mock_class_repo.get_by_id.return_value = sample_class_domain
    mock_class_repo.get_students_in_class.return_value = [sample_student_for_class]
    use_case = ListStudentsInClassUseCase(class_repo=mock_class_repo)
    students_list = await use_case.execute(sample_class_domain.class_id, sample_teacher_user)
    mock_class_repo.get_by_id.assert_called_once_with(sample_class_domain.class_id)
    mock_class_repo.get_students_in_class.assert_called_once_with(sample_class_domain.class_id)
    assert len(students_list) == 1
    assert students_list[0] == sample_student_for_class
