"""
API Router for Parent-specific operations, such as viewing children's progress.
All endpoints in this router require PARENT role.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
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
from readmaster_ai.application.dto.user_dtos import UserResponseDTO, ParentChildCreateRequestDTO
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO, ParentAssignReadingRequestDTO

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
    ListParentChildrenUseCase, GetChildProgressForParentUseCase, GetChildAssessmentResultForParentUseCase,
    CreateChildAccountUseCase, # Renamed
    ParentAssignReadingUseCase,
    ListChildAssignmentsUseCase,
    UpdateChildAssignmentUseCase,
    DeleteChildAssignmentUseCase,
)
# Presentation Schemas
from readmaster_ai.presentation.schemas.user_schemas import ParentChildCreateRequestSchema, UserResponse
from readmaster_ai.presentation.schemas.assessment_schemas import (
    ParentAssignReadingRequestSchema,
    AssessmentResponseSchema,
    AssignmentUpdateSchema,
    PaginatedAssessmentListResponseSchema,
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

# New DI for the CreateChildAccountUseCase
def get_create_child_account_use_case( # Renamed
    user_repo: UserRepository = Depends(get_user_repo)
) -> CreateChildAccountUseCase: # Renamed
    return CreateChildAccountUseCase(user_repository=user_repo) # Renamed internal var

# DI for new Assignment Use Cases
def get_parent_assign_reading_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
) -> ParentAssignReadingUseCase:
    return ParentAssignReadingUseCase(assessment_repository=assessment_repo, user_repository=user_repo, reading_repository=reading_repo)

def get_list_child_assignments_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
) -> ListChildAssignmentsUseCase:
    return ListChildAssignmentsUseCase(assessment_repository=assessment_repo, user_repository=user_repo, reading_repository=reading_repo)

def get_update_child_assignment_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UpdateChildAssignmentUseCase:
    return UpdateChildAssignmentUseCase(assessment_repository=assessment_repo, user_repository=user_repo)

def get_delete_child_assignment_use_case(
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> DeleteChildAssignmentUseCase:
    return DeleteChildAssignmentUseCase(assessment_repository=assessment_repo, user_repository=user_repo)


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
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo)
):
    """Allows a parent to view the progress summary of one of their linked children."""
    use_case = GetChildProgressForParentUseCase(
        user_repo=user_repo,
        assessment_repo=assessment_repo,
        result_repo=result_repo,
        reading_repo=reading_repo
    )
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


@router.post(
    "/children", # Path based on swagger: /api/v1/parent/children
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Parent Create Child Account",
    tags=["Parent - Account Management"]
)
async def parent_create_child_account( # Renamed function to match endpoint summary better
    request_schema: ParentChildCreateRequestSchema, # Correct schema from presentation layer
    current_parent: DomainUser = Depends(require_role(UserRole.PARENT)), # Explicitly use require_role here for clarity
    use_case: CreateChildAccountUseCase = Depends(get_create_child_account_use_case), # Use renamed UC
):
    """
    Allows an authenticated parent to create a new student account linked to them.
    """
    try:
        # Map schema to DTO for the use case
        child_dto = ParentChildCreateRequestDTO(**request_schema.model_dump())
        created_child_user_dto = await use_case.execute(parent_user=current_parent, child_data=child_dto)
        # Map DTO back to response schema
        return UserResponse(**created_child_user_dto.dict())
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 400, detail=str(e.message if hasattr(e, 'message') else str(e)))
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in parent_create_child_account: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


# --- Parent Assignment Endpoints ---

@router.post(
    "/children/{child_id}/assignments",
    response_model=AssessmentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Parent Assign Reading to Child",
    tags=["Parent - Assignments"]
)
async def parent_assign_reading_to_child(
    child_id: UUID,
    request_schema: ParentAssignReadingRequestSchema,
    current_parent: DomainUser = Depends(require_role(UserRole.PARENT)),
    use_case: ParentAssignReadingUseCase = Depends(get_parent_assign_reading_use_case),
):
    """
    Allows an authenticated parent to assign a specific reading material to one of their linked children.
    """
    try:
        assign_dto = ParentAssignReadingRequestDTO(**request_schema.model_dump())
        assessment = await use_case.execute(
            parent_user=current_parent,
            child_id=child_id,
            assign_data=assign_dto
        )
        return AssessmentResponseSchema.model_validate(assessment)
    except (NotFoundException, ForbiddenException) as e:
        status_code_map = {NotFoundException: status.HTTP_404_NOT_FOUND, ForbiddenException: status.HTTP_403_FORBIDDEN}
        raise HTTPException(status_code=status_code_map.get(type(e), status.HTTP_400_BAD_REQUEST), detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 500, detail=str(e))


@router.get(
    "/children/{child_id}/assignments",
    response_model=PaginatedAssessmentListResponseSchema,
    summary="Parent List Child's Assignments",
    tags=["Parent - Assignments"]
)
async def parent_list_child_assignments(
    child_id: UUID,
    current_parent: DomainUser = Depends(require_role(UserRole.PARENT)),
    use_case: ListChildAssignmentsUseCase = Depends(get_list_child_assignments_use_case),
    page: int = Query(1, ge=1, description="Page number for pagination."),
    size: int = Query(20, ge=1, le=100, description="Number of items per page."),
):
    """
    Retrieves a list of all readings assigned by the parent to a specific child.
    """
    try:
        paginated_result_dto = await use_case.execute(
            parent_user=current_parent,
            child_id=child_id,
            page=page,
            size=size
        )
        # The DTO from use case should directly map to the schema
        return paginated_result_dto
    except (NotFoundException, ForbiddenException) as e:
        status_code_map = {NotFoundException: status.HTTP_404_NOT_FOUND, ForbiddenException: status.HTTP_403_FORBIDDEN}
        raise HTTPException(status_code=status_code_map.get(type(e), status.HTTP_400_BAD_REQUEST), detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 500, detail=str(e))


@router.put(
    "/children/{child_id}/assignments/{assignment_id}",
    response_model=AssessmentResponseSchema,
    summary="Parent Update Child's Assignment",
    tags=["Parent - Assignments"]
)
async def parent_update_child_assignment(
    child_id: UUID,
    assignment_id: UUID,
    request_schema: AssignmentUpdateSchema,
    current_parent: DomainUser = Depends(require_role(UserRole.PARENT)),
    use_case: UpdateChildAssignmentUseCase = Depends(get_update_child_assignment_use_case),
):
    """
    Allows an authenticated parent to update details (e.g., due date) of an existing assignment for their child.
    Note: Currently, `due_date` update is a no-op as it's not stored on the Assessment entity.
    """
    try:
        update_dto = AssignmentUpdateDTO(**request_schema.model_dump(exclude_unset=True))
        updated_assessment = await use_case.execute(
            parent_user=current_parent,
            child_id=child_id,
            assignment_id=assignment_id,
            update_data=update_dto
        )
        return AssessmentResponseSchema.model_validate(updated_assessment)
    except (NotFoundException, ForbiddenException) as e:
        status_code_map = {NotFoundException: status.HTTP_404_NOT_FOUND, ForbiddenException: status.HTTP_403_FORBIDDEN}
        raise HTTPException(status_code=status_code_map.get(type(e), status.HTTP_400_BAD_REQUEST), detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 500, detail=str(e))


@router.delete(
    "/children/{child_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Parent Delete Child's Assignment",
    tags=["Parent - Assignments"]
)
async def parent_delete_child_assignment(
    child_id: UUID,
    assignment_id: UUID,
    current_parent: DomainUser = Depends(require_role(UserRole.PARENT)),
    use_case: DeleteChildAssignmentUseCase = Depends(get_delete_child_assignment_use_case),
):
    """
    Allows an authenticated parent to delete a specific assignment for their child.
    """
    try:
        await use_case.execute(
            parent_user=current_parent,
            child_id=child_id,
            assignment_id=assignment_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except (NotFoundException, ForbiddenException) as e:
        status_code_map = {NotFoundException: status.HTTP_404_NOT_FOUND, ForbiddenException: status.HTTP_403_FORBIDDEN}
        raise HTTPException(status_code=status_code_map.get(type(e), status.HTTP_400_BAD_REQUEST), detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else 500, detail=str(e))
