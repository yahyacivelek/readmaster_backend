"""
API Router for Parent-specific operations, such as viewing children's progress.
All endpoints in this router require PARENT role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession # For DI context
from typing import List
from uuid import UUID

# Infrastructure (Database session for DI)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities, Enums for type hinting and auth)
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole

# Presentation (Dependencies, DTOs from Application)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user, require_role
from readmaster_ai.application.dto.user_dtos import UserResponseDTO
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO

# Repositories (Abstract for DI to Use Cases and their dependencies)
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository

# Infrastructure (Concrete Repositories for DI)
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.assessment_repository_impl import AssessmentRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.assessment_result_repository_impl import AssessmentResultRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.student_quiz_answer_repository_impl import StudentQuizAnswerRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.quiz_question_repository_impl import QuizQuestionRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl

# Application (Use Cases)
from readmaster_ai.application.use_cases.parent_use_cases import (
    ListParentChildrenUseCase, GetChildProgressForParentUseCase, GetChildAssessmentResultForParentUseCase
)
# Reused Use Cases (needed for DI into parent use cases)
from readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase
from readmaster_ai.application.use_cases.assessment_use_cases import GetAssessmentResultDetailsUseCase

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException, ForbiddenException, ApplicationException

router = APIRouter(
    prefix="/parent",
    tags=["Parent - Child Monitoring"],
    dependencies=[Depends(require_role(UserRole.PARENT))] # Protect all routes
)

# --- DI for Repositories (many are needed for the reused use cases) ---
def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository: return UserRepositoryImpl(session)
def get_assessment_repo(session: AsyncSession = Depends(get_db)) -> AssessmentRepository: return AssessmentRepositoryImpl(session)
def get_assessment_result_repo(session: AsyncSession = Depends(get_db)) -> AssessmentResultRepository: return AssessmentResultRepositoryImpl(session)
def get_reading_repo(session: AsyncSession = Depends(get_db)) -> ReadingRepository: return ReadingRepositoryImpl(session)
def get_student_answer_repo(session: AsyncSession = Depends(get_db)) -> StudentQuizAnswerRepository: return StudentQuizAnswerRepositoryImpl(session)
def get_quiz_question_repo(session: AsyncSession = Depends(get_db)) -> QuizQuestionRepository: return QuizQuestionRepositoryImpl(session)

# --- DI for Reused Use Cases (which are dependencies of Parent Use Cases) ---
def get_student_progress_summary_uc(
    user_repo: UserRepository = Depends(get_user_repo),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo)
) -> GetStudentProgressSummaryUseCase:
    return GetStudentProgressSummaryUseCase(user_repo, assessment_repo, result_repo, reading_repo)

def get_assessment_result_details_uc(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    assessment_result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo),
    student_answer_repo: StudentQuizAnswerRepository = Depends(get_student_answer_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo)
) -> GetAssessmentResultDetailsUseCase:
    return GetAssessmentResultDetailsUseCase(assessment_repo, assessment_result_repo, student_answer_repo, quiz_question_repo, reading_repo)


# --- Parent Endpoints ---
@router.get("/my-children", response_model=List[UserResponseDTO])
async def parent_list_my_children(
    parent: DomainUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """Lists all children linked to the authenticated parent."""
    use_case = ListParentChildrenUseCase(user_repo)
    try:
        return await use_case.execute(parent)
    except ForbiddenException as e: # Should be caught by router dependency, but defensive
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/children/{child_student_id}/progress", response_model=StudentProgressSummaryDTO)
async def parent_get_child_progress_summary(
    child_student_id: UUID = Path(..., description="The ID of the child (student) whose progress is to be viewed."),
    parent: DomainUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
    # All repos for student_progress_uc are injected via its DI function
    student_progress_uc_instance: GetStudentProgressSummaryUseCase = Depends(get_student_progress_summary_uc)
):
    """Allows a parent to view the progress summary of one of their linked children."""
    use_case = GetChildProgressForParentUseCase(user_repo, student_progress_uc_instance)
    try:
        return await use_case.execute(parent, child_student_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: # Other errors from use case
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error getting child progress for parent: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")

@router.get("/children/{child_student_id}/assessments/{assessment_id}/results", response_model=AssessmentResultDetailDTO)
async def parent_get_child_assessment_result_details(
    child_student_id: UUID = Path(..., description="The ID of the child (student)."),
    assessment_id: UUID = Path(..., description="The ID of the assessment."),
    parent: DomainUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
    # All repos for assessment_details_uc are injected via its DI function
    assessment_details_uc_instance: GetAssessmentResultDetailsUseCase = Depends(get_assessment_result_details_uc)
):
    """Allows a parent to view detailed results of a specific assessment for one of their linked children."""
    use_case = GetChildAssessmentResultForParentUseCase(user_repo, assessment_details_uc_instance)
    try:
        return await use_case.execute(parent, child_student_id, assessment_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error getting child assessment result for parent: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred.")

# Endpoint to link a parent to a student (conceptual - typically done by Admin or system process)
# @router.post("/link-child", status_code=status.HTTP_204_NO_CONTENT)
# async def link_child_to_parent(
#     student_id: UUID, # This would come from a request body DTO
#     relationship_type: str, # e.g., "mother", "father", "guardian"
#     parent: DomainUser = Depends(get_current_user),
#     user_repo: UserRepository = Depends(get_user_repo)
# ):
#     try:
#         success = await user_repo.link_parent_to_student(parent.user_id, student_id, relationship_type)
#         if not success: # Should be handled by exceptions in repo method
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to link child.")
#         return None
#     except NotFoundException as e:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error linking child.")
