# tests/application/use_cases/test_assessment_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY # ANY for comparing objects partially
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import List

from readmaster_ai.application.use_cases.assessment_use_cases import (
    StartAssessmentUseCase, RequestAssessmentAudioUploadURLUseCase,
    ConfirmAudioUploadUseCase, SubmitQuizAnswersUseCase, GetAssessmentResultDetailsUseCase
)
from readmaster_ai.domain.entities.assessment import Assessment as DomainAssessment
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus as AssessmentStatusEnum
from readmaster_ai.domain.entities.assessment_result import AssessmentResult as DomainAssessmentResult
from readmaster_ai.domain.entities.student_quiz_answer import StudentQuizAnswer as DomainStudentQuizAnswer
from readmaster_ai.domain.entities.reading import Reading as DomainReading
from readmaster_ai.domain.entities.quiz_question import QuizQuestion as DomainQuizQuestion
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # Corrected import
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.application.interfaces.file_storage_interface import FileStorageInterface
from readmaster_ai.application.dto.assessment_dtos import (
    StartAssessmentRequestDTO, ConfirmUploadRequestDTO, QuizAnswerDTO, QuizSubmissionRequestDTO,
    RequestUploadURLResponseDTO, ConfirmUploadResponseDTO, QuizSubmissionResponseDTO, AssessmentResultDetailDTO # Added missing DTOs
)
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException


# --- Fixtures ---
@pytest.fixture
def mock_assessment_repo() -> MagicMock:
    mock = MagicMock(spec=AssessmentRepository)
    mock.create = AsyncMock(side_effect=lambda assessment: DomainAssessment(
        assessment_id=assessment.assessment_id,
        student_id=assessment.student_id,
        reading_id=assessment.reading_id,
        status=assessment.status,
        assessment_date=assessment.assessment_date,
        updated_at=assessment.updated_at
    ))
    mock.get_by_id = AsyncMock(return_value=None)
    mock.update = AsyncMock(side_effect=lambda assessment: assessment)
    # mock.list_by_student_ids = AsyncMock(return_value=[]) # If needed by other tests
    return mock

@pytest.fixture
def mock_reading_repo_for_assessment() -> MagicMock:
    mock = MagicMock(spec=ReadingRepository)
    # Default: reading found when get_by_id is called
    mock.get_by_id = AsyncMock(return_value=DomainReading(reading_id=uuid4(), title="Default Test Reading", language="en"))
    return mock

@pytest.fixture
def mock_file_storage_service() -> MagicMock:
    mock = MagicMock(spec=FileStorageInterface)
    mock.get_presigned_upload_url = AsyncMock(return_value=("http://fakeurl.com/upload", {"Content-Type": "audio/wav"}))
    return mock

@pytest.fixture
def mock_assessment_result_repo() -> MagicMock:
    mock = MagicMock(spec=AssessmentResultRepository)
    mock.create_or_update = AsyncMock(side_effect=lambda result: result)
    mock.get_by_assessment_id = AsyncMock(return_value=None)
    # mock.list_by_assessment_ids = AsyncMock(return_value=[]) # If needed
    return mock

@pytest.fixture
def mock_student_answer_repo() -> MagicMock:
    mock = MagicMock(spec=StudentQuizAnswerRepository)
    mock.bulk_create = AsyncMock(side_effect=lambda answers: answers)
    mock.list_by_assessment_id = AsyncMock(return_value=[])
    return mock

@pytest.fixture
def mock_quiz_question_repo_for_assessment() -> MagicMock:
    mock = MagicMock(spec=QuizQuestionRepository)
    mock.list_by_reading_id = AsyncMock(return_value=[]) # Default empty list
    mock.get_by_id = AsyncMock(return_value=None)
    return mock

@pytest.fixture
def sample_student_user() -> DomainUser:
    return DomainUser(user_id=uuid4(), email="student.assessmenttests@example.com", password_hash="student", role=UserRole.STUDENT)

@pytest.fixture
def sample_reading(sample_student_user: DomainUser) -> DomainReading:
    # admin_id not strictly needed for reading entity if not used by assessment UCs directly for reading creation
    return DomainReading(reading_id=uuid4(), title="Sample Reading for Assessment Tests", language="en", added_by_admin_id=uuid4())

@pytest.fixture
def sample_assessment(sample_student_user: DomainUser, sample_reading: DomainReading) -> DomainAssessment:
    return DomainAssessment(
        assessment_id=uuid4(),
        student_id=sample_student_user.user_id,
        reading_id=sample_reading.reading_id,
        status=AssessmentStatusEnum.PENDING_AUDIO, # Use the imported enum
        assessment_date=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

# === StartAssessmentUseCase Tests ===
@pytest.mark.asyncio
async def test_start_assessment_success(mock_assessment_repo: MagicMock, mock_reading_repo_for_assessment: MagicMock, sample_student_user: DomainUser, sample_reading: DomainReading):
    mock_reading_repo_for_assessment.get_by_id.return_value = sample_reading
    use_case = StartAssessmentUseCase(assessment_repo=mock_assessment_repo, reading_repo=mock_reading_repo_for_assessment)
    request_dto = StartAssessmentRequestDTO(reading_id=sample_reading.reading_id)

    created_assessment = await use_case.execute(request_dto, sample_student_user)

    mock_reading_repo_for_assessment.get_by_id.assert_called_once_with(sample_reading.reading_id)
    mock_assessment_repo.create.assert_called_once()
    call_args = mock_assessment_repo.create.call_args[0][0]
    assert isinstance(call_args, DomainAssessment)
    assert call_args.reading_id == sample_reading.reading_id
    assert call_args.student_id == sample_student_user.user_id
    assert call_args.status == AssessmentStatusEnum.PENDING_AUDIO
    assert created_assessment.status == AssessmentStatusEnum.PENDING_AUDIO

@pytest.mark.asyncio
async def test_start_assessment_reading_not_found(mock_assessment_repo: MagicMock, mock_reading_repo_for_assessment: MagicMock, sample_student_user: DomainUser):
    mock_reading_repo_for_assessment.get_by_id.return_value = None
    use_case = StartAssessmentUseCase(assessment_repo=mock_assessment_repo, reading_repo=mock_reading_repo_for_assessment)
    request_dto = StartAssessmentRequestDTO(reading_id=uuid4())

    with pytest.raises(NotFoundException):
        await use_case.execute(request_dto, sample_student_user)
    mock_assessment_repo.create.assert_not_called()


# === RequestAssessmentAudioUploadURLUseCase Tests ===
@pytest.mark.asyncio
async def test_request_upload_url_success(mock_assessment_repo: MagicMock, mock_file_storage_service: MagicMock, sample_assessment: DomainAssessment, sample_student_user: DomainUser):
    sample_assessment.status = AssessmentStatusEnum.PENDING_AUDIO
    sample_assessment.student_id = sample_student_user.user_id # Ensure student owns assessment
    mock_assessment_repo.get_by_id.return_value = sample_assessment

    use_case = RequestAssessmentAudioUploadURLUseCase(assessment_repo=mock_assessment_repo, file_storage_service=mock_file_storage_service)

    response_dto = await use_case.execute(assessment_id=sample_assessment.assessment_id, student=sample_student_user, content_type="audio/mp3")

    mock_assessment_repo.get_by_id.assert_called_once_with(sample_assessment.assessment_id)
    mock_file_storage_service.get_presigned_upload_url.assert_called_once_with(
        f"assessments_audio/{sample_assessment.assessment_id}.wav",
        "audio/mp3"
    )
    assert response_dto.upload_url == "http://fakeurl.com/upload"
    assert response_dto.blob_name == f"assessments_audio/{sample_assessment.assessment_id}.wav"

@pytest.mark.asyncio
async def test_request_upload_url_assessment_not_found(mock_assessment_repo: MagicMock, mock_file_storage_service: MagicMock, sample_student_user: DomainUser):
    mock_assessment_repo.get_by_id.return_value = None
    use_case = RequestAssessmentAudioUploadURLUseCase(assessment_repo=mock_assessment_repo, file_storage_service=mock_file_storage_service)

    with pytest.raises(NotFoundException):
        await use_case.execute(uuid4(), sample_student_user)

@pytest.mark.asyncio
async def test_request_upload_url_wrong_status(mock_assessment_repo: MagicMock, mock_file_storage_service: MagicMock, sample_assessment: DomainAssessment, sample_student_user: DomainUser):
    sample_assessment.status = AssessmentStatusEnum.COMPLETED
    sample_assessment.student_id = sample_student_user.user_id # Ensure student owns assessment
    mock_assessment_repo.get_by_id.return_value = sample_assessment
    use_case = RequestAssessmentAudioUploadURLUseCase(assessment_repo=mock_assessment_repo, file_storage_service=mock_file_storage_service)

    with pytest.raises(ApplicationException) as exc_info:
        await use_case.execute(sample_assessment.assessment_id, sample_student_user)
    assert f"Status is '{AssessmentStatusEnum.COMPLETED.value}', expected PENDING_AUDIO" in exc_info.value.message
    assert exc_info.value.status_code == 400


# === ConfirmAudioUploadUseCase Tests ===
@pytest.mark.asyncio
@patch('src.readmaster_ai.application.use_cases.assessment_use_cases.process_assessment_audio_task.delay')
async def test_confirm_upload_success(mock_celery_delay: MagicMock, mock_assessment_repo: MagicMock, sample_assessment: DomainAssessment, sample_student_user: DomainUser):
    sample_assessment.status = AssessmentStatusEnum.PENDING_AUDIO
    sample_assessment.student_id = sample_student_user.user_id # Ensure student owns assessment
    mock_assessment_repo.get_by_id.return_value = sample_assessment

    use_case = ConfirmAudioUploadUseCase(assessment_repo=mock_assessment_repo)
    blob_name = f"assessments_audio/{sample_assessment.assessment_id}.wav"
    request_dto = ConfirmUploadRequestDTO(blob_name=blob_name)

    response_dto = await use_case.execute(sample_assessment.assessment_id, sample_student_user, request_dto)

    mock_assessment_repo.get_by_id.assert_called_once_with(sample_assessment.assessment_id)
    mock_assessment_repo.update.assert_called_once()
    updated_assessment_arg = mock_assessment_repo.update.call_args[0][0]
    assert updated_assessment_arg.status == AssessmentStatusEnum.PROCESSING
    assert updated_assessment_arg.audio_file_url == blob_name

    mock_celery_delay.assert_called_once_with(str(sample_assessment.assessment_id))

    assert response_dto.status == AssessmentStatusEnum.PROCESSING
    assert "Processing has been initiated" in response_dto.message # Check against new message


# Note: Tests for SubmitQuizAnswersUseCase and GetAssessmentResultDetailsUseCase are more complex
# and would involve more setup for related entities (QuizQuestions, StudentQuizAnswers, AssessmentResult).
# They are good candidates for separate, focused test efforts.

# Example structure for SubmitQuizAnswersUseCase test (very basic)
@pytest.mark.asyncio
async def test_submit_quiz_answers_success(
    mock_assessment_repo: MagicMock,
    mock_quiz_question_repo_for_assessment: MagicMock,
    mock_student_answer_repo: MagicMock,
    mock_assessment_result_repo: MagicMock,
    sample_assessment: DomainAssessment,
    sample_student_user: DomainUser
):
    # Arrange
    sample_assessment.status = AssessmentStatusEnum.COMPLETED # AI Processing must be done
    sample_assessment.student_id = sample_student_user.user_id
    mock_assessment_repo.get_by_id.return_value = sample_assessment

    # Mock a quiz question related to the assessment's reading
    q1_id = uuid4()
    mock_quiz_question = DomainQuizQuestion(question_id=q1_id, reading_id=sample_assessment.reading_id,
                                            question_text="Q1?", options={"A":"OptA"}, correct_option_id="A")
    mock_quiz_question_repo_for_assessment.list_by_reading_id.return_value = [mock_quiz_question]

    # Mock existing assessment result (or None if it should be created)
    mock_assessment_result_repo.get_by_assessment_id.return_value = None

    use_case = SubmitQuizAnswersUseCase(
        mock_assessment_repo, mock_quiz_question_repo_for_assessment,
        mock_student_answer_repo, mock_assessment_result_repo
    )
    submission_dto = QuizSubmissionRequestDTO(answers=[QuizAnswerDTO(question_id=q1_id, selected_option_id="A")])

    # Act
    response = await use_case.execute(sample_assessment.assessment_id, sample_student_user, submission_dto)

    # Assert
    mock_student_answer_repo.bulk_create.assert_called_once()
    mock_assessment_result_repo.create_or_update.assert_called_once()
    assert response.correct_answers == 1
    assert response.total_questions == 1
    assert response.comprehension_score == 100.0

    # Check that the assessment result passed to create_or_update has the correct score
    saved_result_arg = mock_assessment_result_repo.create_or_update.call_args[0][0]
    assert isinstance(saved_result_arg, DomainAssessmentResult)
    assert saved_result_arg.comprehension_score == 100.0


# === SubmitQuizAnswersUseCase Tests (Continued) ===
@pytest.mark.asyncio
async def test_submit_quiz_answers_assessment_not_found(
    mock_assessment_repo: MagicMock,
    mock_quiz_question_repo_for_assessment: MagicMock,
    mock_student_answer_repo: MagicMock,
    mock_assessment_result_repo: MagicMock,
    sample_student_user: DomainUser
):
    mock_assessment_repo.get_by_id.return_value = None # Assessment not found
    use_case = SubmitQuizAnswersUseCase(
        mock_assessment_repo, mock_quiz_question_repo_for_assessment,
        mock_student_answer_repo, mock_assessment_result_repo
    )
    submission_dto = QuizSubmissionRequestDTO(answers=[]) # Empty answers, but check should be for assessment

    with pytest.raises(NotFoundException):
        await use_case.execute(uuid4(), sample_student_user, submission_dto)

@pytest.mark.asyncio
async def test_submit_quiz_answers_wrong_assessment_status(
    mock_assessment_repo: MagicMock,
    sample_assessment: DomainAssessment, # Has PENDING_AUDIO status by default from its fixture
    mock_quiz_question_repo_for_assessment: MagicMock,
    mock_student_answer_repo: MagicMock,
    mock_assessment_result_repo: MagicMock,
    sample_student_user: DomainUser
):
    # Ensure student owns the assessment for this test path
    sample_assessment.student_id = sample_student_user.user_id
    sample_assessment.status = AssessmentStatusEnum.PENDING_AUDIO # Explicitly set for clarity
    mock_assessment_repo.get_by_id.return_value = sample_assessment

    use_case = SubmitQuizAnswersUseCase(
        mock_assessment_repo, mock_quiz_question_repo_for_assessment,
        mock_student_answer_repo, mock_assessment_result_repo
    )
    submission_dto = QuizSubmissionRequestDTO(answers=[])

    with pytest.raises(ApplicationException) as exc_info:
        await use_case.execute(sample_assessment.assessment_id, sample_student_user, submission_dto)
    assert "Status is 'pending_audio'. Quiz can only be submitted for COMPLETED assessments." in exc_info.value.message # Or similar message from use case
    assert exc_info.value.status_code == 400


# === GetAssessmentResultDetailsUseCase Tests ===
@pytest.fixture
def sample_assessment_result(sample_assessment: DomainAssessment) -> DomainAssessmentResult:
    return DomainAssessmentResult(
        result_id=uuid4(), assessment_id=sample_assessment.assessment_id,
        analysis_data={"fluency_score": 90.5, "transcription": "text..."}, # Example analysis data
        comprehension_score=80.0,
        created_at=datetime.now(timezone.utc) # Ensure datetime objects are timezone-aware
    )

@pytest.fixture
def sample_student_quiz_answers(sample_assessment: DomainAssessment, sample_student_user: DomainUser) -> List[DomainStudentQuizAnswer]:
    # This fixture now needs to align with questions that would be mocked for the reading
    # Let's assume a question_id that we can also mock in mock_quiz_question_repo_for_assessment
    question_id_for_answer = uuid4()
    return [
        DomainStudentQuizAnswer(
            answer_id=uuid4(),
            assessment_id=sample_assessment.assessment_id,
            question_id=question_id_for_answer, # Use a defined ID
            student_id=sample_student_user.user_id,
            selected_option_id="A",
            is_correct=True,
            answered_at=datetime.now(timezone.utc)
        )
    ]

@pytest.mark.asyncio
async def test_get_assessment_result_details_success(
    mock_assessment_repo: MagicMock, mock_assessment_result_repo: MagicMock,
    mock_student_answer_repo: MagicMock, mock_quiz_question_repo_for_assessment: MagicMock,
    mock_reading_repo_for_assessment: MagicMock,
    sample_assessment: DomainAssessment, sample_student_user: DomainUser,
    sample_assessment_result: DomainAssessmentResult,
    sample_student_quiz_answers: List[DomainStudentQuizAnswer],
    sample_reading: DomainReading
):
    sample_assessment.status = AssessmentStatusEnum.COMPLETED # Ensure assessment is completed
    sample_assessment.student_id = sample_student_user.user_id # Ensure student owns assessment
    sample_assessment.reading_id = sample_reading.reading_id # Link assessment to sample_reading

    mock_assessment_repo.get_by_id.return_value = sample_assessment
    mock_assessment_result_repo.get_by_assessment_id.return_value = sample_assessment_result
    mock_student_answer_repo.list_by_assessment_id.return_value = sample_student_quiz_answers

    # Mock reading for title
    mock_reading_repo_for_assessment.get_by_id.return_value = sample_reading

    # Mock quiz questions based on IDs from sample_student_quiz_answers
    mock_quiz_questions_for_reading = []
    if sample_student_quiz_answers:
        for sqa in sample_student_quiz_answers:
            mock_quiz_questions_for_reading.append(
                DomainQuizQuestion(
                    question_id=sqa.question_id,
                    reading_id=sample_reading.reading_id,
                    question_text=f"Question text for {sqa.question_id}",
                    options={"A": "Opt A Correct", "B": "Opt B"},
                    correct_option_id="A" # Ensure this matches sqa.is_correct if possible
                )
            )
    mock_quiz_question_repo_for_assessment.list_by_reading_id.return_value = mock_quiz_questions_for_reading

    use_case = GetAssessmentResultDetailsUseCase(
        mock_assessment_repo, mock_assessment_result_repo, mock_student_answer_repo,
        mock_quiz_question_repo_for_assessment, mock_reading_repo_for_assessment
    )

    result_dto = await use_case.execute(sample_assessment.assessment_id, sample_student_user)

    assert result_dto.assessment_id == sample_assessment.assessment_id
    assert result_dto.reading_title == sample_reading.title
    assert result_dto.analysis_data == sample_assessment_result.analysis_data
    assert result_dto.comprehension_score == sample_assessment_result.comprehension_score
    assert len(result_dto.submitted_answers) == len(sample_student_quiz_answers)
    if sample_student_quiz_answers:
        assert result_dto.submitted_answers[0].question_id == sample_student_quiz_answers[0].question_id
        assert result_dto.submitted_answers[0].is_correct == sample_student_quiz_answers[0].is_correct
        assert result_dto.submitted_answers[0].correct_option_id == "A" # From mocked question

@pytest.mark.asyncio
async def test_get_assessment_result_details_not_completed(
    mock_assessment_repo: MagicMock, sample_assessment: DomainAssessment, sample_student_user: DomainUser,
    mock_assessment_result_repo: MagicMock, mock_student_answer_repo: MagicMock,
    mock_quiz_question_repo_for_assessment: MagicMock, mock_reading_repo_for_assessment: MagicMock
):
    sample_assessment.status = AssessmentStatusEnum.PROCESSING # Not completed or error state
    sample_assessment.student_id = sample_student_user.user_id
    mock_assessment_repo.get_by_id.return_value = sample_assessment

    use_case = GetAssessmentResultDetailsUseCase(
        mock_assessment_repo, mock_assessment_result_repo, mock_student_answer_repo,
        mock_quiz_question_repo_for_assessment, mock_reading_repo_for_assessment
    )

    with pytest.raises(ApplicationException) as exc_info:
        await use_case.execute(sample_assessment.assessment_id, sample_student_user)
    assert "results not ready. status: processing" in exc_info.value.message.lower()
    assert exc_info.value.status_code == 400
