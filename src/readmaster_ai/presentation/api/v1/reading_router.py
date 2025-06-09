"""
API Router for student-facing operations related to Reading materials.
All endpoints here require user authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

# Infrastructure (Database session)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities for type hinting, Enums for query params)
from readmaster_ai.domain.entities.user import User as DomainUser
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel

# Repositories (Abstract for DI)
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository

# Infrastructure (Concrete Repositories for DI)
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.quiz_question_repository_impl import QuizQuestionRepositoryImpl

# Presentation (Dependencies, Schemas - DTOs are imported from Application)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
from readmaster_ai.presentation.schemas.pagination import PaginatedResponse

# Application (DTOs, Use Cases)
from readmaster_ai.application.dto.reading_dtos import ReadingResponseDTO
# Import the student-specific DTO for quiz questions directly
from readmaster_ai.application.dto.quiz_question_dtos import StudentQuizQuestionResponseDTO
from readmaster_ai.application.use_cases.reading_use_cases import ListReadingsUseCase, GetReadingUseCase
from readmaster_ai.application.use_cases.quiz_question_use_cases import ListQuizQuestionsByReadingUseCase

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException

router = APIRouter(
    prefix="/readings",
    tags=["Readings (Student View)"],
    dependencies=[Depends(get_current_user)] # Protect all routes in this router
)

# --- Repository Dependency Provider Functions ---
def get_reading_repo(session: AsyncSession = Depends(get_db)) -> ReadingRepository:
    """Dependency provider for ReadingRepository."""
    return ReadingRepositoryImpl(session)

def get_quiz_question_repo(session: AsyncSession = Depends(get_db)) -> QuizQuestionRepository:
    """Dependency provider for QuizQuestionRepository."""
    return QuizQuestionRepositoryImpl(session)


@router.get("", response_model=PaginatedResponse[ReadingResponseDTO])
async def list_available_readings(
    current_user: DomainUser = Depends(get_current_user), # To acknowledge authenticated user
    page: int = Query(1, ge=1, description="Page number for pagination."),
    size: int = Query(20, ge=1, le=100, description="Number of items per page."),
    language: Optional[str] = Query(None, description="Filter by language code (e.g., 'en')."),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level."),
    age_category: Optional[str] = Query(None, description="Filter by age category."),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
):
    """
    Lists available reading materials for students, with pagination and filters.
    Quiz questions associated with each reading are also listed, but without correct answers.
    """
    list_readings_use_case = ListReadingsUseCase(reading_repo)
    domain_readings, total_count = await list_readings_use_case.execute(
        page=page, size=size, language=language, difficulty=difficulty, age_category=age_category
    )

    items = []
    list_questions_use_case = ListQuizQuestionsByReadingUseCase(quiz_question_repo)
    for r_domain in domain_readings:
        reading_dto = ReadingResponseDTO.model_validate(r_domain) # Uses the updated ReadingResponseDTO

        questions_domain = await list_questions_use_case.execute(reading_id=r_domain.reading_id)
        # ReadingResponseDTO expects List[StudentQuizQuestionResponseDTO] for its 'questions' field
        reading_dto.questions = [StudentQuizQuestionResponseDTO.model_validate(q) for q in questions_domain]
        items.append(reading_dto)

    return PaginatedResponse[ReadingResponseDTO](
        items=items,
        total=total_count,
        page=page,
        size=size
    )

@router.get("/{reading_id}", response_model=ReadingResponseDTO)
async def get_reading_details(
    reading_id: UUID = Path(..., description="The ID of the reading to retrieve."),
    current_user: DomainUser = Depends(get_current_user), # To acknowledge authenticated user
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
):
    """
    Retrieves details of a specific reading material, including its quiz questions (without correct answers).
    """
    get_reading_use_case = GetReadingUseCase(reading_repo)
    list_questions_use_case = ListQuizQuestionsByReadingUseCase(quiz_question_repo)

    try:
        reading_domain = await get_reading_use_case.execute(reading_id)
        questions_domain = await list_questions_use_case.execute(reading_id=reading_domain.reading_id)

        response_dto = ReadingResponseDTO.model_validate(reading_domain)
        # ReadingResponseDTO expects List[StudentQuizQuestionResponseDTO] for its 'questions' field
        response_dto.questions = [StudentQuizQuestionResponseDTO.model_validate(q) for q in questions_domain]

        return response_dto
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
