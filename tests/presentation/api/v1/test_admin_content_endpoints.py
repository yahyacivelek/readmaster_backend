# tests/presentation/api/v1/test_admin_content_endpoints.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select # For direct DB checks

# Application components
from src.readmaster_ai.domain.entities.user import User as DomainUser
from src.readmaster_ai.domain.value_objects.common_enums import UserRole, DifficultyLevel # Enums
from src.readmaster_ai.application.services.auth_service import AuthenticationService
from src.readmaster_ai.infrastructure.database.models import ReadingModel, QuizQuestionModel
from src.readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # For creating admin
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

@pytest.fixture
def admin_auth_headers(admin_user: DomainUser, auth_service_for_test_tokens: AuthenticationService) -> dict:
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
    reading_model = ReadingModel(reading_id=uuid4(), title="Fetchable Admin Reading", added_by_admin_id=admin_user.user_id, language="en")
    db_session.add(reading_model)
    await db_session.commit()

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
    reading_model = ReadingModel(reading_id=uuid4(), title="Original Title for API Update", added_by_admin_id=admin_user.user_id, language="en")
    db_session.add(reading_model)
    await db_session.commit()

    update_data = {"title": "Updated Title by Admin API", "genre": "Science Fiction"}
    response = await async_client.put(f"/api/v1/admin/readings/{reading_model.reading_id}", json=update_data, headers=admin_auth_headers)
    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["title"] == "Updated Title by Admin API"
    assert response_json["genre"] == "Science Fiction"

    updated_db_reading = await db_session.get(ReadingModel, reading_model.reading_id)
    assert updated_db_reading.title == "Updated Title by Admin API"

@pytest.mark.asyncio
async def test_admin_delete_reading_success(async_client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, admin_user: DomainUser):
    reading_model = ReadingModel(reading_id=uuid4(), title="Reading To Be Deleted by Admin", added_by_admin_id=admin_user.user_id, language="en")
    db_session.add(reading_model)
    await db_session.commit()

    response = await async_client.delete(f"/api/v1/admin/readings/{reading_model.reading_id}", headers=admin_auth_headers)
    assert response.status_code == 204

    deleted_db_reading = await db_session.get(ReadingModel, reading_model.reading_id)
    assert deleted_db_reading is None


# === Quiz Question Management Tests (Admin) ===
@pytest_asyncio.fixture
async def sample_reading_for_admin_quizzes(db_session: AsyncSession, admin_user: DomainUser) -> ReadingModel:
    reading = ReadingModel(reading_id=uuid4(), title="Reading for Admin Quiz Tests", added_by_admin_id=admin_user.user_id, language="en")
    db_session.add(reading)
    await db_session.commit()
    return reading

@pytest.mark.asyncio
async def test_admin_add_quiz_question_success(async_client: AsyncClient, admin_auth_headers: dict, sample_reading_for_admin_quizzes: ReadingModel, db_session: AsyncSession, admin_user: DomainUser):
    question_data = {
        "reading_id": str(sample_reading_for_admin_quizzes.reading_id), # DTO expects this
        "question_text": "What is the main theme of this reading?",
        "options": {"A": "Love", "B": "War", "C": "Adventure"},
        "correct_option_id": "C",
        "language": "en"
    }
    # Endpoint: POST /admin/questions (not nested for creation as per router structure)
    response = await async_client.post("/api/v1/admin/questions", json=question_data, headers=admin_auth_headers)

    assert response.status_code == 201, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["question_text"] == question_data["question_text"]
    assert response_json["reading_id"] == str(sample_reading_for_admin_quizzes.reading_id)
    assert "question_id" in response_json
    question_id = response_json["question_id"]

    db_question = await db_session.get(QuizQuestionModel, UUID(question_id))
    assert db_question is not None
    assert db_question.question_text == question_data["question_text"]
    assert db_question.added_by_admin_id == admin_user.user_id # Check admin ID

@pytest.mark.asyncio
async def test_admin_list_quiz_questions_for_reading(async_client: AsyncClient, admin_auth_headers: dict, sample_reading_for_admin_quizzes: ReadingModel, db_session: AsyncSession, admin_user: DomainUser):
    q_model = QuizQuestionModel(question_id=uuid4(), reading_id=sample_reading_for_admin_quizzes.reading_id,
                                question_text="Q1 for Admin List", correct_option_id="A", options={},
                                added_by_admin_id=admin_user.user_id) # Ensure admin_id for question
    db_session.add(q_model)
    await db_session.commit()

    response = await async_client.get(f"/api/v1/admin/readings/{sample_reading_for_admin_quizzes.reading_id}/questions", headers=admin_auth_headers)
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
