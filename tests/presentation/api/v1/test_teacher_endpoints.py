# tests/presentation/api/v1/test_teacher_endpoints.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func # For DB checks
from typing import List # For type hints
from unittest.mock import patch, MagicMock, AsyncMock # For mocking NotificationService.notify

# Application components
from src.readmaster_ai.domain.entities.user import DomainUser
from src.readmaster_ai.domain.value_objects.common_enums import UserRole, AssessmentStatus, DifficultyLevel
from src.readmaster_ai.application.services.auth_service import AuthenticationService
from src.readmaster_ai.infrastructure.database.models import (
    ClassModel, UserModel, StudentsClassesAssociation,
    ReadingModel, AssessmentModel
)
from src.readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # For creating teacher/student
from passlib.context import CryptContext # For hashing passwords

# Fixtures and helpers from conftest.py
from tests.conftest import get_auth_headers_for_user # Explicit import for clarity

@pytest_asyncio.fixture(scope="function")
async def teacher_user(db_session: AsyncSession) -> DomainUser:
    """Fixture to create a dedicated teacher user for these tests."""
    user_repo = UserRepositoryImpl(db_session)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    teacher_id = uuid4()
    teacher_email = f"teacher_content_tests_{teacher_id}@example.com"

    existing_teacher = await user_repo.get_by_email(teacher_email)
    if existing_teacher:
        return existing_teacher

    teacher_domain = DomainUser(
        user_id=teacher_id,
        email=teacher_email,
        password_hash=pwd_context.hash("teacher_password123"),
        first_name="DedicatedTeacher",
        last_name="ForTests",
        role=UserRole.TEACHER
    )
    created_teacher = await user_repo.create(teacher_domain)
    await db_session.commit() # Commit to make it available for API calls
    return created_teacher

@pytest.fixture
def teacher_auth_headers(teacher_user: DomainUser, auth_service_for_test_tokens: AuthenticationService) -> dict:
    """Fixture to get authentication headers for the teacher_user."""
    return get_auth_headers_for_user(teacher_user, auth_service_for_test_tokens)

@pytest_asyncio.fixture(scope="function")
async def student_for_class_tests(db_session: AsyncSession) -> UserModel:
    """Fixture to create a student UserModel directly for class tests."""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    student_id = uuid4()
    student_email = f"student_for_class_{student_id}@example.com"

    # Check if student exists to avoid unique constraint errors if tests run without full DB teardown/recreation
    # This is more of a safeguard; conftest.py's setup_test_database should handle clean slate.
    stmt = select(UserModel).where(UserModel.email == student_email)
    existing = (await db_session.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing

    student = UserModel(
        user_id=student_id,
        email=student_email,
        password_hash=pwd_context.hash("studentpass123"),
        role=UserRole.STUDENT.value,
        first_name="ClassStudent"
    )
    db_session.add(student)
    await db_session.commit()
    return student


# === Class Management Tests ===
@pytest.mark.asyncio
async def test_teacher_create_class_success(async_client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession, teacher_user: DomainUser):
    class_data = {"class_name": "Literacy Group Alpha", "grade_level": "3"}
    response = await async_client.post("/api/v1/teacher/classes", json=class_data, headers=teacher_auth_headers)

    assert response.status_code == 201, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["class_name"] == class_data["class_name"]
    assert response_json["created_by_teacher_id"] == str(teacher_user.user_id)
    class_id = UUID(response_json["class_id"])

    db_class = await db_session.get(ClassModel, class_id)
    assert db_class is not None
    assert db_class.class_name == class_data["class_name"]

@pytest.mark.asyncio
async def test_teacher_list_classes_success(async_client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession, teacher_user: DomainUser):
    c1 = ClassModel(class_id=uuid4(), class_name="History Buffs", created_by_teacher_id=teacher_user.user_id)
    c2 = ClassModel(class_id=uuid4(), class_name="Science Geeks", created_by_teacher_id=teacher_user.user_id)
    db_session.add_all([c1, c2])
    await db_session.commit()

    response = await async_client.get("/api/v1/teacher/classes", headers=teacher_auth_headers)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["total"] == 2
    assert len(response_json["items"]) == 2
    class_names_in_response = {c["class_name"] for c in response_json["items"]}
    assert "History Buffs" in class_names_in_response
    assert "Science Geeks" in class_names_in_response

@pytest.mark.asyncio
async def test_teacher_add_student_to_class_success(async_client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession, teacher_user: DomainUser, student_for_class_tests: UserModel):
    class_model = ClassModel(class_id=uuid4(), class_name="Robotics Club", created_by_teacher_id=teacher_user.user_id)
    db_session.add(class_model)
    await db_session.commit()

    add_student_data = {"student_id": str(student_for_class_tests.user_id)}
    # API returns updated class details (including student list) with 200 OK
    response = await async_client.post(f"/api/v1/teacher/classes/{class_model.class_id}/students", json=add_student_data, headers=teacher_auth_headers)
    assert response.status_code == 200, f"Response: {response.text}"

    response_json = response.json()
    assert len(response_json["students"]) == 1
    assert response_json["students"][0]["user_id"] == str(student_for_class_tests.user_id)

    # Verify association in DB
    stmt = select(StudentsClassesAssociation).where(
        StudentsClassesAssociation.c.class_id == class_model.class_id,
        StudentsClassesAssociation.c.student_id == student_for_class_tests.user_id
    )
    assoc = (await db_session.execute(stmt)).first()
    assert assoc is not None

@pytest.mark.asyncio
async def test_teacher_list_students_in_class(async_client: AsyncClient, teacher_auth_headers: dict, db_session: AsyncSession, teacher_user: DomainUser, student_for_class_tests: UserModel):
    class_model = ClassModel(class_id=uuid4(), class_name="Art History", created_by_teacher_id=teacher_user.user_id)
    db_session.add(class_model)
    await db_session.commit()

    assoc_stmt = StudentsClassesAssociation.insert().values(class_id=class_model.class_id, student_id=student_for_class_tests.user_id)
    await db_session.execute(assoc_stmt)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/teacher/classes/{class_model.class_id}/students", headers=teacher_auth_headers)
    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert len(response_json) == 1
    assert response_json[0]["user_id"] == str(student_for_class_tests.user_id)
    assert response_json[0]["first_name"] == student_for_class_tests.first_name


# === Reading Assignment Tests ===
@pytest_asyncio.fixture(scope="function")
async def reading_for_assignment(db_session: AsyncSession) -> ReadingModel:
    """Fixture to create a ReadingModel for assignment tests."""
    reading = ReadingModel(reading_id=uuid4(), title="The Raven", added_by_admin_id=uuid4(), language="en")
    db_session.add(reading)
    await db_session.commit()
    return reading

@pytest.mark.asyncio
@patch('src.readmaster_ai.application.use_cases.assessment_use_cases.NotificationService.notify', new_callable=AsyncMock)
async def test_teacher_assign_reading_to_students_success(
    mock_notify: MagicMock, async_client: AsyncClient, teacher_auth_headers: dict,
    reading_for_assignment: ReadingModel, student_for_class_tests: UserModel,
    db_session: AsyncSession, teacher_user: DomainUser
):
    """Tests assigning a reading to a specific list of students."""
    assign_data = {
        "reading_id": str(reading_for_assignment.reading_id),
        "student_ids": [str(student_for_class_tests.user_id)]
    }
    response = await async_client.post("/api/v1/teacher/assignments/readings", json=assign_data, headers=teacher_auth_headers)

    assert response.status_code == 201, f"Response: {response.text}"
    response_json = response.json()
    assert len(response_json["created_assessments"]) == 1
    created_assessment_info = response_json["created_assessments"][0]
    assert created_assessment_info["student_id"] == str(student_for_class_tests.user_id)
    assert created_assessment_info["reading_id"] == str(reading_for_assignment.reading_id)
    assert created_assessment_info["status"] == AssessmentStatus.PENDING_AUDIO.value

    stmt = select(AssessmentModel).where(
        AssessmentModel.student_id == student_for_class_tests.user_id,
        AssessmentModel.reading_id == reading_for_assignment.reading_id
    )
    db_assessment = (await db_session.execute(stmt)).scalar_one_or_none()
    assert db_assessment is not None
    assert db_assessment.assigned_by_teacher_id == teacher_user.user_id

    mock_notify.assert_called_once() # Check if notification service was triggered

@pytest.mark.asyncio
@patch('src.readmaster_ai.application.use_cases.assessment_use_cases.NotificationService.notify', new_callable=AsyncMock)
async def test_teacher_assign_reading_to_class_success(
    mock_notify: MagicMock, async_client: AsyncClient, teacher_auth_headers: dict,
    reading_for_assignment: ReadingModel, student_for_class_tests: UserModel,
    db_session: AsyncSession, teacher_user: DomainUser
):
    """Tests assigning a reading to all students in a class."""
    class_model = ClassModel(class_id=uuid4(), class_name="English Lit 101", created_by_teacher_id=teacher_user.user_id)
    db_session.add(class_model)
    await db_session.commit()

    assoc_stmt = StudentsClassesAssociation.insert().values(class_id=class_model.class_id, student_id=student_for_class_tests.user_id)
    await db_session.execute(assoc_stmt)
    await db_session.commit()

    assign_data = {
        "reading_id": str(reading_for_assignment.reading_id),
        "class_id": str(class_model.class_id)
    }
    response = await async_client.post("/api/v1/teacher/assignments/readings", json=assign_data, headers=teacher_auth_headers)

    assert response.status_code == 201, f"Response: {response.text}"
    response_json = response.json()
    assert len(response_json["created_assessments"]) == 1

    # Verify assessment for the student in the class
    db_assessment_count_stmt = select(func.count(AssessmentModel.assessment_id)).select_from(AssessmentModel).where(
        AssessmentModel.reading_id == reading_for_assignment.reading_id,
        AssessmentModel.assigned_by_teacher_id == teacher_user.user_id,
        AssessmentModel.student_id == student_for_class_tests.user_id # Check for this specific student
    )
    db_assessment_count = (await db_session.execute(db_assessment_count_stmt)).scalar_one()
    assert db_assessment_count == 1

    mock_notify.assert_called_once()

# Placeholder for more tests:
# - Test GET /teacher/classes/{class_id} (verify student list population in response)
# - Test PUT /teacher/classes/{class_id} (update class details)
# - Test DELETE /teacher/classes/{class_id} (delete a class)
# - Test DELETE /teacher/classes/{class_id}/students/{student_id} (remove student from class)
# - Test various error conditions for all endpoints (e.g., not found, forbidden for different teacher)
# - Test assigning reading to class with no students, or to specific non-existent students.
