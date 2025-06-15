import pytest
from fastapi.testclient import TestClient
import uuid # Standard uuid
from unittest.mock import AsyncMock # For mocking use case instance

from readmaster_ai.main import app # Main FastAPI app
from readmaster_ai.presentation.schemas.user_schemas import UserResponse, TeacherStudentCreateRequestSchema
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.domain.entities.user import DomainUser

# Fixtures (client is module-scoped, auth headers are function-scoped for clarity)
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def teacher_auth_headers():
    # This token is conceptual. Relies on get_current_user override.
    return {"Authorization": "Bearer fake-teacher-token"}

@pytest.fixture
def parent_auth_headers(): # For testing role restriction
    return {"Authorization": "Bearer fake-parent-token"}

@pytest.mark.asyncio
async def test_teacher_create_student_success(client, teacher_auth_headers):
    from readmaster_ai.presentation.api.v1.teacher_router import get_create_student_by_teacher_use_case
    from readmaster_ai.application.use_cases.user_use_cases import CreateStudentByTeacherUseCase
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user

    mock_created_student_domain = DomainUser(
        user_id=uuid.uuid4(),
        email="newlycreated@example.com",
        first_name="NewLy",
        last_name="Created",
        role=UserRole.STUDENT,
        preferred_language="es"
    )

    mock_uc_instance = AsyncMock(spec=CreateStudentByTeacherUseCase)
    mock_uc_instance.execute.return_value = mock_created_student_domain

    app.dependency_overrides[get_create_student_by_teacher_use_case] = lambda: mock_uc_instance
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testteacher@example.com", role=UserRole.TEACHER)

    student_payload = {
        "email": "newlycreated@example.com",
        "password": "securepassword",
        "first_name": "NewLy",
        "last_name": "Created",
        "preferred_language": "es"
    }

    response = client.post("/api/v1/teacher/students", json=student_payload, headers=teacher_auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newlycreated@example.com"
    assert data["first_name"] == "NewLy"
    assert data["role"] == "student"
    assert "user_id" in data

    del app.dependency_overrides[get_create_student_by_teacher_use_case]
    del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
async def test_teacher_create_student_email_exists(client, teacher_auth_headers):
    from readmaster_ai.presentation.api.v1.teacher_router import get_create_student_by_teacher_use_case
    from readmaster_ai.application.use_cases.user_use_cases import CreateStudentByTeacherUseCase
    from readmaster_ai.shared.exceptions import ApplicationException
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user

    mock_uc_instance = AsyncMock(spec=CreateStudentByTeacherUseCase)
    mock_uc_instance.execute.side_effect = ApplicationException("Email already taken.", status_code=409)

    app.dependency_overrides[get_create_student_by_teacher_use_case] = lambda: mock_uc_instance
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testteacher@example.com", role=UserRole.TEACHER)

    student_payload = {"email": "existingstudent@example.com", "password": "password"}
    response = client.post("/api/v1/teacher/students", json=student_payload, headers=teacher_auth_headers)

    assert response.status_code == 409
    assert "Email already taken" in response.json()["detail"]

    del app.dependency_overrides[get_create_student_by_teacher_use_case]
    del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
async def test_teacher_create_student_unauthorized_wrong_role(client, parent_auth_headers): # Use parent token
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testparent@example.com", role=UserRole.PARENT)

    student_payload = {"email": "studentbywrongrole@example.com", "password": "password"}
    response = client.post("/api/v1/teacher/students", json=student_payload, headers=parent_auth_headers)

    # teacher_router has router-level `Depends(require_role(UserRole.TEACHER))`
    assert response.status_code == 403
    assert "User does not have the required role(s)" in response.json()["detail"]

    del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
async def test_teacher_create_student_invalid_payload(client, teacher_auth_headers):
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testteacher@example.com", role=UserRole.TEACHER)

    # Missing 'email'
    student_payload = {"password": "password123"}
    response = client.post("/api/v1/teacher/students", json=student_payload, headers=teacher_auth_headers)
    assert response.status_code == 422

    del app.dependency_overrides[get_current_user]
