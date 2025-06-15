"""
Dependency injection setup for application use cases.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Database session
from readmaster_ai.infrastructure.database.config import get_db

# Repository Interfaces
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
# from readmaster_ai.domain.repositories.iparent_student_link_repository import IParentStudentLinkRepository # If created

# Repository Implementations
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.assessment_repository_impl import AssessmentRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
# from readmaster_ai.infrastructure.database.repositories.sqla_parent_student_link_repository import SQLAParentStudentLinkRepositoryImpl # If created

# Use Cases
from readmaster_ai.application.use_cases.parent_use_cases import (
    CreateChildAccountUseCase,
    ParentAssignReadingUseCase,
    ListChildAssignmentsUseCase,
    UpdateChildAssignmentUseCase,
    DeleteChildAssignmentUseCase,
)
from readmaster_ai.application.use_cases.teacher_use_cases import CreateStudentByTeacherUseCase
from readmaster_ai.application.use_cases.assessment_use_cases import ListAssessmentsByReadingIdUseCase


# Service dependencies (e.g., PasswordService)
from readmaster_ai.services.password_service import PasswordService # Assuming this path
# from readmaster_ai.application.services.password_service import PasswordService # Alternative path

# --- Repository Dependency Providers ---

def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepositoryImpl(session)

def get_assessment_repository(session: AsyncSession = Depends(get_db)) -> AssessmentRepository:
    return AssessmentRepositoryImpl(session)

def get_reading_repository(session: AsyncSession = Depends(get_db)) -> ReadingRepository:
    return ReadingRepositoryImpl(session)

# def get_parent_student_link_repository(session: AsyncSession = Depends(get_db)) -> IParentStudentLinkRepository:
#     return SQLAParentStudentLinkRepositoryImpl(session)

# --- Service Dependency Providers ---
def get_password_service() -> PasswordService:
    return PasswordService()


# --- Parent Use Case Dependency Providers ---

def get_create_child_account_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
    password_service: PasswordService = Depends(get_password_service)
    # parent_student_link_repo: IParentStudentLinkRepository = Depends(get_parent_student_link_repository) # If separate
) -> CreateChildAccountUseCase:
    return CreateChildAccountUseCase(user_repository=user_repo, password_service=password_service) # , parent_student_link_repository=parent_student_link_repo)

def get_parent_assign_reading_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    reading_repo: ReadingRepository = Depends(get_reading_repository),
) -> ParentAssignReadingUseCase:
    return ParentAssignReadingUseCase(
        assessment_repository=assessment_repo,
        user_repository=user_repo,
        reading_repository=reading_repo
    )

def get_list_child_assignments_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    reading_repo: ReadingRepository = Depends(get_reading_repository),
) -> ListChildAssignmentsUseCase:
    return ListChildAssignmentsUseCase(
        assessment_repository=assessment_repo,
        user_repository=user_repo,
        reading_repository=reading_repo
    )

def get_update_child_assignment_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UpdateChildAssignmentUseCase:
    return UpdateChildAssignmentUseCase(
        assessment_repository=assessment_repo,
        user_repository=user_repo
    )

def get_delete_child_assignment_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> DeleteChildAssignmentUseCase:
    return DeleteChildAssignmentUseCase(
        assessment_repository=assessment_repo,
        user_repository=user_repo
    )


# --- Teacher Use Case Dependency Providers ---

def get_create_student_by_teacher_use_case(
    user_repo: UserRepository = Depends(get_user_repository),
    password_service: PasswordService = Depends(get_password_service)
) -> CreateStudentByTeacherUseCase:
    return CreateStudentByTeacherUseCase(user_repository=user_repo, password_service=password_service)


# --- Assessment Use Case Dependency Providers ---

def get_list_assessments_by_reading_id_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repository),
    reading_repo: ReadingRepository = Depends(get_reading_repository),
    user_repo: UserRepository = Depends(get_user_repository)
) -> ListAssessmentsByReadingIdUseCase:
    return ListAssessmentsByReadingIdUseCase(
        assessment_repo=assessment_repo,
        reading_repo=reading_repo,
        user_repo=user_repo
    )


# Add other use case providers here following the same pattern.
