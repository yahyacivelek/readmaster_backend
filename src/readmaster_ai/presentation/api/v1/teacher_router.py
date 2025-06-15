"""
API Router for Teacher-specific operations, primarily Class Management,
Reading Assignments, and Progress Monitoring.
All endpoints in this router require TEACHER role (or ADMIN where use cases permit).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

# Infrastructure (Database session for DI)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities, Enums for type hinting and auth)
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole

# Presentation (Dependencies, Schemas from Application DTOs)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user, require_role
from readmaster_ai.application.dto.class_dtos import (
    ClassCreateDTO, ClassUpdateDTO, ClassResponseDTO, AddStudentToClassRequestDTO
)
from readmaster_ai.application.dto.user_dtos import UserResponseDTO
from readmaster_ai.application.dto.assessment_dtos import AssignReadingRequestDTO, AssignmentResponseDTO
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO, ClassProgressReportDTO
from readmaster_ai.presentation.schemas.pagination import PaginatedResponse

# Repositories (Abstract for DI to Use Cases)
from readmaster_ai.domain.repositories.class_repository import ClassRepository
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.domain.repositories.notification_repository import NotificationRepository # New

# Infrastructure (Concrete Repositories for DI)
from readmaster_ai.infrastructure.database.repositories.class_repository_impl import ClassRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.assessment_repository_impl import AssessmentRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.assessment_result_repository_impl import AssessmentResultRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.notification_repository_impl import NotificationRepositoryImpl # New

# Application (Use Cases)
from readmaster_ai.application.use_cases.class_use_cases import (
    CreateClassUseCase, GetClassDetailsUseCase, ListClassesByTeacherUseCase,
    UpdateClassUseCase, DeleteClassUseCase, AddStudentToClassUseCase,
    RemoveStudentFromClassUseCase, ListStudentsInClassUseCase
)
from readmaster_ai.application.use_cases.assessment_use_cases import AssignReadingUseCase
from readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase, GetClassProgressReportUseCase
from readmaster_ai.application.use_cases.user_use_cases import CreateStudentByTeacherUseCase # New
from readmaster_ai.presentation.schemas.user_schemas import TeacherStudentCreateRequestSchema, UserResponse # New

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException, ForbiddenException

router = APIRouter(
    prefix="/teacher",
    tags=["Teacher - Class, Assignment & Progress"], # Updated tag
    dependencies=[Depends(require_role(UserRole.TEACHER))]
)

# --- Dependency Provider Functions for Repositories ---
def get_class_repo(session: AsyncSession = Depends(get_db)) -> ClassRepository: return ClassRepositoryImpl(session)
def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository: return UserRepositoryImpl(session)

# New DI for the CreateStudentByTeacherUseCase
def get_create_student_by_teacher_use_case(
    user_repo: UserRepository = Depends(get_user_repo)
) -> CreateStudentByTeacherUseCase:
    return CreateStudentByTeacherUseCase(user_repo=user_repo)

def get_assessment_repo(session: AsyncSession = Depends(get_db)) -> AssessmentRepository: return AssessmentRepositoryImpl(session)
def get_reading_repo(session: AsyncSession = Depends(get_db)) -> ReadingRepository: return ReadingRepositoryImpl(session)
def get_assessment_result_repo(session: AsyncSession = Depends(get_db)) -> AssessmentResultRepository: return AssessmentResultRepositoryImpl(session)
def get_notification_repo(session: AsyncSession = Depends(get_db)) -> NotificationRepository: return NotificationRepositoryImpl(session) # New


# --- Class Management Endpoints ---
@router.post("/classes", response_model=ClassResponseDTO, status_code=status.HTTP_201_CREATED)
async def teacher_create_class(dto: ClassCreateDTO, teacher: DomainUser = Depends(get_current_user), repo: ClassRepository = Depends(get_class_repo)):
    uc = CreateClassUseCase(repo)
    try: return ClassResponseDTO.model_validate(await uc.execute(dto, teacher))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/classes", response_model=PaginatedResponse[ClassResponseDTO])
async def teacher_list_my_classes(teacher: DomainUser = Depends(get_current_user), repo: ClassRepository = Depends(get_class_repo),
                               page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    uc = ListClassesByTeacherUseCase(repo)
    try:
        items, total = await uc.execute(teacher, page, size)
        return PaginatedResponse(items=[ClassResponseDTO.model_validate(i) for i in items], total=total, page=page, size=size)
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/classes/{class_id}", response_model=ClassResponseDTO)
async def teacher_get_class_details(class_id: UUID, teacher: DomainUser = Depends(get_current_user), class_repo: ClassRepository = Depends(get_class_repo)):
    uc = GetClassDetailsUseCase(class_repo)
    try:
        class_obj = await uc.execute(class_id, teacher)
        student_dtos = [UserResponseDTO.model_validate(s) for s in class_obj.students if s]
        class_dto = ClassResponseDTO.model_validate(class_obj)
        class_dto.students = student_dtos
        return class_dto
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))

@router.put("/classes/{class_id}", response_model=ClassResponseDTO)
async def teacher_update_class_details(class_id: UUID, dto: ClassUpdateDTO, teacher: DomainUser = Depends(get_current_user), repo: ClassRepository = Depends(get_class_repo)):
    uc = UpdateClassUseCase(repo)
    try: return ClassResponseDTO.model_validate(await uc.execute(class_id, dto, teacher))
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def teacher_delete_class(class_id: UUID, teacher: DomainUser = Depends(get_current_user), repo: ClassRepository = Depends(get_class_repo)):
    uc = DeleteClassUseCase(repo)
    try:
        if not await uc.execute(class_id, teacher): raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Deletion failed.")
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/classes/{class_id}/students", response_model=ClassResponseDTO)
async def teacher_add_student_to_class(class_id: UUID, dto: AddStudentToClassRequestDTO, teacher: DomainUser = Depends(get_current_user),
                                       class_repo: ClassRepository = Depends(get_class_repo), user_repo: UserRepository = Depends(get_user_repo)):
    uc = AddStudentToClassUseCase(class_repo, user_repo)
    try:
        await uc.execute(class_id, dto.student_id, teacher)
        get_uc = GetClassDetailsUseCase(class_repo)
        class_obj = await get_uc.execute(class_id, teacher)
        student_dtos = [UserResponseDTO.model_validate(s) for s in class_obj.students if s]
        class_dto_resp = ClassResponseDTO.model_validate(class_obj)
        class_dto_resp.students = student_dtos
        return class_dto_resp
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/classes/{class_id}/students/{student_id}", response_model=ClassResponseDTO)
async def teacher_remove_student_from_class(class_id: UUID, student_id: UUID, teacher: DomainUser = Depends(get_current_user), class_repo: ClassRepository = Depends(get_class_repo)):
    uc = RemoveStudentFromClassUseCase(class_repo)
    try:
        if not await uc.execute(class_id, student_id, teacher): raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not in class.")
        get_uc = GetClassDetailsUseCase(class_repo)
        class_obj = await get_uc.execute(class_id, teacher)
        student_dtos = [UserResponseDTO.model_validate(s) for s in class_obj.students if s]
        class_dto_resp = ClassResponseDTO.model_validate(class_obj)
        class_dto_resp.students = student_dtos
        return class_dto_resp
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/classes/{class_id}/students", response_model=List[UserResponseDTO])
async def teacher_list_students_in_class(class_id: UUID, teacher: DomainUser = Depends(get_current_user), class_repo: ClassRepository = Depends(get_class_repo)):
    uc = ListStudentsInClassUseCase(class_repo)
    try: return [UserResponseDTO.model_validate(s) for s in await uc.execute(class_id, teacher) if s]
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))

# --- Reading Assignment Endpoint ---
@router.post("/assignments/readings", response_model=AssignmentResponseDTO, status_code=status.HTTP_201_CREATED)
async def teacher_assign_reading_to_students(
    request_data: AssignReadingRequestDTO,
    teacher: DomainUser = Depends(get_current_user),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    class_repo: ClassRepository = Depends(get_class_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo) # Added
):
    use_case = AssignReadingUseCase(
        assessment_repo, reading_repo, class_repo, user_repo, notification_repo # Pass it here
    )
    try:
        return await use_case.execute(request_data, teacher)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error assigning reading: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while assigning the reading.")

# --- Progress Monitoring Endpoints ---
@router.get("/classes/{class_id}/progress-report", response_model=ClassProgressReportDTO)
async def teacher_get_class_progress_report(class_id: UUID, teacher: DomainUser = Depends(get_current_user),
                                            class_repo: ClassRepository = Depends(get_class_repo), user_repo: UserRepository = Depends(get_user_repo),
                                            assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
                                            result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo),
                                            reading_repo: ReadingRepository = Depends(get_reading_repo)):
    student_progress_uc = GetStudentProgressSummaryUseCase(user_repo, assessment_repo, result_repo, reading_repo)
    class_report_uc = GetClassProgressReportUseCase(class_repo, student_progress_uc, user_repo)
    try: return await class_report_uc.execute(class_id, teacher)
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error generating class progress report: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while generating the class progress report.")

@router.get("/students/{student_id}/progress-summary", response_model=StudentProgressSummaryDTO)
async def teacher_get_student_progress_summary(student_id: UUID, teacher: DomainUser = Depends(get_current_user),
                                               user_repo: UserRepository = Depends(get_user_repo), assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
                                               result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo), reading_repo: ReadingRepository = Depends(get_reading_repo)):
    use_case = GetStudentProgressSummaryUseCase(user_repo, assessment_repo, result_repo, reading_repo)
    try: return await use_case.execute(student_id, teacher)
    except NotFoundException as e: raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenException as e: raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Unexpected error generating student progress summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while generating the student progress summary.")


@router.post(
    "/students", # Path based on swagger: /api/v1/teacher/students
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Teacher Create Student Account", # From Swagger
    tags=["Teacher - Account Management"] # New tag as per Swagger
)
async def teacher_create_student_account(
    request_data: TeacherStudentCreateRequestSchema,
    current_teacher: DomainUser = Depends(get_current_user), # Ensures authenticated and gets teacher user
    use_case: CreateStudentByTeacherUseCase = Depends(get_create_student_by_teacher_use_case)
):
    """
    Allows an authenticated teacher to create a new student account.
    The created user's role will be 'student'. This student can then be
    added to a class using another endpoint.
    """
    # Router-level dependency `require_role(UserRole.TEACHER)` should enforce teacher role.
    try:
        # The use case already checks if current_teacher.role is TEACHER.
        created_student_domain = await use_case.execute(teacher_user=current_teacher, student_data=request_data)
        return UserResponse.model_validate(created_student_domain)
    except ForbiddenException as e: # From use case if teacher_user.role is not TEACHER
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ApplicationException as e: # Handles other errors like email already exists (409)
        # The use case might use ApplicationException with status 403 for role check if ForbiddenException is not used there.
        if hasattr(e, 'status_code') and e.status_code == 403:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e.message if hasattr(e, 'message') else str(e)))
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 400, detail=str(e.message if hasattr(e, 'message') else str(e)))
    except Exception as e:
        # Log unexpected errors
        print(f"Unexpected error in teacher_create_student_account: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while creating the student account.")
