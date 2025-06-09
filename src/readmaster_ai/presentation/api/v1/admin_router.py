"""
API Router for Admin-specific operations, including management of
Reading materials and Quiz Questions.
All endpoints in this router require ADMIN role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

# Infrastructure (Database session)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities, Enums, Repositories - Abstract)
from readmaster_ai.domain.entities.user import User as DomainUser # For type hinting current_admin
from readmaster_ai.domain.value_objects.common_enums import UserRole, DifficultyLevel # UserRole for auth, DifficultyLevel for query param
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository

# Infrastructure (Repositories - Concrete for DI)
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.quiz_question_repository_impl import QuizQuestionRepositoryImpl

# Presentation (Dependencies, Schemas - DTOs are imported from Application)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user, require_role
from readmaster_ai.presentation.schemas.pagination import PaginatedResponse

# Application (DTOs, Use Cases)
from readmaster_ai.application.dto.reading_dtos import ReadingCreateDTO, ReadingUpdateDTO, ReadingResponseDTO
from readmaster_ai.application.dto.quiz_question_dtos import QuizQuestionCreateDTO, QuizQuestionUpdateDTO, QuizQuestionResponseDTO
from readmaster_ai.application.use_cases.reading_use_cases import (
    CreateReadingUseCase, GetReadingUseCase, ListReadingsUseCase, UpdateReadingUseCase, DeleteReadingUseCase
)
from readmaster_ai.application.use_cases.quiz_question_use_cases import (
    AddQuizQuestionToReadingUseCase, GetQuizQuestionUseCase, ListQuizQuestionsByReadingUseCase,
    UpdateQuizQuestionUseCase, DeleteQuizQuestionUseCase
)

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException


router = APIRouter(
    prefix="/admin",
    tags=["Admin Management"], # Combined tag for all admin operations
    dependencies=[Depends(require_role(UserRole.ADMIN))] # Protect all routes in this router
)

# --- Repository Dependency Provider Functions ---
def get_reading_repo(session: AsyncSession = Depends(get_db)) -> ReadingRepository:
    """Dependency provider for ReadingRepository."""
    return ReadingRepositoryImpl(session)

def get_quiz_question_repo(session: AsyncSession = Depends(get_db)) -> QuizQuestionRepository:
    """Dependency provider for QuizQuestionRepository."""
    return QuizQuestionRepositoryImpl(session)

# --- Readings Endpoints ---
@router.post("/readings", response_model=ReadingResponseDTO, status_code=status.HTTP_201_CREATED)
async def admin_create_reading(
    reading_data: ReadingCreateDTO,
    current_admin: DomainUser = Depends(get_current_user), # Ensures admin context, though router dep already checks role
    reading_repo: ReadingRepository = Depends(get_reading_repo)
):
    """Allows Admins to create a new reading material."""
    use_case = CreateReadingUseCase(reading_repo)
    try:
        created_reading = await use_case.execute(reading_data, current_admin)
        # ReadingResponseDTO has questions=[] by default, which is fine for a new reading.
        return ReadingResponseDTO.model_validate(created_reading)
    except ApplicationException as e: # Catch broad application errors, e.g., validation if added
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/readings/{reading_id}", response_model=ReadingResponseDTO)
async def admin_get_reading_with_questions(
    reading_id: UUID = Path(..., description="The ID of the reading to retrieve"),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
):
    """Allows Admins to retrieve a specific reading material, including its quiz questions."""
    get_reading_use_case = GetReadingUseCase(reading_repo)
    list_questions_use_case = ListQuizQuestionsByReadingUseCase(quiz_question_repo)
    try:
        reading = await get_reading_use_case.execute(reading_id)
        questions = await list_questions_use_case.execute(reading_id)

        response_dto = ReadingResponseDTO.model_validate(reading)
        response_dto.questions = [QuizQuestionResponseDTO.model_validate(q) for q in questions]
        return response_dto
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/readings", response_model=PaginatedResponse[ReadingResponseDTO])
async def admin_list_readings(
    page: int = Query(1, ge=1, description="Page number for pagination."),
    size: int = Query(20, ge=1, le=100, description="Number of items per page."),
    language: Optional[str] = Query(None, description="Filter by language code (e.g., 'en')."),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level."), # FastAPI handles Enum query params
    age_category: Optional[str] = Query(None, description="Filter by age category."),
    reading_repo: ReadingRepository = Depends(get_reading_repo)
):
    """Allows Admins to list reading materials with filters and pagination."""
    use_case = ListReadingsUseCase(reading_repo)
    domain_readings, total_count = await use_case.execute(
        page=page, size=size, language=language, difficulty=difficulty, age_category=age_category
    )
    # For list view, questions for each reading are not loaded to keep response lean.
    items = [ReadingResponseDTO.model_validate(r) for r in domain_readings]

    return PaginatedResponse[ReadingResponseDTO](
        items=items, total=total_count, page=page, size=size
    )


@router.put("/readings/{reading_id}", response_model=ReadingResponseDTO)
async def admin_update_reading(
    reading_id: UUID = Path(..., description="The ID of the reading to update."),
    reading_data: ReadingUpdateDTO,
    current_admin: DomainUser = Depends(get_current_user),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo) # If questions need to be re-fetched
):
    """Allows Admins to update an existing reading material."""
    use_case = UpdateReadingUseCase(reading_repo)
    try:
        updated_reading = await use_case.execute(reading_id, reading_data, current_admin)
        # If response needs to show updated questions (if they could be part of reading_data implicitly)
        # This example assumes questions are managed separately.
        response_dto = ReadingResponseDTO.model_validate(updated_reading)
        # Optionally, fetch and attach questions if the update could affect them or if required by response contract.
        # questions = await ListQuizQuestionsByReadingUseCase(quiz_question_repo).execute(reading_id)
        # response_dto.questions = [QuizQuestionResponseDTO.model_validate(q) for q in questions]
        return response_dto
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e: # Catch other use case errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_reading(
    reading_id: UUID = Path(..., description="The ID of the reading to delete."),
    current_admin: DomainUser = Depends(get_current_user), # For audit/logging or pre-delete checks if needed
    reading_repo: ReadingRepository = Depends(get_reading_repo)
):
    """Allows Admins to delete a reading material.
    Note: Associated quiz questions might need manual deletion or cascading delete in DB.
    """
    use_case = DeleteReadingUseCase(reading_repo)
    try:
        success = await use_case.execute(reading_id, current_admin) # Pass admin for potential checks
        if not success: # Should be handled by NotFoundException from use case if not found
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found or delete failed.")
        return None
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- Quiz Questions Endpoints ---
@router.post("/questions", response_model=QuizQuestionResponseDTO, status_code=status.HTTP_201_CREATED)
async def admin_create_quiz_question(
    # Reading ID is now part of the DTO as per QuizQuestionCreateDTO
    question_data: QuizQuestionCreateDTO,
    current_admin: DomainUser = Depends(get_current_user),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo) # For use case to validate reading exists
):
    """Allows Admins to add a quiz question to an existing reading material."""
    use_case = AddQuizQuestionToReadingUseCase(quiz_question_repo, reading_repo)
    try:
        created_question = await use_case.execute(question_data, current_admin)
        return QuizQuestionResponseDTO.model_validate(created_question)
    except NotFoundException as e: # Handles if Reading for question_data.reading_id not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/readings/{reading_id}/questions", response_model=List[QuizQuestionResponseDTO])
async def admin_list_quiz_questions_for_reading(
    reading_id: UUID = Path(..., description="The ID of the reading material."),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
    # Optionally, add reading_repo to first verify reading_id exists
):
    """Allows Admins to list all quiz questions for a specific reading material."""
    # Consider adding a check: if not await GetReadingUseCase(reading_repo).execute(reading_id): error...
    use_case = ListQuizQuestionsByReadingUseCase(quiz_question_repo)
    questions = await use_case.execute(reading_id)
    return [QuizQuestionResponseDTO.model_validate(q) for q in questions]


@router.get("/questions/{question_id}", response_model=QuizQuestionResponseDTO)
async def admin_get_quiz_question(
    question_id: UUID = Path(..., description="The ID of the quiz question to retrieve."),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
):
    """Allows Admins to retrieve a specific quiz question by its ID."""
    use_case = GetQuizQuestionUseCase(quiz_question_repo)
    try:
        question = await use_case.execute(question_id)
        return QuizQuestionResponseDTO.model_validate(question)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/questions/{question_id}", response_model=QuizQuestionResponseDTO)
async def admin_update_quiz_question(
    question_id: UUID = Path(..., description="The ID of the quiz question to update."),
    question_data: QuizQuestionUpdateDTO,
    current_admin: DomainUser = Depends(get_current_user),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
):
    """Allows Admins to update an existing quiz question."""
    use_case = UpdateQuizQuestionUseCase(quiz_question_repo)
    try:
        updated_question = await use_case.execute(question_id, question_data, current_admin)
        return QuizQuestionResponseDTO.model_validate(updated_question)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_quiz_question(
    question_id: UUID = Path(..., description="The ID of the quiz question to delete."),
    current_admin: DomainUser = Depends(get_current_user), # For audit/checks
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)
):
    """Allows Admins to delete a quiz question."""
    use_case = DeleteQuizQuestionUseCase(quiz_question_repo)
    try:
        success = await use_case.execute(question_id, current_admin) # Pass admin for potential checks
        if not success: # Should be handled by NotFoundException
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz question not found or delete failed.")
        return None
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
