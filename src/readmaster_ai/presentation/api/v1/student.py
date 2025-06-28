from fastapi import APIRouter, Depends, Query
from uuid import UUID

from readmaster_ai.application.dto.student_dto import PaginatedStudentAssignmentResponseDTO, StudentAssignmentItemDTO
from readmaster_ai.application.use_cases.list_student_assignments_use_case import ListStudentAssignmentsUseCase # Keep for type hint
from readmaster_ai.presentation.dependencies.use_case_dependencies import get_list_student_assignments_use_case # Import the provider
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects import AssessmentStatus
from readmaster_ai.presentation.dependencies.auth_deps import get_current_active_student
from readmaster_ai.presentation.schemas.common import ErrorResponse

router = APIRouter(
    tags=["Student - Assignments"],
    responses={
        401: {"description": "Unauthorized", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
        422: {"description": "Validation Error", "model": ErrorResponse},
    },
)

@router.get(
    "/student/assignments",
    response_model=PaginatedStudentAssignmentResponseDTO,
    summary="List My Assignments",
    description="Retrieves a paginated list of assignments for the authenticated student.",
    operation_id="list_my_assignments_api_v1_student_assignments_get",
)
async def list_my_assignments(
    current_student: User = Depends(get_current_active_student),
    page: int = Query(1, ge=1, description="Page number for pagination."),
    size: int = Query(20, ge=1, le=100, description="Number of items per page."),
    status: AssessmentStatus | None = Query(None, description="Filter assignments by status (e.g., pending_audio, completed)."),
    use_case: ListStudentAssignmentsUseCase = Depends(get_list_student_assignments_use_case)
) -> PaginatedStudentAssignmentResponseDTO:
    """
    Retrieves a paginated list of assignments for the authenticated student.
    """
    assignments, total_count = await use_case.execute(
        student_id=current_student.user_id, # Corrected: DomainUser uses user_id
        page=page,
        size=size,
        status=status,
    )
    return PaginatedStudentAssignmentResponseDTO(
        items=assignments,
        page=page,
        size=size,
        total=total_count # Ensure DTO field name matches (total vs total_count)
    )
