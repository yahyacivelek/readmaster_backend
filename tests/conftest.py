# tests/conftest.py
import asyncio
import os
from typing import AsyncGenerator, Generator, Any, Dict # Added Dict for get_auth_headers_for_user
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio # For async fixtures
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool # Use NullPool for test database connections

# Application components to be tested or overridden
from src.readmaster_ai.main import app as fastapi_app
from src.readmaster_ai.infrastructure.database.models import Base
from src.readmaster_ai.infrastructure.database.config import get_db as app_get_db # Original get_db
# DATABASE_URL as APP_DATABASE_URL is not needed if we define TEST_DATABASE_URL directly

# Core components for testing
from src.readmaster_ai.core.config import jwt_settings # For auth service if it uses global settings
from src.readmaster_ai.domain.entities.user import User as DomainUser # For type hints and test_user
from src.readmaster_ai.domain.value_objects.common_enums import UserRole # For creating test user
from src.readmaster_ai.application.services.auth_service import AuthenticationService # For generating test tokens
from src.readmaster_ai.infrastructure.database.models import UserModel # For creating test user in DB

# --- Test Database Configuration ---
# Use a separate database for testing to avoid conflicts with development data.
# Ensure this database exists and the user has permissions.
# It will be wiped and recreated (tables dropped/created) for each test session.
DEFAULT_TEST_DB_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/readmaster_test_db"
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DB_URL)

# --- Test Engine and Session Setup ---
# Create an async engine for the test database. NullPool is recommended for tests
# to ensure connections are closed properly and don't interfere between tests.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False) # Set echo=True for debugging SQL

# Create a sessionmaker for creating test database sessions.
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

# --- Pytest Event Loop Fixture ---
# This fixture provides the asyncio event loop for the test session.
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Ensure a single event loop for the whole test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# --- Test Database Setup and Teardown Fixture ---
# This session-scoped autouse fixture sets up the test database once per session.
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Drops and recreates all tables in the test database at the start of a test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Clear any existing tables
        await conn.run_sync(Base.metadata.create_all) # Create tables based on current models
    yield # Tests run after this
    # Optional: Teardown (e.g., drop tables again) - usually not needed if DB is test-specific
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose() # Dispose of the engine once all tests are done

# --- FastAPI Dependency Override for Database Sessions ---
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency override for get_db.
    Provides a test database session that is part of a transaction,
    which is rolled back after each test to ensure test isolation.
    """
    async with TestingSessionLocal() as session:
        # Begin a transaction. Using begin_nested if already in transaction,
        # though for function-scoped fixtures, it's typically the start of a new one.
        # Not using begin_nested() here as each test should get a fresh top-level transaction context.
        await session.begin()
        try:
            yield session
        finally:
            # Rollback the transaction after the test to undo any changes
            await session.rollback()
            await session.close() # Close the session

# --- Fixture for the FastAPI application with DB override ---
@pytest.fixture(scope="function") # function scope to ensure clean app state for each test
def test_app_with_db_override() -> fastapi_app:
    """
    Provides the FastAPI application instance with the get_db dependency
    overridden to use the test database session.
    """
    fastapi_app.dependency_overrides[app_get_db] = override_get_db
    yield fastapi_app # The test runs with this app instance
    fastapi_app.dependency_overrides.clear() # Clean up overrides after the test

# --- Fixture for a Test Database Session ---
# This provides a direct session for tests that need to interact with the DB outside of API calls.
@pytest_asyncio.fixture(scope="function")
async def db_session(test_app_with_db_override: Any) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a test database session that is automatically rolled back.
    Ensures that the app's DB dependency is overridden for this session's scope.
    """
    async with TestingSessionLocal() as session:
        await session.begin() # Start a transaction
        try:
            yield session
        finally:
            await session.rollback() # Ensure test isolation
            await session.close()

# --- Fixture for an Async HTTP Client ---
# This client is configured to make requests to the test_app_with_db_override.
@pytest_asyncio.fixture(scope="function")
async def async_client(test_app_with_db_override: Any) -> AsyncGenerator[AsyncClient, None]:
    """Provides an HTTPX AsyncClient for making API requests to the test application."""
    async with AsyncClient(app=test_app_with_db_override, base_url="http://testserver") as client:
        yield client

# --- Fixture for a Default Test User ---
@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> DomainUser:
    """
    Creates a test user (STUDENT role) in the database for use in tests.
    The user is committed within the test's transaction context provided by db_session.
    Returns the DomainUser entity.
    """
    from passlib.context import CryptContext # Local import to avoid top-level if only here
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    unique_id = uuid4()
    unique_email = f"testuser_{unique_id}@example.com"

    user_model = UserModel(
        user_id=unique_id,
        email=unique_email,
        password_hash=pwd_context.hash("testpassword"),
        first_name="Test",
        last_name="User",
        role=UserRole.STUDENT.value, # Store enum value in DB
        preferred_language="en",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user_model)
    # This commit is to the nested transaction of db_session for this fixture.
    # It makes the user available within the same test function if db_session is used again
    # or if an API call via async_client (which uses override_get_db) needs this user.
    # The overall rollback in db_session and override_get_db ensures test isolation.
    await db_session.commit()
    await db_session.refresh(user_model) # Refresh to get any DB-side updates

    # Convert to domain model for direct use in some unit tests if needed
    return DomainUser(
        user_id=user_model.user_id, email=user_model.email,
        password_hash=user_model.password_hash,
        first_name=user_model.first_name,
        last_name=user_model.last_name,
        role=UserRole(user_model.role), # Convert back to Enum
        created_at=user_model.created_at,
        updated_at=user_model.updated_at,
        preferred_language=user_model.preferred_language
    )

# --- Fixture for AuthenticationService with Test DB ---
@pytest.fixture(scope="function")
def auth_service_for_test_tokens(db_session: AsyncSession) -> AuthenticationService:
    """
    Provides an AuthenticationService instance configured with the test database session.
    Useful for generating tokens for test users.
    """
    # Local import to avoid circular dependency if auth_service imports things that lead back here
    from src.readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
    user_repo = UserRepositoryImpl(db_session)
    return AuthenticationService(user_repo)

# --- Helper Function for Auth Headers ---
def get_auth_headers_for_user(user: DomainUser, auth_service: AuthenticationService) -> Dict[str, str]:
    """
    Generates authentication headers for a given domain user using the provided auth_service.
    """
    token = auth_service.create_access_token(user)
    return {"Authorization": f"Bearer {token}"}
