# tests/presentation/api/v1/test_student_reading_endpoints.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List # For type hinting List[ReadingModel]

# Application components
from src.readmaster_ai.domain.entities.user import DomainUser
# UserRole is not strictly needed here unless creating users with specific roles within these tests.
# from src.readmaster_ai.domain.value_objects.common_enums import UserRole
from src.readmaster_ai.application.services.auth_service import AuthenticationService
from src.readmaster_ai.infrastructure.database.models import ReadingModel, QuizQuestionModel
from src.readmaster_ai.domain.value_objects.common_enums import DifficultyLevel # For enum values in tests

# Fixtures from conftest.py: async_client, db_session, test_user (is a STUDENT by default), auth_service_for_test_tokens
# Helper from conftest.py: get_auth_headers_for_user
from tests.conftest import get_auth_headers_for_user # Explicit import for clarity

@pytest_asyncio.fixture(scope="function")
async def setup_readings_with_questions(db_session: AsyncSession) -> List[ReadingModel]:
    """
    Fixture to populate the test database with sample readings and quiz questions.
    Returns a list of the created ReadingModel instances.
    """
    # A dummy admin_id is used as added_by_admin_id is a required field for ReadingModel.
    # In a real scenario with more complex user interactions, you might use an admin_user fixture.
    dummy_admin_id = uuid4()

    reading1_id = uuid4()
    reading1 = ReadingModel(
        reading_id=reading1_id, title="Student Reading 1 (Easy, EN)", language="en",
        difficulty=DifficultyLevel.BEGINNER.value, age_category="6-8",
        added_by_admin_id=dummy_admin_id, content_text="Content for reading 1."
    )
    q1_r1 = QuizQuestionModel(question_id=uuid4(), reading_id=reading1_id, question_text="Q1 for R1?", options={"A":"Opt1", "B":"Opt2"}, correct_option_id="A", added_by_admin_id=dummy_admin_id)
    q2_r1 = QuizQuestionModel(question_id=uuid4(), reading_id=reading1_id, question_text="Q2 for R1?", options={"C":"Opt3", "D":"Opt4"}, correct_option_id="D", added_by_admin_id=dummy_admin_id)

    reading2_id = uuid4()
    reading2 = ReadingModel(
        reading_id=reading2_id, title="Student Reading 2 (Hard, ES)", language="es",
        difficulty=DifficultyLevel.ADVANCED.value, age_category="9-12",
        added_by_admin_id=dummy_admin_id, content_text="Content for reading 2."
    )
    q1_r2 = QuizQuestionModel(question_id=uuid4(), reading_id=reading2_id, question_text="Q1 for R2 (Spanish)?", options={"X":"OptX", "Y":"OptY"}, correct_option_id="X", added_by_admin_id=dummy_admin_id)

    reading3_id = uuid4() # A reading with no quiz questions
    reading3 = ReadingModel(
        reading_id=reading3_id, title="Student Reading 3 (Easy, EN, No Quiz)", language="en",
        difficulty=DifficultyLevel.BEGINNER.value, age_category="6-8",
        added_by_admin_id=dummy_admin_id, content_text="Content for reading 3."
    )

    db_session.add_all([reading1, q1_r1, q2_r1, reading2, q1_r2, reading3])
    await db_session.commit()
    # Return the models as they might be useful for assertions if IDs are needed
    return [reading1, reading2, reading3]


@pytest.mark.asyncio
async def test_list_readings_success_authenticated(
    async_client: AsyncClient,
    test_user: DomainUser, # test_user is a STUDENT from conftest.py
    auth_service_for_test_tokens: AuthenticationService,
    setup_readings_with_questions: List[ReadingModel] # This fixture ensures data exists
):
    """Tests successful listing of readings for an authenticated student."""
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)
    response = await async_client.get("/api/v1/readings", headers=auth_headers)

    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert "items" in response_json
    assert "total" in response_json
    assert response_json["total"] == 3 # Based on setup_readings_with_questions fixture
    assert len(response_json["items"]) == 3 # Assuming default page size covers all

    # Verify that correct_option_id is NOT in the questions for student view
    for item in response_json["items"]:
        assert "questions" in item
        for question_dto in item["questions"]:
            assert "correct_option_id" not in question_dto # Key check for student DTO
            assert "question_text" in question_dto
            assert "options" in question_dto

@pytest.mark.asyncio
async def test_list_readings_unauthenticated(async_client: AsyncClient):
    """Tests that unauthenticated access to list readings is denied."""
    response = await async_client.get("/api/v1/readings") # No Authorization header
    assert response.status_code == 401 # Expect 401 Unauthorized as route is protected

@pytest.mark.asyncio
async def test_list_readings_with_filters(
    async_client: AsyncClient,
    test_user: DomainUser,
    auth_service_for_test_tokens: AuthenticationService,
    setup_readings_with_questions: List[ReadingModel] # Ensures data is present
):
    """Tests filtering capabilities for listing readings."""
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)

    # Filter by language 'en'
    response_en = await async_client.get("/api/v1/readings?language=en", headers=auth_headers)
    assert response_en.status_code == 200
    json_en = response_en.json()
    assert json_en["total"] == 2 # Reading 1 and Reading 3 are 'en'
    assert all(item["language"] == "en" for item in json_en["items"])

    # Filter by difficulty 'BEGINNER'
    response_easy = await async_client.get(f"/api/v1/readings?difficulty={DifficultyLevel.BEGINNER.value}", headers=auth_headers)
    assert response_easy.status_code == 200
    json_easy = response_easy.json()
    assert json_easy["total"] == 2 # Reading 1 and Reading 3 are 'BEGINNER'
    assert all(item["difficulty"] == DifficultyLevel.BEGINNER.value for item in json_easy["items"])

    # Filter by language 'en' AND difficulty 'ADVANCED' (should be 0 from setup)
    response_en_hard = await async_client.get(f"/api/v1/readings?language=en&difficulty={DifficultyLevel.ADVANCED.value}", headers=auth_headers)
    assert response_en_hard.status_code == 200
    json_en_hard = response_en_hard.json()
    assert json_en_hard["total"] == 0
    assert len(json_en_hard["items"]) == 0

    # Filter by age_category "6-8"
    response_age = await async_client.get("/api/v1/readings?age_category=6-8", headers=auth_headers)
    assert response_age.status_code == 200
    json_age = response_age.json()
    assert json_age["total"] == 2 # Reading 1 and Reading 3
    assert all(item["age_category"] == "6-8" for item in json_age["items"])


@pytest.mark.asyncio
async def test_get_specific_reading_success(
    async_client: AsyncClient,
    test_user: DomainUser,
    auth_service_for_test_tokens: AuthenticationService,
    setup_readings_with_questions: List[ReadingModel] # Provides created readings
):
    """Tests successful retrieval of a specific reading by its ID."""
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)
    # Get the first reading created by the fixture
    reading_to_fetch = setup_readings_with_questions[0]

    response = await async_client.get(f"/api/v1/readings/{reading_to_fetch.reading_id}", headers=auth_headers)

    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["reading_id"] == str(reading_to_fetch.reading_id)
    assert response_json["title"] == reading_to_fetch.title
    assert len(response_json["questions"]) == 2 # Reading 1 (index 0) has 2 questions from fixture
    for q_dto in response_json["questions"]:
        assert "correct_option_id" not in q_dto # Verify student DTO is used

@pytest.mark.asyncio
async def test_get_specific_reading_not_found(
    async_client: AsyncClient,
    test_user: DomainUser,
    auth_service_for_test_tokens: AuthenticationService
):
    """Tests retrieval of a non-existent reading ID."""
    auth_headers = get_auth_headers_for_user(test_user, auth_service_for_test_tokens)
    non_existent_id = uuid4() # Random, non-existent UUID
    response = await async_client.get(f"/api/v1/readings/{non_existent_id}", headers=auth_headers)
    assert response.status_code == 404
    assert "Reading not found" in response.json()["detail"] # Check for specific message if possible
