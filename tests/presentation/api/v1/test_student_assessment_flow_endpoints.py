# tests/presentation/api/v1/test_student_assessment_flow_endpoints.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import patch # For mocking Celery task dispatch
from unittest.mock import MagicMock
# Application components
from src.readmaster_ai.domain.entities.user import DomainUser
from src.readmaster_ai.application.services.auth_service import AuthenticationService
from src.readmaster_ai.infrastructure.database.models import (
    ReadingModel, AssessmentModel, AssessmentResultModel,
    StudentQuizAnswerModel, QuizQuestionModel, UserModel
)
from src.readmaster_ai.domain.value_objects.common_enums import AssessmentStatus, DifficultyLevel

# Fixtures and helpers from conftest.py
from tests.conftest import get_auth_headers_for_user


@pytest_asyncio.fixture(scope="function")
async def student_auth_headers(test_user: DomainUser, auth_service_for_test_tokens: AuthenticationService) -> dict:
    """Generates authentication headers for the default test_user (student)."""
    return get_auth_headers_for_user(test_user, auth_service_for_test_tokens)

@pytest_asyncio.fixture(scope="function")
async def test_reading_for_assessment(db_session: AsyncSession) -> ReadingModel:
    """
    Creates a ReadingModel with associated QuizQuestionModels for assessment tests.
    Attaches question IDs to the reading model instance for easy access in tests.
    Refreshes the reading object after commit to ensure its state is loaded.
    """
    # Create an admin user first
    admin_user = UserModel(
        user_id=uuid4(),
        email="admin_assessment_flow@test.com", # Changed email to avoid potential conflicts if unique constraint exists
        password_hash="dummy_hash",
        role="admin",
        first_name="Test",
        last_name="Admin"
    )
    db_session.add(admin_user)
    await db_session.flush() # Ensure admin_user.user_id is available for foreign keys

    reading_obj_id = uuid4()
    reading = ReadingModel(
        reading_id=reading_obj_id,
        title="The Adventures of Tom Sawyer - Chapter 1",
        language="en",
        difficulty_level=DifficultyLevel.INTERMEDIATE.value,
        added_by_admin_id=admin_user.user_id,
        content_text="Tom appeared on the sidewalk with a bucket of whitewash and a long-handled brush."
    )

    # It's good practice to store IDs assigned in Python locally if they are needed later,
    # especially if the ORM objects (q1, q2) might become expired.
    q1_obj_id = uuid4()
    q1 = QuizQuestionModel(
        question_id=q1_obj_id,
        reading_id=reading.reading_id, # Uses reading_obj_id via reading.reading_id
        question_text="What did Tom have?",
        options={"A": "A cat", "B": "A bucket of whitewash", "C": "A dog"},
        correct_option_id="B",
        added_by_admin_id=admin_user.user_id
    )

    q2_obj_id = uuid4()
    q2 = QuizQuestionModel(
        question_id=q2_obj_id,
        reading_id=reading.reading_id, # Uses reading_obj_id via reading.reading_id
        question_text="Where did Tom appear?",
        options={"A": "In the house", "B": "On the sidewalk", "C": "In the garden"},
        correct_option_id="B",
        added_by_admin_id=admin_user.user_id
    )

    db_session.add_all([reading, q1, q2])
    await db_session.flush() # Persist to DB, make objects persistent

    # Refresh reading object before commit - its state is now loaded from DB based on flushed data.
    # This was in the original code and is fine. q1, q2 are persistent but not explicitly refreshed.
    await db_session.refresh(reading)

    # Attach question IDs to the reading model instance.
    # Accessing .question_id on q1, q2 should be safe as these IDs were assigned in Python
    # and the objects q1, q2 are persistent (not expired yet).
    reading.test_question_ids = [q1.question_id, q2.question_id] # Or use q1_obj_id, q2_obj_id

    # Verify the reading exists in the database before final commit
    stmt = select(ReadingModel).where(ReadingModel.reading_id == reading.reading_id)
    result = await db_session.execute(stmt)
    db_reading_check = result.scalar_one_or_none()
    assert db_reading_check is not None, "Reading was not properly created/flushed in the database"

    # Commit the transaction. If expire_on_commit=True (default), 'reading', 'q1', 'q2'
    # will be marked as EXPIRED after this.
    await db_session.commit()

    # CRITICAL CHANGE: Refresh the 'reading' object AFTER the commit.
    # This loads its state from the database again, so it's no longer expired.
    # When the fixture returns and its 'db_session' is closed, 'reading' will be
    # detached, but its attributes will be populated and accessible.
    await db_session.refresh(reading)
    # If tests needed to access attributes of q1 or q2 directly (e.g. q1.question_text),
    # they would also need to be refreshed here:
    # await db_session.refresh(q1)
    # await db_session.refresh(q2)
    # However, reading.test_question_ids already stores the UUID values, so q1/q2 refresh isn't
    # strictly needed for the current usage.

    return reading

@pytest.mark.asyncio
async def test_start_assessment_success(
    async_client: AsyncClient,
    student_auth_headers: dict,
    test_reading_for_assessment: ReadingModel,
    db_session: AsyncSession,
    test_user: DomainUser # To get student_id for DB verification
):
    """Tests successful initiation of an assessment by a student."""
    request_data = {"reading_id": str(test_reading_for_assessment.reading_id)}
    response = await async_client.post("/api/v1/assessments", json=request_data, headers=student_auth_headers)

    assert response.status_code == 201, f"Response: {response.text}"
    response_json = response.json()
    assert "assessment_id" in response_json
    assert response_json["reading_id"] == str(test_reading_for_assessment.reading_id)
    assert response_json["student_id"] == str(test_user.user_id)
    assert response_json["status"] == AssessmentStatus.PENDING_AUDIO.value

    # Verify in DB using a new session
    # async with db_session.begin():
    #     assessment_id = UUID(response_json["assessment_id"])
    #     stmt = select(AssessmentModel).where(AssessmentModel.assessment_id == assessment_id)
    #     result = await db_session.execute(stmt)
    #     db_assessment = result.scalar_one_or_none()
    #     assert db_assessment is not None
    #     assert db_assessment.status == AssessmentStatus.PENDING_AUDIO.value
    #     assert db_assessment.student_id == test_user.user_id

@pytest.mark.asyncio
async def test_start_assessment_reading_not_found(async_client: AsyncClient, student_auth_headers: dict):
    """Tests assessment initiation with a non-existent reading ID."""
    non_existent_reading_id = uuid4()
    request_data = {"reading_id": str(non_existent_reading_id)}
    response = await async_client.post("/api/v1/assessments", json=request_data, headers=student_auth_headers)
    assert response.status_code == 404
    assert "Reading not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_request_upload_url_success(
    async_client: AsyncClient,
    student_auth_headers: dict,
    test_reading_for_assessment: ReadingModel,
    test_user: DomainUser,
    db_session: AsyncSession
):
    """Tests successfully requesting an audio upload URL for an assessment."""
    # 1. Start an assessment first
    assessment = AssessmentModel(
        assessment_id=uuid4(),
        student_id=test_user.user_id,
        reading_id=test_reading_for_assessment.reading_id,
        status=AssessmentStatus.PENDING_AUDIO.value # Must be in this status
    )
    db_session.add(assessment)
    await db_session.commit()

    # 2. Request upload URL for this assessment
    response = await async_client.post(f"/api/v1/assessments/{assessment.assessment_id}/request-upload-url", headers=student_auth_headers)

    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert "upload_url" in response_json
    assert "blob_name" in response_json
    assert f"assessments_audio/{assessment.assessment_id}" in response_json["blob_name"]
    # For LocalFileStorageService mock, URL structure includes /upload/ and query params
    assert "/upload/" in response_json["upload_url"]
    assert "token=" in response_json["upload_url"]


@pytest.mark.asyncio
@patch('src.readmaster_ai.application.use_cases.assessment_use_cases.process_assessment_audio_task.delay')
async def test_confirm_upload_success_and_celery_dispatch(
    mock_celery_delay: MagicMock,
    async_client: AsyncClient,
    student_auth_headers: dict,
    test_reading_for_assessment: ReadingModel,
    test_user: DomainUser,
    db_session: AsyncSession
):
    """Tests confirming audio upload, which should trigger Celery task and update status."""
    assessment = AssessmentModel(
        assessment_id=uuid4(),
        student_id=test_user.user_id,
        reading_id=test_reading_for_assessment.reading_id,
        status=AssessmentStatus.PENDING_AUDIO.value
    )
    db_session.add(assessment)
    await db_session.commit()

    blob_name_from_upload_step = f"assessments_audio/{assessment.assessment_id}.wav" # Example blob name
    confirm_data = {"blob_name": blob_name_from_upload_step}
    response = await async_client.post(f"/api/v1/assessments/{assessment.assessment_id}/confirm-upload", json=confirm_data, headers=student_auth_headers)

    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["assessment_id"] == str(assessment.assessment_id)
    assert response_json["status"] == AssessmentStatus.PROCESSING.value
    assert "Processing has been initiated" in response_json["message"]

    mock_celery_delay.assert_called_once_with(str(assessment.assessment_id))

    await db_session.refresh(assessment)
    assert assessment.status == AssessmentStatus.PROCESSING.value
    assert assessment.audio_file_url == blob_name_from_upload_step


@pytest.mark.asyncio
async def test_submit_quiz_answers_success(
    async_client: AsyncClient,
    student_auth_headers: dict,
    test_reading_for_assessment: ReadingModel,
    test_user: DomainUser,
    db_session: AsyncSession
):
    """Tests successful submission of quiz answers and score calculation."""
    assessment = AssessmentModel(
        assessment_id=uuid4(),
        student_id=test_user.user_id,
        reading_id=test_reading_for_assessment.reading_id,
        status=AssessmentStatus.COMPLETED.value # AI processing must be done
    )
    # Simulate that AI processing created an AssessmentResult record (without comprehension score yet)
    assessment_result = AssessmentResultModel(
        result_id=uuid4(),
        assessment_id=assessment.assessment_id,
        analysis_data={"fluency": "good", "transcription": "some text"}
    )
    db_session.add_all([assessment, assessment_result])
    await db_session.commit()

    # Use question IDs attached to test_reading_for_assessment by its fixture
    q1_id = test_reading_for_assessment.test_question_ids[0] # Correct answer "B" for "What did Tom have?"
    q2_id = test_reading_for_assessment.test_question_ids[1] # Correct answer "B" for "Where did Tom appear?"

    quiz_answers_payload = {
        "answers": [
            {"question_id": str(q1_id), "selected_option_id": "B"}, # Correct
            {"question_id": str(q2_id), "selected_option_id": "C"}  # Incorrect
        ]
    }
    response = await async_client.post(f"/api/v1/assessments/{assessment.assessment_id}/quiz-answers", json=quiz_answers_payload, headers=student_auth_headers)

    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()
    assert response_json["assessment_id"] == str(assessment.assessment_id)
    assert response_json["total_questions"] == 2
    assert response_json["correct_answers"] == 1
    assert response_json["comprehension_score"] == 50.0

    # Verify StudentQuizAnswer entries in DB
    stmt = select(StudentQuizAnswerModel).where(StudentQuizAnswerModel.assessment_id == assessment.assessment_id)
    db_answers = (await db_session.execute(stmt)).scalars().all()
    assert len(db_answers) == 2

    await db_session.refresh(assessment_result)
    assert assessment_result.comprehension_score == 50.0


@pytest.mark.asyncio
async def test_get_assessment_results_success(
    async_client: AsyncClient,
    student_auth_headers: dict,
    test_reading_for_assessment: ReadingModel,
    test_user: DomainUser,
    db_session: AsyncSession
):
    """Tests successful retrieval of detailed assessment results by a student."""
    assessment_id = uuid4()
    assessment = AssessmentModel(
        assessment_id=assessment_id, student_id=test_user.user_id, reading_id=test_reading_for_assessment.reading_id,
        status=AssessmentStatus.COMPLETED.value, audio_file_url="fake/url.wav", ai_raw_speech_to_text="Some transcribed text."
    )
    assessment_result = AssessmentResultModel(
        result_id=uuid4(), assessment_id=assessment_id,
        analysis_data={"fluency_score": 92.5, "pronunciation_details": "clear overall"},
        comprehension_score=75.0 # Example score
    )
    # Use question IDs from the fixture-created reading
    q1_id = test_reading_for_assessment.test_question_ids[0]
    q2_id = test_reading_for_assessment.test_question_ids[1]
    ans1 = StudentQuizAnswerModel(answer_id=uuid4(), assessment_id=assessment_id, question_id=q1_id, student_id=test_user.user_id, selected_option_id="B", is_correct=True)
    ans2 = StudentQuizAnswerModel(answer_id=uuid4(), assessment_id=assessment_id, question_id=q2_id, student_id=test_user.user_id, selected_option_id="A", is_correct=False) # One correct, one incorrect

    db_session.add_all([assessment, assessment_result, ans1, ans2])
    await db_session.commit()

    response = await async_client.get(f"/api/v1/assessments/{assessment_id}/results", headers=student_auth_headers)

    assert response.status_code == 200, f"Response: {response.text}"
    response_json = response.json()

    assert response_json["assessment_id"] == str(assessment_id)
    assert response_json["status"] == AssessmentStatus.COMPLETED.value
    assert response_json["reading_title"] == test_reading_for_assessment.title
    assert response_json["analysis_data"]["fluency_score"] == 92.5
    assert response_json["comprehension_score"] == 75.0 # As set in fixture
    assert len(response_json["submitted_answers"]) == 2

    # Check details of submitted answers
    submitted_q1_ans = next((ans for ans in response_json["submitted_answers"] if ans["question_id"] == str(q1_id)), None)
    assert submitted_q1_ans is not None
    assert submitted_q1_ans["is_correct"] is True
    assert "question_text" in submitted_q1_ans # Ensure question details are populated
    assert "correct_option_id" in submitted_q1_ans # Students see correct answer in results
    assert submitted_q1_ans["correct_option_id"] == "B" # Assuming Q1's correct answer is "B"
    assert "options" in submitted_q1_ans
    assert submitted_q1_ans["options"] == {"A": "A cat", "B": "A bucket of whitewash", "C": "A dog"} # Options for Q1
