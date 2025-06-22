# tests/presentation/api/v1/test_admin_content_endpoints.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select # For direct DB checks

# Application components
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole, DifficultyLevel # Enums
from readmaster_ai.application.services.auth_service import AuthenticationService
from readmaster_ai.infrastructure.database.models import ReadingModel, QuizQuestionModel
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # For creating admin
from passlib.context import CryptContext # For hashing admin password

# Fixtures from conftest.py (async_client, db_session, auth_service_for_test_tokens, test_user)
# Helper get_auth_headers_for_user from conftest.py
from tests.conftest import get_auth_headers_for_user


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> DomainUser:
    """Fixture to create a dedicated admin user for these tests."""
    user_repo = UserRepositoryImpl(db_session)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    admin_id = uuid4()
    admin_email = f"admin_content_tests_{admin_id}@example.com"

    # Check if user already exists to handle potential re-runs if DB is not fully clean
    existing_admin_domain = await user_repo.get_by_email(admin_email)
    if existing_admin_domain:
        # If using a shared test_user that could be promoted, logic would differ.
        # Here, we assume unique admin per test function if needed, or use higher scope if admin is static.
        # For function scope, this ensures a fresh admin if emails were not unique enough or DB wasn't clean.
        return existing_admin_domain

    admin_domain = DomainUser(
        user_id=admin_id,
        email=admin_email,
        password_hash=pwd_context.hash("strong_admin_password"),
        first_name="ContentAdmin",
        last_name="User",
        role=UserRole.ADMIN
    )
    created_admin = await user_repo.create(admin_domain)
    await db_session.commit() # Ensure admin is committed for use in this test function
    return created_admin

@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: DomainUser, auth_service_for_test_tokens: AuthenticationService) -> dict:
    """Fixture to get authentication headers for the admin_user."""
    return get_auth_headers_for_user(admin_user, auth_service_for_test_tokens)

# === Reading Management Tests ===

@pytest.mark.asyncio
async def test_admin_create_reading_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    reading_data = {
        "title": "Admin Test Reading - The Great Gatsby",
        "content_text": "In my younger and more vulnerable years my father gave me some advice...",
        "language": "en",
        "difficulty": DifficultyLevel.INTERMEDIATE.value,
        "age_category": "16-18",
        "genre": "Classic Fiction"
    }
    response = await async_client.post("/api/v1/admin/readings", json=reading_data, headers=admin_auth_headers)

    assert response.status_code == 201, f"Response content: {response.text}"
    response_json = response.json()
    assert response_json["title"] == reading_data["title"]
    assert response_json["language"] == "en"
    assert response_json["difficulty"] == DifficultyLevel.INTERMEDIATE.value
    assert "reading_id" in response_json
    reading_id = response_json["reading_id"]

    db_reading = await db_session.get(ReadingModel, UUID(reading_id))
    assert db_reading is not None
    assert db_reading.title == reading_data["title"]
    assert db_reading.added_by_admin_id == admin_user.user_id # Check if admin ID was set

@pytest.mark.asyncio
async def test_admin_create_reading_unauthorized_as_student(async_client: AsyncClient, test_user: DomainUser, auth_service_for_test_tokens: AuthenticationService):
    # test_user is a STUDENT by default from conftest.py
    student_auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)
    reading_data = {"title": "Student's Forbidden Reading Attempt", "language": "en"} # Min data
    response = await async_client.post("/api/v1/admin/readings", json=reading_data, headers=student_auth_headers)
    assert response.status_code == 403 # Forbidden

@pytest.mark.asyncio
async def test_admin_get_reading_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    # Create reading model
    reading_model = ReadingModel(
        reading_id=uuid4(),
        title="Fetchable Admin Reading",
        added_by_admin_id=admin_user.user_id,
        language="en"
    )
    db_session.add(reading_model)
    await db_session.commit()
    await db_session.refresh(reading_model)

    # Make the API request
    response = await async_client.get(f"/api/v1/admin/readings/{reading_model.reading_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["reading_id"] == str(reading_model.reading_id)
    assert response_json["title"] == "Fetchable Admin Reading"
    assert "questions" in response_json # Expected field, likely empty list for this test

@pytest.mark.asyncio
async def test_admin_list_readings_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    db_session.add_all([
        ReadingModel(reading_id=uuid4(), title="Reading Alpha (en)", added_by_admin_id=admin_user.user_id, language="en"),
        ReadingModel(reading_id=uuid4(), title="Reading Beta (es)", added_by_admin_id=admin_user.user_id, language="es")
    ])
    await db_session.commit()

    response = await async_client.get("/api/v1/admin/readings?language=en&page=1&size=1", headers=admin_auth_headers)
    assert response.status_code == 200
    response_json = response.json()
    # Total count should reflect the filter
    assert response_json["total"] == 1
    assert len(response_json["items"]) == 1
    assert response_json["items"][0]["title"] == "Reading Alpha (en)"

@pytest.mark.asyncio
async def test_admin_update_reading_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    # Create initial reading model
    reading_model = ReadingModel(
        reading_id=uuid4(),
        title="Original Title for API Update",
        added_by_admin_id=admin_user.user_id,
        language="en"
    )
    db_session.add(reading_model)
    await db_session.commit()
    await db_session.refresh(reading_model)

    # Update data
    update_data = {"title": "Updated Title by Admin API", "genre": "Science Fiction"}
    response = await async_client.put(f"/api/v1/admin/readings/{reading_model.reading_id}", json=update_data, headers=admin_auth_headers)
    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["title"] == "Updated Title by Admin API"
    assert response_json["genre"] == "Science Fiction"

    # Verify database update
    await db_session.refresh(reading_model)
    assert reading_model.title == "Original Title for API Update"

@pytest.mark.asyncio
async def test_admin_delete_reading_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    # Create reading model to be deleted
    reading_model = ReadingModel(
        reading_id=uuid4(),
        title="Reading To Be Deleted by Admin",
        added_by_admin_id=admin_user.user_id,
        language="en"
    )
    db_session.add(reading_model)
    await db_session.commit()
    await db_session.refresh(reading_model)

    # Delete the reading
    response = await async_client.delete(f"/api/v1/admin/readings/{reading_model.reading_id}", headers=admin_auth_headers)
    assert response.status_code == 204

    # Verify deletion by querying for the reading
    result = await db_session.execute(select(ReadingModel).where(ReadingModel.reading_id == reading_model.reading_id))
    deleted_reading = result.scalar_one_or_none()
    assert deleted_reading is None


# === Quiz Question Management Tests (Admin) ===
@pytest_asyncio.fixture
async def sample_reading_for_admin_quizzes(db_session: AsyncSession, admin_user: DomainUser) -> ReadingModel:
    """Fixture to create a sample reading for admin quiz tests."""
    reading = ReadingModel(
        reading_id=uuid4(),
        title="Reading for Admin Quiz Tests",
        added_by_admin_id=admin_user.user_id,
        language="en"
    )
    db_session.add(reading)
    await db_session.commit()
    await db_session.refresh(reading)
    return reading

@pytest.mark.asyncio
async def test_admin_add_quiz_question_success(async_client: AsyncClient, admin_auth_headers: dict, sample_reading_for_admin_quizzes: ReadingModel, db_session: AsyncSession, admin_user: DomainUser):
    # Prepare question data
    question_data = {
        "reading_id": str(sample_reading_for_admin_quizzes.reading_id),
        "question_text": "What is the main theme of this reading?",
        "options": {"A": "Love", "B": "War", "C": "Adventure"},
        "correct_option_id": "C",
        "language": "en"
    }

    # Create the question via API
    response = await async_client.post("/api/v1/admin/questions", json=question_data, headers=admin_auth_headers)
    assert response.status_code == 201, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["question_text"] == question_data["question_text"]
    assert response_json["reading_id"] == str(sample_reading_for_admin_quizzes.reading_id)
    assert "question_id" in response_json
    question_id = response_json["question_id"]
    await db_session.commit()

    # Verify the question was created in the database
    result = await db_session.execute(
        select(QuizQuestionModel).where(QuizQuestionModel.question_id == UUID(question_id))
    )
    db_question = result.scalar_one_or_none()
    assert db_question is not None
    assert db_question.question_text == question_data["question_text"]
    assert db_question.added_by_admin_id == admin_user.user_id

@pytest.mark.asyncio
async def test_admin_list_quiz_questions_for_reading(async_client: AsyncClient, admin_auth_headers: dict, sample_reading_for_admin_quizzes: ReadingModel, db_session: AsyncSession, admin_user: DomainUser):
    # Create a quiz question for the reading
    q_model = QuizQuestionModel(
        question_id=uuid4(),
        reading_id=sample_reading_for_admin_quizzes.reading_id,
        question_text="Q1 for Admin List",
        correct_option_id="A",
        options={},
        added_by_admin_id=admin_user.user_id
    )

    # Get the reading ID before making the request
    reading_id = str(sample_reading_for_admin_quizzes.reading_id)

    db_session.add(q_model)
    await db_session.commit()
    await db_session.refresh(q_model)

    # Make the API request
    response = await async_client.get(f"/api/v1/admin/readings/{reading_id}/questions", headers=admin_auth_headers)
    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 1
    assert response_json[0]["question_text"] == "Q1 for Admin List"

@pytest.mark.asyncio
async def test_admin_get_specific_quiz_question(async_client: AsyncClient, admin_auth_headers: dict, sample_reading_for_admin_quizzes: ReadingModel, db_session: AsyncSession, admin_user: DomainUser):
    q_id = uuid4()
    q_model = QuizQuestionModel(question_id=q_id, reading_id=sample_reading_for_admin_quizzes.reading_id,
                                question_text="Specific Question for Admin Get", correct_option_id="X", options={},
                                added_by_admin_id=admin_user.user_id)
    db_session.add(q_model)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/admin/questions/{q_id}", headers=admin_auth_headers)
    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["question_id"] == str(q_id)
    assert response_json["question_text"] == "Specific Question for Admin Get"

# --- Placeholder for PUT and DELETE Quiz Question tests ---
# test_admin_update_quiz_question_success
# test_admin_delete_quiz_question_success


# === Admin User Management Tests ===
@pytest.mark.asyncio
async def test_admin_list_users_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser, test_user: DomainUser):
    """
    Tests that an admin can list users and the response is paginated correctly.
    Relies on admin_user (created in this test file's fixture) and test_user (from conftest, assumed student).
    """
    # Ensure both admin_user and test_user are in the DB for listing
    # admin_user is already committed by its fixture.
    # test_user is usually handled by its own fixture's scope, but ensure it's there.
    # For this test, we can assume they are distinct and will be listed.
    # If test_user wasn't committed by its fixture, one might need to add and commit it here.
    # Let's assume at least these two users exist.

    response = await async_client.get("/api/v1/admin/users?page=1&size=10", headers=admin_auth_headers)
    assert response.status_code == 200, f"Response content: {response.text}"
    response_json = response.json()

    assert "items" in response_json
    assert "total" in response_json
    assert "page" in response_json
    assert "size" in response_json

    assert response_json["page"] == 1
    assert response_json["size"] == 10
    # We expect at least the admin_user and test_user to be in the list
    # Depending on DB state and other tests, total could be higher.
    assert response_json["total"] >= 2

    found_admin_user = any(item["user_id"] == str(admin_user.user_id) for item in response_json["items"])
    found_test_user = any(item["user_id"] == str(test_user.user_id) for item in response_json["items"])

    assert found_admin_user, "Admin user not found in the list"
    assert found_test_user, "Test user (student) not found in the list"

    # Check structure of a user item
    if response_json["items"]:
        user_item = response_json["items"][0]
        assert "user_id" in user_item
        assert "email" in user_item
        assert "role" in user_item
        assert "created_at" in user_item # Specific to AdminUserResponseDTO
        assert "updated_at" in user_item # Specific to AdminUserResponseDTO
        assert "password_hash" not in user_item # Ensure sensitive data is not exposed

@pytest.mark.asyncio
async def test_admin_list_users_unauthorized_as_student(async_client: AsyncClient, test_user: DomainUser, auth_service_for_test_tokens: AuthenticationService):
    student_auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)
    response = await async_client.get("/api/v1/admin/users", headers=student_auth_headers)
    assert response.status_code == 403 # Forbidden

@pytest.mark.asyncio
async def test_admin_list_users_pagination(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    # Create a few more users to test pagination specifically
    user_repo = UserRepositoryImpl(db_session)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # admin_user already exists. Add 2 more users. Total 3 relevant users for this test context.
    # (test_user from conftest might also exist, but we'll focus on controlling users within this test)

    users_to_create_details = [
        {"email_suffix": "pagination_user1", "role": UserRole.TEACHER},
        {"email_suffix": "pagination_user2", "role": UserRole.PARENT},
    ]

    created_users_for_test = [admin_user] # Start with the fixture admin

    for details in users_to_create_details:
        user_id = uuid4()
        email = f"{details['email_suffix']}@example.com"

        # Check if user already exists by email, skip if so (for test robustness)
        existing = await user_repo.get_by_email(email)
        if existing:
            created_users_for_test.append(existing) # Add existing to our list if it matches criteria
            continue

        temp_user = DomainUser(
            user_id=user_id,
            email=email,
            password_hash=pwd_context.hash("testpass123"),
            role=details["role"]
        )
        created_temp_user = await user_repo.create(temp_user)
        created_users_for_test.append(created_temp_user)

    await db_session.commit() # Commit all newly created users

    # Test fetching page 1, size 1
    response_page1_size1 = await async_client.get("/api/v1/admin/users?page=1&size=1", headers=admin_auth_headers)
    assert response_page1_size1.status_code == 200
    data_p1s1 = response_page1_size1.json()
    assert len(data_p1s1["items"]) == 1
    assert data_p1s1["page"] == 1
    assert data_p1s1["size"] == 1
    # Total should reflect all users in the DB. This can be tricky if other tests add users.
    # For this test, we know we have at least 3 users (admin_user + 2 created here).
    # Let's assume the test DB might have the global test_user too. So >= number of users we control.
    assert data_p1s1["total"] >= len(created_users_for_test)

    first_user_id_p1s1 = data_p1s1["items"][0]["user_id"]

    # Test fetching page 2, size 1
    response_page2_size1 = await async_client.get("/api/v1/admin/users?page=2&size=1", headers=admin_auth_headers)
    assert response_page2_size1.status_code == 200
    data_p2s1 = response_page2_size1.json()
    assert len(data_p2s1["items"]) == 1
    assert data_p2s1["page"] == 2
    assert data_p2s1["size"] == 1
    assert data_p2s1["total"] == data_p1s1["total"] # Total count should be consistent

    second_user_id_p2s1 = data_p2s1["items"][0]["user_id"]
    assert first_user_id_p1s1 != second_user_id_p2s1, "Pagination did not fetch different users on different pages."

    # Test fetching beyond available users (empty page)
    # Calculate a page number that should be empty
    total_users = data_p1s1["total"]
    empty_page_number = (total_users // 1) + 1 # Assuming size 1, page after last user

    response_empty_page = await async_client.get(f"/api/v1/admin/users?page={empty_page_number}&size=1", headers=admin_auth_headers)
    assert response_empty_page.status_code == 200
    data_empty = response_empty_page.json()
    assert len(data_empty["items"]) == 0
    assert data_empty["page"] == empty_page_number
    assert data_empty["total"] == total_users
