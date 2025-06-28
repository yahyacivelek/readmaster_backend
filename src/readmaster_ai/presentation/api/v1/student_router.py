"""
API Router for Student related operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Application Layer
from readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO

# Presentation Layer

# Infrastructure Layer (for DI)
from readmaster_ai.infrastructure.database.config import get_db
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository

# Shared Layer
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.shared.exceptions import ApplicationException

# For get_current_user dependency and DomainUser type hint
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user

router = APIRouter(prefix="/student", tags=["Student - Progress"])

# Dependency Injection for Repositories
def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Provides a UserRepository implementation."""
    from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
    return UserRepositoryImpl(session)

def get_assessment_repository(session: AsyncSession = Depends(get_db)) -> AssessmentRepository:
    """Provides an AssessmentRepository implementation."""
    from readmaster_ai.infrastructure.database.repositories.assessment_repository_impl import AssessmentRepositoryImpl
    return AssessmentRepositoryImpl(session)

def get_result_repository(session: AsyncSession = Depends(get_db)) -> AssessmentResultRepository:
    """Provides an AssessmentResultRepository implementation."""
    from readmaster_ai.infrastructure.database.repositories.assessment_result_repository_impl import AssessmentResultRepositoryImpl
    return AssessmentResultRepositoryImpl(session)

def get_reading_repository(session: AsyncSession = Depends(get_db)) -> ReadingRepository:
    """Provides a ReadingRepository implementation."""
    from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
    return ReadingRepositoryImpl(session)

@router.get("/progress-summary", response_model=StudentProgressSummaryDTO)
async def get_student_progress_summary(
    current_user: DomainUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    result_repo: AssessmentResultRepository = Depends(get_result_repository),
    reading_repo: ReadingRepository = Depends(get_reading_repository)
):
    """
    Retrieves a comprehensive progress summary for the authenticated student.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access their progress summary"
        )

    progress_use_case = GetStudentProgressSummaryUseCase(
        user_repo=user_repo,
        assessment_repo=assessment_repo,
        result_repo=result_repo,
        reading_repo=reading_repo
    )

    try:
        progress_summary = await progress_use_case._compile_summary_for_student(current_user)
        return progress_summary
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching progress summary"
        )

