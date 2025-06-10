"""
API Router for Admin-specific operations, including management of
Reading materials, Quiz Questions, and System Configurations.
All endpoints in this router require ADMIN role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

# Infrastructure (Database session)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities, Enums, Repositories - Abstract)
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole, DifficultyLevel
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.domain.repositories.system_configuration_repository import SystemConfigurationRepository # New

# Infrastructure (Repositories - Concrete for DI)
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.quiz_question_repository_impl import QuizQuestionRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.system_configuration_repository_impl import SystemConfigurationRepositoryImpl # New

# Presentation (Dependencies, Schemas - DTOs are imported from Application)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user, require_role
from readmaster_ai.presentation.schemas.pagination import PaginatedResponse

# Application (DTOs, Use Cases)
from readmaster_ai.application.dto.reading_dtos import ReadingCreateDTO, ReadingUpdateDTO, ReadingResponseDTO
from readmaster_ai.application.dto.quiz_question_dtos import QuizQuestionCreateDTO, QuizQuestionUpdateDTO, QuizQuestionResponseDTO
from readmaster_ai.application.dto.system_config_dtos import SystemConfigResponseDTO, SystemConfigUpdateDTO # New
from readmaster_ai.application.use_cases.reading_use_cases import (
    CreateReadingUseCase, GetReadingUseCase, ListReadingsUseCase, UpdateReadingUseCase, DeleteReadingUseCase
)
from readmaster_ai.application.use_cases.quiz_question_use_cases import (
    AddQuizQuestionToReadingUseCase, GetQuizQuestionUseCase, ListQuizQuestionsByReadingUseCase,
    UpdateQuizQuestionUseCase, DeleteQuizQuestionUseCase
)
from readmaster_ai.application.use_cases.system_config_use_cases import ( # New
    GetSystemConfigurationUseCase, UpdateSystemConfigurationUseCase, ListSystemConfigurationsUseCase
)

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException


router = APIRouter(
    prefix="/admin",
    tags=["Admin Management"],
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)

# --- Repository Dependency Provider Functions ---
def get_reading_repo(session: AsyncSession = Depends(get_db)) -> ReadingRepository:
    return ReadingRepositoryImpl(session)

def get_quiz_question_repo(session: AsyncSession = Depends(get_db)) -> QuizQuestionRepository:
    return QuizQuestionRepositoryImpl(session)

def get_system_config_repo(session: AsyncSession = Depends(get_db)) -> SystemConfigurationRepository: # New
    return SystemConfigurationRepositoryImpl(session)

# --- Readings Endpoints ---
@router.post("/readings", response_model=ReadingResponseDTO, status_code=status.HTTP_201_CREATED)
async def admin_create_reading(
    reading_data: ReadingCreateDTO,
    current_admin: DomainUser = Depends(get_current_user),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    config_repo: SystemConfigurationRepository = Depends(get_system_config_repo) # Add config_repo DI
):
    use_case = CreateReadingUseCase(reading_repo, config_repo) # Pass config_repo
    try:
        created_reading = await use_case.execute(reading_data, current_admin)
        response_dto = ReadingResponseDTO.model_validate(created_reading)
        # Ensure questions field is present in the response, even if empty, as per DTO definition
        if not hasattr(response_dto, 'questions') or response_dto.questions is None:
             response_dto.questions = []
        return response_dto
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error creating reading: {e}") # Log unexpected errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/readings/{reading_id}", response_model=ReadingResponseDTO)
async def admin_get_reading_with_questions(reading_id: UUID = Path(..., description="The ID of the reading to retrieve"),
                                       reading_repo: ReadingRepository = Depends(get_reading_repo),
                                       quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)):
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
async def admin_list_readings(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                              language: Optional[str] = Query(None), difficulty: Optional[DifficultyLevel] = Query(None),
                              age_category: Optional[str] = Query(None), reading_repo: ReadingRepository = Depends(get_reading_repo)):
    use_case = ListReadingsUseCase(reading_repo)
    domain_readings, total_count = await use_case.execute(page=page, size=size, language=language, difficulty=difficulty, age_category=age_category)
    items = [ReadingResponseDTO.model_validate(r) for r in domain_readings]
    return PaginatedResponse[ReadingResponseDTO](items=items, total=total_count, page=page, size=size)

@router.put("/readings/{reading_id}", response_model=ReadingResponseDTO)
async def admin_update_reading(reading_id: UUID, reading_data: ReadingUpdateDTO, current_admin: DomainUser = Depends(get_current_user),
                               reading_repo: ReadingRepository = Depends(get_reading_repo)): # Removed quiz_question_repo as it's not used in UC
    use_case = UpdateReadingUseCase(reading_repo)
    try:
        updated_reading = await use_case.execute(reading_id, reading_data, current_admin)
        return ReadingResponseDTO.model_validate(updated_reading)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/readings/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_reading(reading_id: UUID, current_admin: DomainUser = Depends(get_current_user),
                               reading_repo: ReadingRepository = Depends(get_reading_repo)):
    use_case = DeleteReadingUseCase(reading_repo)
    try:
        if not await use_case.execute(reading_id, current_admin):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reading not found or delete failed.") # More specific
    except NotFoundException as e: # Should be caught by the check above or if execute raises it
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# --- Quiz Questions Endpoints ---
@router.post("/questions", response_model=QuizQuestionResponseDTO, status_code=status.HTTP_201_CREATED)
async def admin_create_quiz_question(question_data: QuizQuestionCreateDTO, current_admin: DomainUser = Depends(get_current_user),
                                   quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo),
                                   reading_repo: ReadingRepository = Depends(get_reading_repo)):
    use_case = AddQuizQuestionToReadingUseCase(quiz_question_repo, reading_repo)
    try:
        created_question = await use_case.execute(question_data, current_admin)
        return QuizQuestionResponseDTO.model_validate(created_question)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/readings/{reading_id}/questions", response_model=List[QuizQuestionResponseDTO])
async def admin_list_quiz_questions_for_reading(reading_id: UUID, quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)):
    use_case = ListQuizQuestionsByReadingUseCase(quiz_question_repo)
    questions = await use_case.execute(reading_id)
    return [QuizQuestionResponseDTO.model_validate(q) for q in questions]

@router.get("/questions/{question_id}", response_model=QuizQuestionResponseDTO)
async def admin_get_quiz_question(question_id: UUID, quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)):
    use_case = GetQuizQuestionUseCase(quiz_question_repo)
    try:
        question = await use_case.execute(question_id)
        return QuizQuestionResponseDTO.model_validate(question)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/questions/{question_id}", response_model=QuizQuestionResponseDTO)
async def admin_update_quiz_question(question_id: UUID, question_data: QuizQuestionUpdateDTO,
                                   current_admin: DomainUser = Depends(get_current_user),
                                   quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)):
    use_case = UpdateQuizQuestionUseCase(quiz_question_repo)
    try:
        updated_question = await use_case.execute(question_id, question_data, current_admin)
        return QuizQuestionResponseDTO.model_validate(updated_question)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_quiz_question(question_id: UUID, current_admin: DomainUser = Depends(get_current_user),
                                     quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo)):
    use_case = DeleteQuizQuestionUseCase(quiz_question_repo)
    try:
        if not await use_case.execute(question_id, current_admin):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz question not found or delete failed.")
    except NotFoundException as e: # Should be caught by the check above or if execute raises it
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- System Configuration Endpoints ---
@router.get("/system-configurations", response_model=List[SystemConfigResponseDTO], tags=["Admin - System Configuration"])
async def admin_list_system_configurations(
    config_repo: SystemConfigurationRepository = Depends(get_system_config_repo)
):
    use_case = ListSystemConfigurationsUseCase(config_repo)
    configs_domain = await use_case.execute()
    return [SystemConfigResponseDTO.model_validate(c) for c in configs_domain]

@router.get("/system-configurations/{config_key}", response_model=SystemConfigResponseDTO, tags=["Admin - System Configuration"])
async def admin_get_system_configuration(
    config_key: str = Path(..., description="The key of the configuration to retrieve"),
    config_repo: SystemConfigurationRepository = Depends(get_system_config_repo)
):
    use_case = GetSystemConfigurationUseCase(config_repo)
    try:
        config_domain = await use_case.execute(config_key)
        return SystemConfigResponseDTO.model_validate(config_domain)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/system-configurations/{config_key}", response_model=SystemConfigResponseDTO, tags=["Admin - System Configuration"])
async def admin_update_system_configuration(
    update_dto: SystemConfigUpdateDTO,
    config_key: str = Path(..., description="The key of the configuration to update or create"),
    config_repo: SystemConfigurationRepository = Depends(get_system_config_repo)
    # current_admin: DomainUser = Depends(get_current_user) # Already enforced by router dependency
):
    use_case = UpdateSystemConfigurationUseCase(config_repo)
    try:
        updated_config_domain = await use_case.execute(config_key, update_dto)
        return SystemConfigResponseDTO.model_validate(updated_config_domain)
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log error e
        print(f"Unexpected error updating system config {config_key}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while updating system configuration.")
