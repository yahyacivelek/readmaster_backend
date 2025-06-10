# tests/application/use_cases/test_quiz_question_use_cases.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timezone

from readmaster_ai.application.use_cases.quiz_question_use_cases import (
    AddQuizQuestionToReadingUseCase, GetQuizQuestionUseCase, ListQuizQuestionsByReadingUseCase,
    UpdateQuizQuestionUseCase, DeleteQuizQuestionUseCase
)
from readmaster_ai.domain.entities.quiz_question import QuizQuestion as DomainQuizQuestion
from readmaster_ai.domain.entities.reading import Reading as DomainReading
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # For admin user
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.application.dto.quiz_question_dtos import QuizQuestionCreateDTO, QuizQuestionUpdateDTO
from readmaster_ai.shared.exceptions import NotFoundException

@pytest.fixture
def mock_quiz_repo() -> MagicMock:
    """Fixture for a mocked QuizQuestionRepository."""
    mock = MagicMock(spec=QuizQuestionRepository)
    mock.create = AsyncMock(side_effect=lambda q: q)
    mock.get_by_id = AsyncMock(return_value=None)
    mock.update = AsyncMock(side_effect=lambda q: q)
    mock.delete = AsyncMock(return_value=True)
    mock.list_by_reading_id = AsyncMock(return_value=[])
    return mock

@pytest.fixture
def mock_reading_repo_for_quiz() -> MagicMock: # Renamed to avoid conflict
    """Fixture for a mocked ReadingRepository, specifically for quiz use case tests."""
    mock = MagicMock(spec=ReadingRepository)
    # Default behavior: Reading is found when checked by AddQuizQuestionToReadingUseCase
    mock.get_by_id = AsyncMock(return_value=DomainReading(
        reading_id=uuid4(), title="Test Reading for Quizzes", language="en"
        # Add other mandatory fields for DomainReading if its __init__ requires them
    ))
    return mock

@pytest.fixture
def sample_admin_user_for_quiz() -> DomainUser: # Renamed to avoid fixture name conflict
    """Fixture for a sample admin DomainUser for quiz tests."""
    return DomainUser(
        user_id=uuid4(),
        email="quiz.admin@example.com",
        password_hash="admin_hash",
        role=UserRole.ADMIN
    )

@pytest.fixture
def sample_quiz_question_domain(sample_admin_user_for_quiz: DomainUser, mock_reading_repo_for_quiz_tests: MagicMock) -> DomainQuizQuestion:
    """Fixture for a sample DomainQuizQuestion."""
    # Ensure reading_id matches the one from the mock_reading_repo_for_quiz_tests fixture if needed for consistency
    # or use a fixed known UUID if tests depend on it.
    # For this sample, we just need a valid UUID.
    reading_id_for_question = mock_reading_repo_for_quiz_tests.get_by_id.return_value.reading_id

    return DomainQuizQuestion(
        question_id=uuid4(),
        reading_id=reading_id_for_question,
        question_text="What is the capital of France?",
        options={"A": "Berlin", "B": "Madrid", "C": "Paris", "D": "Rome"},
        correct_option_id="C",
        language="en",
        added_by_admin_id=sample_admin_user_for_quiz.user_id,
        created_at=datetime.now(timezone.utc)
    )

# === AddQuizQuestionToReadingUseCase Tests ===
@pytest.mark.asyncio
async def test_add_quiz_question_success(
    mock_quiz_repo: MagicMock,
    mock_reading_repo_for_quiz: MagicMock, # Use the correctly named fixture
    sample_admin_user_for_quiz: DomainUser
):
    # Arrange
    # mock_reading_repo_for_quiz.get_by_id is already set up to return a DomainReading
    reading_id_for_test = mock_reading_repo_for_quiz.get_by_id.return_value.reading_id

    use_case = AddQuizQuestionToReadingUseCase(
        quiz_repo=mock_quiz_repo,
        reading_repo=mock_reading_repo_for_quiz
    )
    create_dto = QuizQuestionCreateDTO(
        reading_id=reading_id_for_test,
        question_text="A new question about AI?",
        options={"True": "Yes", "False": "No"},
        correct_option_id="True",
        language="en"
    )

    # Act
    created_question = await use_case.execute(create_dto, sample_admin_user_for_quiz)

    # Assert
    mock_reading_repo_for_quiz.get_by_id.assert_called_once_with(reading_id_for_test)
    mock_quiz_repo.create.assert_called_once()

    call_args = mock_quiz_repo.create.call_args[0][0] # Get the DomainQuizQuestion object passed to create
    assert isinstance(call_args, DomainQuizQuestion)
    assert call_args.question_text == "A new question about AI?"
    assert call_args.reading_id == reading_id_for_test
    assert call_args.added_by_admin_id == sample_admin_user_for_quiz.user_id

    assert created_question.question_text == "A new question about AI?" # Check returned object

@pytest.mark.asyncio
async def test_add_quiz_question_reading_not_found(
    mock_quiz_repo: MagicMock,
    mock_reading_repo_for_quiz: MagicMock, # Use the correctly named fixture
    sample_admin_user_for_quiz: DomainUser
):
    # Arrange
    mock_reading_repo_for_quiz.get_by_id.return_value = None # Simulate reading not found
    use_case = AddQuizQuestionToReadingUseCase(
        quiz_repo=mock_quiz_repo,
        reading_repo=mock_reading_repo_for_quiz
    )

    non_existent_reading_id = uuid4()
    create_dto = QuizQuestionCreateDTO(
        reading_id=non_existent_reading_id,
        question_text="Question for non-existent reading",
        options={"A":"B"}, correct_option_id="A"
    )

    # Act & Assert
    with pytest.raises(NotFoundException) as exc_info:
        await use_case.execute(create_dto, sample_admin_user_for_quiz)

    assert str(non_existent_reading_id) in exc_info.value.message
    assert "Reading" in exc_info.value.message # Check if resource name is mentioned
    mock_quiz_repo.create.assert_not_called()


# === GetQuizQuestionUseCase Tests ===
@pytest.mark.asyncio
async def test_get_quiz_question_success(mock_quiz_repo: MagicMock, sample_quiz_question_domain: DomainQuizQuestion):
    # Arrange
    mock_quiz_repo.get_by_id.return_value = sample_quiz_question_domain
    use_case = GetQuizQuestionUseCase(quiz_repo=mock_quiz_repo)

    # Act
    question = await use_case.execute(sample_quiz_question_domain.question_id)

    # Assert
    mock_quiz_repo.get_by_id.assert_called_once_with(sample_quiz_question_domain.question_id)
    assert question == sample_quiz_question_domain

@pytest.mark.asyncio
async def test_get_quiz_question_not_found(mock_quiz_repo: MagicMock):
    # Arrange
    mock_quiz_repo.get_by_id.return_value = None # Simulate not found
    use_case = GetQuizQuestionUseCase(quiz_repo=mock_quiz_repo)

    non_existent_id = uuid4()
    # Act & Assert
    with pytest.raises(NotFoundException):
        await use_case.execute(non_existent_id)

# Placeholder for further tests for List, Update, Delete use cases
# These would follow a similar pattern:
# - test_list_quiz_questions_by_reading_success_empty
# - test_list_quiz_questions_by_reading_success_with_data
# - test_update_quiz_question_success
# - test_update_quiz_question_not_found
# - test_delete_quiz_question_success
# - test_delete_quiz_question_not_found
