# tests/presentation/api/v1/test_user_auth_endpoints.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Application components
from src.readmaster_ai.infrastructure.database.models import UserModel
from src.readmaster_ai.domain.value_objects.common_enums import UserRole # Enum for role checks/assertions
from src.readmaster_ai.application.services.auth_service import AuthenticationService
from src.readmaster_ai.domain.entities.user import DomainUser

# Fixtures from conftest.py (async_client, db_session, test_user, auth_service_for_test_tokens)
# and helper get_auth_headers_for_user will be automatically available.
# Make sure to import helper if it's not implicitly available via pytest magic.
from tests.conftest import get_auth_headers_for_user


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient, db_session: AsyncSession):
    """Test successful user registration."""
    user_email = f"test_register_{uuid4()}@example.com"
    user_data = {
        "email": user_email,
        "password": "password123",
        "first_name": "Register",
        "last_name": "User",
        "role": UserRole.STUDENT.value, # Send the string value for role enum
        "preferred_language": "fr"
    }
    response = await async_client.post("/api/v1/users/register", json=user_data)

    assert response.status_code == 201, f"Response content: {response.text}"
    response_json = response.json()
    assert response_json["email"] == user_email
    assert response_json["first_name"] == "Register"
    assert response_json["role"] == UserRole.STUDENT.value
    assert response_json["preferred_language"] == "fr"
    assert "user_id" in response_json

    # Verify user was actually created in the database
    stmt = select(UserModel).where(UserModel.email == user_email)
    db_user_model = (await db_session.execute(stmt)).scalar_one_or_none()
    assert db_user_model is not None
    assert db_user_model.first_name == "Register"
    assert db_user_model.preferred_language == "fr"
    # Note: db_session is rolled back after test, so this user won't persist for other tests.

@pytest.mark.asyncio
async def test_register_user_duplicate_email(async_client: AsyncClient, test_user: DomainUser):
    """Test registration attempt with an email that already exists."""
    # test_user fixture (from conftest.py) already creates a user.
    user_data = {
        "email": test_user.email, # Use email from the fixture-created user
        "password": "newpassword123",
        "first_name": "DuplicateFirstName",
        "role": UserRole.TEACHER.value
    }
    response = await async_client.post("/api/v1/users/register", json=user_data)

    assert response.status_code == 409 # HTTP 409 Conflict
    response_json = response.json()
    assert "Email already registered" in response_json["detail"]


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, test_user: DomainUser):
    """Test successful user login with correct credentials."""
    # The test_user fixture (from conftest.py) should create a user with a known raw password,
    # e.g., "testpassword", which is then hashed.
    login_data = {"email": test_user.email, "password": "testpassword"} # Raw password from conftest.py
    response = await async_client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200, f"Response content: {response.text}"
    response_json = response.json()
    assert "access_token" in response_json
    assert "refresh_token" in response_json
    assert response_json["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials_wrong_password(async_client: AsyncClient, test_user: DomainUser):
    """Test login attempt with correct email but wrong password."""
    login_data = {"email": test_user.email, "password": "thisisawrongpassword"}
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_invalid_credentials_wrong_email(async_client: AsyncClient):
    """Test login attempt with a non-existent email."""
    login_data = {"email": f"nonexistent_{uuid4()}@example.com", "password": "anypassword"}
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_me_success(
    async_client: AsyncClient,
    test_user: DomainUser, # Fixture provides a created user
    auth_service_for_test_tokens: AuthenticationService # Fixture provides auth service with test DB context
):
    """Test retrieving current user's details using a valid access token."""
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)

    response = await async_client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200, f"Response content: {response.text}"
    response_json = response.json()
    assert response_json["email"] == test_user.email
    assert response_json["user_id"] == str(test_user.user_id) # Ensure UUIDs are compared as strings if needed
    assert response_json["first_name"] == test_user.first_name
    assert response_json["role"] == test_user.role.value


@pytest.mark.asyncio
async def test_get_current_user_me_unauthenticated(async_client: AsyncClient):
    """Test accessing /me endpoint without authentication token."""
    response = await async_client.get("/api/v1/users/me") # No Authorization header
    assert response.status_code == 401 # Expect 401 Unauthorized
    # Detail might vary based on FastAPI's default for OAuth2PasswordBearer missing token
    # assert "Not authenticated" in response.json()["detail"] # Or similar, check actual response

@pytest.mark.asyncio
async def test_update_current_user_me_success(
    async_client: AsyncClient,
    test_user: DomainUser,
    auth_service_for_test_tokens: AuthenticationService,
    db_session: AsyncSession # For DB verification
):
    """Test successfully updating current user's profile."""
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)

    update_data = {
        "first_name": "FirstNameUpdatedByAPI",
        "last_name": "LastNameUpdatedByAPI",
        "preferred_language": "es"
        # Email update is also tested, but here we focus on other fields.
    }
    response = await async_client.put("/api/v1/users/me", json=update_data, headers=auth_headers)

    assert response.status_code == 200, f"Response content: {response.text}"
    response_json = response.json()
    assert response_json["first_name"] == "FirstNameUpdatedByAPI"
    assert response_json["last_name"] == "LastNameUpdatedByAPI"
    assert response_json["preferred_language"] == "es"
    assert response_json["email"] == test_user.email # Email should remain unchanged if not in update_data

    # Verify the update in the database
    updated_db_user = await db_session.get(UserModel, test_user.user_id)
    assert updated_db_user is not None
    assert updated_db_user.first_name == "FirstNameUpdatedByAPI"
    assert updated_db_user.preferred_language == "es"

@pytest.mark.asyncio
async def test_update_current_user_me_change_email_conflict(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user: DomainUser, # This is the user whose token we'll use
    auth_service_for_test_tokens: AuthenticationService
):
    """Test updating email to one that's already taken by another user."""
    # 1. Create "other_user" whose email "test_user" will try to take.
    other_user_email = f"other_user_for_conflict_{uuid4()}@example.com"
    other_user_password = "other_password"
    # Using the register endpoint to create this other user easily.
    # Note: This relies on the register endpoint working correctly.
    # Alternatively, create directly via repository if preferred for isolation, but API test is fine.
    register_payload = {
        "email": other_user_email, "password": other_user_password, "role": UserRole.STUDENT.value
    }
    reg_response = await async_client.post("/api/v1/users/register", json=register_payload)
    assert reg_response.status_code == 201 # Ensure other user was created

    # 2. test_user attempts to update their email to other_user_email
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)
    update_data_conflict_email = {"email": other_user_email}

    response = await async_client.put("/api/v1/users/me", json=update_data_conflict_email, headers=auth_headers)

    assert response.status_code == 409 # HTTP 409 Conflict
    response_json = response.json()
    assert "email is already registered by another user" in response_json["detail"]

    # Ensure test_user's email has not changed in DB
    original_user_db = await db_session.get(UserModel, test_user.user_id)
    assert original_user_db is not None
    assert original_user_db.email == test_user.email # Should still be the original email
