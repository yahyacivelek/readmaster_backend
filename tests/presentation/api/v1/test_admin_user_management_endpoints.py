# tests/presentation/api/v1/test_admin_user_management_endpoints.py
import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4, UUID

from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole

# Fixtures for authenticated clients will be needed (admin, regular user)
# These might be defined in a conftest.py or need to be created here.
# Assuming a fixture `admin_client` provides an AsyncClient authenticated as an admin,
# and `student_client` for a regular student user.

@pytest.mark.asyncio
async def test_admin_delete_user_success(admin_client: AsyncClient, mock_user_repo_fixture_test_api: None, test_db_session, regular_user_domain_fixture_test_api: DomainUser):
    """Test successful deletion of a user by an admin."""
    user_to_delete = regular_user_domain_fixture_test_api # This user is already in the DB via fixture

    response = await admin_client.delete(f"/api/v1/admin/users/{user_to_delete.user_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify user is actually deleted from DB (or mock_user_repo was called appropriately)
    # For a real DB test, you'd query the DB. For mock, check mock_user_repo.delete_by_id.
    # This depends on how mock_user_repo_fixture_test_api is implemented.
    # If it's a mock:
    # mock_user_repo_fixture_test_api.delete_by_id.assert_called_once_with(user_to_delete.user_id)
    # If it's a real DB, we'd need to fetch from test_db_session:
    from readmaster_ai.infrastructure.database.models import UserModel
    deleted_user_db = await test_db_session.get(UserModel, user_to_delete.user_id)
    assert deleted_user_db is None


@pytest.mark.asyncio
async def test_admin_delete_non_existent_user(admin_client: AsyncClient, mock_user_repo_fixture_test_api: None):
    """Test deleting a user that does not exist."""
    non_existent_user_id = uuid4()
    response = await admin_client.delete(f"/api/v1/admin/users/{non_existent_user_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"User with ID {non_existent_user_id} not found."


@pytest.mark.asyncio
async def test_admin_delete_self_forbidden(admin_client: AsyncClient, admin_user_fixture_test_api: DomainUser, mock_user_repo_fixture_test_api: None):
    """Test an admin trying to delete their own account."""
    admin_user_id = admin_user_fixture_test_api.user_id
    response = await admin_client.delete(f"/api/v1/admin/users/{admin_user_id}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST # As per AdminDeleteUserUseCase
    assert response.json()["detail"] == "Admins cannot delete their own accounts."


@pytest.mark.asyncio
async def test_delete_user_by_non_admin(student_client: AsyncClient, regular_user_domain_fixture_test_api: DomainUser, mock_user_repo_fixture_test_api: None):
    """Test non-admin trying to delete a user."""
    user_to_delete_id = regular_user_domain_fixture_test_api.user_id
    response = await student_client.delete(f"/api/v1/admin/users/{user_to_delete_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    # The exact message depends on the require_role dependency
    # Example: "User role 'student' is not authorized for this operation. Requires 'admin'."
    assert "not authorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_delete_user_invalid_uuid(admin_client: AsyncClient, mock_user_repo_fixture_test_api: None):
    """Test deleting a user with an invalid UUID format."""
    invalid_user_id = "not-a-uuid"
    response = await admin_client.delete(f"/api/v1/admin/users/{invalid_user_id}")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # FastAPI's default validation error for path parameters
    # Details might vary slightly based on FastAPI version
    assert any(
        err["type"] == "uuid_parsing" and err["loc"] == ["path", "user_id"]
        for err in response.json()["detail"]
    )

# Note:
# The fixtures `admin_client`, `student_client`, `mock_user_repo_fixture_test_api`,
# `admin_user_fixture_test_api`, and `regular_user_domain_fixture_test_api` are assumed to be defined
# in a conftest.py or similar shared testing setup file.
# `mock_user_repo_fixture_test_api` might need to be adjusted if it's a real DB test,
# or its mock methods configured as needed (e.g., get_by_id, delete_by_id).
# `test_db_session` is assumed to be a fixture providing an AsyncSession for DB assertions.
#
# For `test_admin_delete_user_success` with a real DB, the `regular_user_domain_fixture_test_api`
# should ensure the user exists in the DB before the test runs, and the assertion checks
# they are gone after.
#
# For mock-based tests of the API layer, you'd typically mock the use case dependency
# rather than the repository, to isolate the router logic. However, if testing the
# full flow up to the repository (as implied by `mock_user_repo_fixture_test_api`),
# then mocking repo methods is appropriate. The current tests seem to mix this a bit.
# For true router unit tests, you'd mock `AdminDeleteUserUseCase`.
# For integration tests (like these seem to be aiming for), using a real DB
# and test clients is common.
#
# I've written them assuming an integration test style where `admin_client` makes real HTTP calls
# to an app instance running against a test database, and `mock_user_repo_fixture_test_api`
# is more of a placeholder name for whatever DB/repo setup is used in API tests.
# The check `deleted_user_db is None` assumes a real DB session.
# If `mock_user_repo_fixture_test_api` is indeed a mock repo passed to the use case,
# then the assertion `mock_user_repo_fixture_test_api.delete_by_id.assert_called_once_with(...)`
# would be more appropriate for some tests.
#
# I will need to define these fixtures or adapt to existing ones.
# For now, I'll assume a `conftest.py` provides:
# - `admin_client`: Authenticated httpx.AsyncClient as admin.
# - `student_client`: Authenticated httpx.AsyncClient as student.
# - `test_db_session`: SQLAlchemy AsyncSession for the test database.
# - `admin_user_fixture_test_api`: A DomainUser (admin) created in the test DB.
# - `regular_user_domain_fixture_test_api`: A DomainUser (student) created in the test DB.
# - `mock_user_repo_fixture_test_api`: This is problematic. For API tests, we usually don't mock the repo
#   directly if we are doing integration tests. We'd mock the use case for unit tests of the router,
#   or use a real repo for integration tests. I'll remove this fixture from the API tests for now,
#   as the use case itself is already tested with a mocked repo. API tests should verify the HTTP layer
#   and overall integration.

# Re-adjusting the test to not rely on mock_user_repo_fixture_test_api for API tests:

# tests/presentation/api/v1/test_admin_user_management_endpoints.py
import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4, UUID

from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.infrastructure.database.models import UserModel # For DB checks

# Assume conftest.py provides:
# - async_client: Unauthenticated client
# - admin_client: Authenticated client as admin
# - student_client: Authenticated client as student
# - test_db_session: SQLAlchemy AsyncSession for the test database
# - create_user_in_db: A fixture or utility to create users directly in DB for setup.
# - admin_user_fixture: An admin DomainUser created in DB.
# - student_user_fixture: A student DomainUser created in DB.


@pytest.mark.asyncio
async def test_admin_delete_user_success(
    admin_client: AsyncClient,
    test_db_session,
    student_user_fixture: DomainUser # A student user created by a fixture in the test DB
):
    """Test successful deletion of a user by an admin."""
    user_to_delete_id = student_user_fixture.user_id

    response = await admin_client.delete(f"/api/v1/admin/users/{user_to_delete_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify user is actually deleted from DB
    deleted_user_db = await test_db_session.get(UserModel, user_to_delete_id)
    assert deleted_user_db is None


@pytest.mark.asyncio
async def test_admin_delete_non_existent_user(admin_client: AsyncClient):
    """Test deleting a user that does not exist."""
    non_existent_user_id = uuid4()
    response = await admin_client.delete(f"/api/v1/admin/users/{non_existent_user_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"User with ID {non_existent_user_id} not found."


@pytest.mark.asyncio
async def test_admin_delete_self_forbidden(
    admin_client: AsyncClient,
    admin_user_fixture: DomainUser # The admin user associated with admin_client
):
    """Test an admin trying to delete their own account."""
    admin_user_id = admin_user_fixture.user_id
    response = await admin_client.delete(f"/api/v1/admin/users/{admin_user_id}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Admins cannot delete their own accounts."


@pytest.mark.asyncio
async def test_delete_user_by_non_admin(
    student_client: AsyncClient, # Client authenticated as a student
    student_user_fixture: DomainUser # Some other student user to attempt to delete
):
    """Test non-admin trying to delete a user."""
    user_to_delete_id = student_user_fixture.user_id
    response = await student_client.delete(f"/api/v1/admin/users/{user_to_delete_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "not authorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_delete_user_invalid_uuid(admin_client: AsyncClient):
    """Test deleting a user with an invalid UUID format."""
    invalid_user_id = "not-a-uuid"
    response = await admin_client.delete(f"/api/v1/admin/users/{invalid_user_id}")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert any(
        err["type"] == "uuid_parsing" and err["loc"] == ["path", "user_id"]
        for err in response.json()["detail"]
    )
