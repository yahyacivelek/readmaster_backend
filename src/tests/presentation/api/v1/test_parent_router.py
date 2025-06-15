import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession # For type hinting if needed by fixtures
import uuid # Standard uuid, changed from uuid_extensions

# Assuming main.py configures the FastAPI app instance
# Adjust the import path according to your project structure
from readmaster_ai.main import app
from readmaster_ai.presentation.schemas.user_schemas import UserResponse, ParentChildCreateRequestSchema
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.domain.entities.user import DomainUser # Added for explicit DomainUser usage
from unittest.mock import AsyncMock # For mocking use case instance

# It's common to have a conftest.py to provide fixtures like:
# - TestClient instance
# - Override dependencies (like get_db for a test database, get_current_user for auth)
# - Functions to create test users with specific roles and get their tokens

# For this subtask, we'll define minimal fixtures here or assume they exist.
# A more robust setup would use a shared conftest.py.

# --- Mocking Authentication and DB ---
# These would typically be in conftest.py and more sophisticated.

# Fixture to provide a TestClient
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Fixture to create a header for an authenticated parent user
# This is a simplified mock. Real tests would involve creating a user in the test DB
# and using their actual token, or a more robust mock of get_current_user.
@pytest.fixture
def parent_auth_headers():
    # This token is fake and won't pass real JWT validation.
    # We'd need to override get_current_user dependency in the app for tests.
    # For now, this illustrates the need.
    # Let's assume a dependency override for get_current_user is set up elsewhere (e.g. conftest.py)
    # that makes this token work or bypasses actual token validation for tests.
    # For the purpose of this script, we'll assume that the test setup handles making this valid.
    return {"Authorization": "Bearer fake-parent-token"}

@pytest.fixture
def teacher_auth_headers(): # For testing role restriction
    return {"Authorization": "Bearer fake-teacher-token"}


# Example of how get_current_user might be overridden in tests (conceptual, usually in conftest.py)
# from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
# from readmaster_ai.domain.entities.user import DomainUser
# def override_get_current_parent():
#     return DomainUser(user_id=uuid.uuid4(), email="testparent@example.com", role=UserRole.PARENT)
# def override_get_current_teacher():
#     return DomainUser(user_id=uuid.uuid4(), email="testteacher@example.com", role=UserRole.TEACHER)
# app.dependency_overrides[get_current_user] = override_get_current_parent # In a test setup function

@pytest.mark.asyncio # Pytest-asyncio might not be needed if TestClient handles async routes correctly
async def test_parent_create_child_success(client, parent_auth_headers, monkeypatch):
    # Assume get_current_user is overridden to return a parent for parent_auth_headers
    # Assume a clean test database for each test or manage data carefully.

    # Mock the use case execution to avoid actual DB writes in this example if DB is not fully mocked/managed
    # A true integration test would hit the DB. For now, let's mock the service call
    # to ensure the routing and request/response handling works.
    # If we want to test the full flow including DB, then repository methods would be called.

    # For a true integration test, we would not mock the use case, but ensure the DB is clean
    # and verify DB state after the call.
    # For now, this test focuses more on the router logic, request/response, and auth.

    # To make this test runnable without full DB setup, we can mock the use case dependency
    # This is closer to a functional test for the endpoint handler.
    mock_created_student_domain = DomainUser(
        user_id=uuid.uuid4(),
        email="newchild@example.com",
        first_name="New",
        last_name="Child",
        role=UserRole.STUDENT,
        preferred_language="en"
    )

    # async def mock_use_case_execute(*args, **kwargs):
    #     return mock_created_student_domain

    from readmaster_ai.application.use_cases.parent_use_cases import CreateStudentByParentUseCase
    # This monkeypatch needs to target where CreateStudentByParentUseCase is *looked up* by FastAPI's Depends
    # which is typically the module where the dependency providing function is.
    # Or, override the dependency get_create_student_by_parent_use_case directly.
    # For simplicity of this script, we'll assume the test client setup allows this or we test without this deep mock.

    # A better way for FastAPI is to override the dependency that provides the use case:
    from readmaster_ai.presentation.api.v1.parent_router import get_create_student_by_parent_use_case
    # def override_get_create_student_by_parent_use_case():
    #     mock_uc_instance = AsyncMock(spec=CreateStudentByParentUseCase)
    #     mock_uc_instance.execute.return_value = mock_created_student_domain
    #     return mock_uc_instance
    # app.dependency_overrides[get_create_student_by_parent_use_case] = override_get_create_student_by_parent_use_case


    child_payload = {
        "email": "newchild@example.com",
        "password": "password123",
        "first_name": "New",
        "last_name": "Child",
        "preferred_language": "en"
    }

    # Setup dependency override for this test
    # This is a common pattern for testing FastAPI endpoints
    mock_uc_instance = AsyncMock(spec=CreateStudentByParentUseCase)
    mock_uc_instance.execute.return_value = mock_created_student_domain

    app.dependency_overrides[get_create_student_by_parent_use_case] = lambda: mock_uc_instance
    # Also override get_current_user for this specific test context if not globally done
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testparent@example.com", role=UserRole.PARENT)


    response = client.post("/api/v1/parent/children", json=child_payload, headers=parent_auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newchild@example.com"
    assert data["first_name"] == "New"
    assert data["role"] == "student" # UserRole.STUDENT.value
    assert "user_id" in data

    # Clean up dependency overrides
    del app.dependency_overrides[get_create_student_by_parent_use_case]
    del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_parent_create_child_email_exists(client, parent_auth_headers):
    from readmaster_ai.presentation.api.v1.parent_router import get_create_student_by_parent_use_case
    from readmaster_ai.application.use_cases.parent_use_cases import CreateStudentByParentUseCase
    from readmaster_ai.shared.exceptions import ApplicationException

    mock_uc_instance = AsyncMock(spec=CreateStudentByParentUseCase)
    mock_uc_instance.execute.side_effect = ApplicationException("Email already exists.", status_code=409)

    app.dependency_overrides[get_create_student_by_parent_use_case] = lambda: mock_uc_instance
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testparent@example.com", role=UserRole.PARENT)

    child_payload = {"email": "existing@example.com", "password": "password123"}
    response = client.post("/api/v1/parent/children", json=child_payload, headers=parent_auth_headers)

    assert response.status_code == 409 # Or the status_code from ApplicationException
    assert "Email already exists" in response.json()["detail"]

    del app.dependency_overrides[get_create_student_by_parent_use_case]
    del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_parent_create_child_unauthorized_wrong_role(client, teacher_auth_headers): # Use teacher token
    # Assuming get_current_user override for teacher_auth_headers returns a TEACHER role user
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testteacher@example.com", role=UserRole.TEACHER)

    child_payload = {"email": "anychild@example.com", "password": "password123"}
    response = client.post("/api/v1/parent/children", json=child_payload, headers=teacher_auth_headers)

    # The parent_router has a router-level dependency `Depends(require_role(UserRole.PARENT))`.
    # This should trigger a 403 if the user is not a Parent.
    assert response.status_code == 403
    assert "User does not have the required role(s)" in response.json()["detail"] # Message from require_role

    del app.dependency_overrides[get_current_user]

@pytest.mark.asyncio
async def test_parent_create_child_invalid_payload(client, parent_auth_headers):
    from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: DomainUser(user_id=uuid.uuid4(), email="testparent@example.com", role=UserRole.PARENT)

    # Missing required 'password' field
    child_payload = {"email": "incomplete@example.com"}
    response = client.post("/api/v1/parent/children", json=child_payload, headers=parent_auth_headers)
    assert response.status_code == 422 # Unprocessable Entity for Pydantic validation errors

    del app.dependency_overrides[get_current_user]
