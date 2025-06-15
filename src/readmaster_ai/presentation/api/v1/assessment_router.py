"""
API Router for Assessment related operations, including student-initiated actions
and teacher/parent views.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query # Added Query
from sqlalchemy.ext.asyncio import AsyncSession # Not directly used, but good for context if DI changes
from uuid import UUID

# Infrastructure (Database session for DI)
from readmaster_ai.infrastructure.database.config import get_db

# Domain (Entities for type hinting)
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # Added UserRole

# Presentation (Dependencies, DTOs from Application)
from readmaster_ai.presentation.dependencies.auth_deps import get_current_user
from readmaster_ai.application.dto.assessment_dtos import (
    StartAssessmentRequestDTO,
    AssessmentResponseDTO,
    RequestUploadURLResponseDTO,
    ConfirmUploadRequestDTO,
    ConfirmUploadResponseDTO,
    QuizSubmissionRequestDTO,
    QuizSubmissionResponseDTO,
    AssessmentResultDetailDTO # Added
)
from readmaster_ai.application.dto.assessment_list_dto import PaginatedAssessmentListResponseDTO # Added

# Repositories (Abstract for DI)
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository # Added
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository # Added
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository # Added
from readmaster_ai.domain.repositories.user_repository import UserRepository # Added


# Infrastructure (Concrete Repositories for DI)
from readmaster_ai.infrastructure.database.repositories.assessment_repository_impl import AssessmentRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl
from readmaster_ai.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl # Added
from readmaster_ai.application.interfaces.file_storage_interface import FileStorageInterface
from readmaster_ai.infrastructure.file_storage.local_storage import LocalFileStorageService
from readmaster_ai.infrastructure.database.repositories.quiz_question_repository_impl import QuizQuestionRepositoryImpl # Added
from readmaster_ai.infrastructure.database.repositories.student_quiz_answer_repository_impl import StudentQuizAnswerRepositoryImpl # Added
from readmaster_ai.infrastructure.database.repositories.assessment_result_repository_impl import AssessmentResultRepositoryImpl # Added


# Application (Use Cases)
from readmaster_ai.application.use_cases.assessment_use_cases import (
    StartAssessmentUseCase,
    RequestAssessmentAudioUploadURLUseCase,
    ConfirmAudioUploadUseCase,
    SubmitQuizAnswersUseCase,
    GetAssessmentResultDetailsUseCase, # Added
    ListAssessmentsByReadingIdUseCase # Added
)

# Shared (Exceptions)
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException

router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"], # Generalized tag
    dependencies=[Depends(get_current_user)] # All assessment routes require user authentication
)

# --- Repository Dependency Provider Functions ---
# These can be moved to a common dependencies module if they grow numerous or are widely shared.
def get_assessment_repo(session: AsyncSession = Depends(get_db)) -> AssessmentRepository:
    """Dependency provider for AssessmentRepository."""
    return AssessmentRepositoryImpl(session)

def get_reading_repo(session: AsyncSession = Depends(get_db)) -> ReadingRepository:
    """Dependency provider for ReadingRepository."""
    return ReadingRepositoryImpl(session)

# --- File Storage Service Dependency Getter ---
def get_file_storage_service() -> FileStorageInterface:
    """
    Dependency provider for FileStorageInterface.
    This is where you'd switch between Local, GCS, S3 based on configuration.
    """
    return LocalFileStorageService() # Using mock local storage for now

def get_quiz_question_repo(session: AsyncSession = Depends(get_db)) -> QuizQuestionRepository:
    """Dependency provider for QuizQuestionRepository."""
    return QuizQuestionRepositoryImpl(session)

def get_student_answer_repo(session: AsyncSession = Depends(get_db)) -> StudentQuizAnswerRepository:
    """Dependency provider for StudentQuizAnswerRepository."""
    return StudentQuizAnswerRepositoryImpl(session)

def get_assessment_result_repo(session: AsyncSession = Depends(get_db)) -> AssessmentResultRepository:
    """Dependency provider for AssessmentResultRepository."""
    return AssessmentResultRepositoryImpl(session)

def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository: # Added
    """Dependency provider for UserRepository."""
    return UserRepositoryImpl(session)


@router.get(
    "/reading/{reading_id}",
    response_model=PaginatedAssessmentListResponseDTO,
    summary="List Assessments by Reading ID for Teachers/Parents",
    # dependencies=[Depends(get_current_user)] # Already on router
)
async def list_assessments_by_reading_id_endpoint(
    reading_id: UUID = Path(..., description="The ID of the reading material."),
    page: int = Query(1, ge=1, description="Page number for pagination."),
    size: int = Query(20, ge=1, le=100, description="Number of items per page."),
    current_user: DomainUser = Depends(get_current_user),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo),
    user_repo: UserRepository = Depends(get_user_repo)
):
    """
    Allows Teachers and Parents to list all assessments for a specific reading material,
    filtered by students/children they own/manage.

    - **Teachers**: See assessments for students in their classes for this reading.
    - **Parents**: See assessments for their children for this reading.
    """
    if current_user.role not in [UserRole.TEACHER, UserRole.PARENT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )

    use_case = ListAssessmentsByReadingIdUseCase(
        assessment_repo=assessment_repo,
        reading_repo=reading_repo,
        user_repo=user_repo
    )

    try:
        result_dto = await use_case.execute(
            reading_id=reading_id,
            current_user=current_user,
            page=page,
            size=size
        )
        # An empty list is an acceptable response if no permissible data found.
        return result_dto
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        raise HTTPException(status_code=e.status_code if hasattr(e, 'status_code') else status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log error: print(f"Unexpected error in list_assessments_by_reading_id_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing assessments."
        )

@router.post("", response_model=AssessmentResponseDTO, status_code=status.HTTP_201_CREATED)
async def start_new_assessment(
    request_data: StartAssessmentRequestDTO,
    current_user: DomainUser = Depends(get_current_user), # Authenticated student
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo) # Required by StartAssessmentUseCase
):
    """
    Allows a student to start a new assessment for a specified reading material.
    This endpoint creates an assessment record with a 'pending_audio' status.
    """
    # Initialize the use case with its dependencies (repositories)
    use_case = StartAssessmentUseCase(assessment_repo=assessment_repo, reading_repo=reading_repo)

    try:
        # Execute the use case with the request data and the authenticated student
        created_assessment_domain = await use_case.execute(request_data, current_user)

        # Convert the resulting domain entity to the API response DTO
        # AssessmentResponseDTO can be directly created from the DomainAssessment entity
        # if its Pydantic Config has from_attributes = True and field names align.
        return AssessmentResponseDTO.model_validate(created_assessment_domain)

    except NotFoundException as e:
        # This exception is raised by the use case if the reading_id is not found.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e:
        # Catch other specific application errors from the use case
        # (e.g., if a student has too many pending assessments - a potential business rule)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Catch-all for any other unexpected errors during the process.
        # It's good practice to log these errors.
        # import logging
        # logging.exception("Unexpected error while starting assessment:")
        print(f"Unexpected error: {e}") # Basic print for now
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while starting the assessment."
        )

# Future endpoints for students:
# GET /assessments -> List their own assessments (PaginatedResponse[StudentAssessmentListItemDTO])
# GET /assessments/{assessment_id} -> Get details of one of their assessments (AssessmentResponseDTO or more detailed student DTO)
# POST /assessments/{assessment_id}/upload-audio -> This is now replaced by POST /request-upload-url then client PUTS to URL
# GET /assessments/{assessment_id}/result -> Get result (once processed)
# POST /assessments/{assessment_id}/quiz-answers -> Submit quiz answers for the assessment

@router.post("/{assessment_id}/request-upload-url", response_model=RequestUploadURLResponseDTO)
async def request_assessment_audio_upload_url(
    assessment_id: UUID = Path(..., description="The ID of the assessment for which to request an upload URL."),
    current_user: DomainUser = Depends(get_current_user),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    file_storage_service: FileStorageInterface = Depends(get_file_storage_service)
):
    """
    Requests a presigned URL for uploading the assessment audio file.
    The client should use this URL to PUT the audio file directly to the storage.
    """
    # The use case defaults content_type to "audio/wav".
    # If client needs to specify (e.g., "audio/mpeg", "audio/mp4"),
    # this endpoint could accept a 'content_type' query parameter or a small request body.
    client_content_type = "audio/wav" # Defaulting here, or get from request if designed so.

    use_case = RequestAssessmentAudioUploadURLUseCase(assessment_repo, file_storage_service)
    try:
        response_data = await use_case.execute(assessment_id, current_user, client_content_type)
        return response_data
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e: # Handles 403 (unauthorized), 400 (wrong status) from use case
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        # Log error e
        print(f"Unexpected error requesting upload URL: {e}") # Basic print for now
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while requesting upload URL.")


@router.post("/{assessment_id}/confirm-upload", response_model=ConfirmUploadResponseDTO)
async def confirm_assessment_audio_upload(
    request_data: ConfirmUploadRequestDTO,
    assessment_id: UUID = Path(..., description="The ID of the assessment for which upload is being confirmed."),
    current_user: DomainUser = Depends(get_current_user),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo)
    # file_storage_service is not directly needed by this endpoint,
    # as ConfirmAudioUploadUseCase currently doesn't use it to re-verify file existence.
):
    """
    Confirms that the audio file for an assessment has been successfully uploaded
    by the client to the URL provided by /request-upload-url.
    This triggers the backend to update the assessment status and dispatch an AI processing task.
    """
    use_case = ConfirmAudioUploadUseCase(assessment_repo)
    try:
        response_data = await use_case.execute(assessment_id, current_user, request_data)
        return response_data
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e: # Handles 403 (unauthorized), 400 (wrong status) from use case
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        # Log error e
        # import logging
        # logging.exception("Error confirming audio upload:")
        print(f"Unexpected error confirming upload: {e}") # Basic print for now
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while confirming upload.")


@router.post("/{assessment_id}/quiz-answers", response_model=QuizSubmissionResponseDTO)
async def submit_quiz_answers_for_assessment(
    submission_data: QuizSubmissionRequestDTO,
    assessment_id: UUID = Path(..., description="The ID of the assessment for which answers are being submitted."),
    current_user: DomainUser = Depends(get_current_user),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo),
    student_answer_repo: StudentQuizAnswerRepository = Depends(get_student_answer_repo),
    assessment_result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo)
):
    """
    Allows a student to submit their answers to the quiz associated with an assessment.
    Calculates and stores the comprehension score.
    """
    use_case = SubmitQuizAnswersUseCase(
        assessment_repo, quiz_question_repo, student_answer_repo, assessment_result_repo
    )
    try:
        response_data = await use_case.execute(assessment_id, current_user, submission_data)
        return response_data
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e: # Handles 403 (unauthorized), 400 (wrong status/data) from use case
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        # Log error e
        # import logging
        # logging.exception("Error submitting quiz answers:")
        print(f"Unexpected error submitting quiz answers: {e}") # Basic print for now
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while submitting quiz answers.")


@router.get("/{assessment_id}/results", response_model=AssessmentResultDetailDTO)
async def get_assessment_results(
    assessment_id: UUID = Path(..., description="The ID of the assessment for which to retrieve results."),
    current_user: DomainUser = Depends(get_current_user),
    assessment_repo: AssessmentRepository = Depends(get_assessment_repo),
    assessment_result_repo: AssessmentResultRepository = Depends(get_assessment_result_repo),
    student_answer_repo: StudentQuizAnswerRepository = Depends(get_student_answer_repo),
    quiz_question_repo: QuizQuestionRepository = Depends(get_quiz_question_repo),
    reading_repo: ReadingRepository = Depends(get_reading_repo) # Added for use case
):
    """
    Retrieves the detailed results of a specific assessment for the authenticated student.
    This includes AI analysis data, comprehension score, and a review of submitted quiz answers.
    """
    use_case = GetAssessmentResultDetailsUseCase(
        assessment_repo, assessment_result_repo, student_answer_repo, quiz_question_repo, reading_repo
    )
    try:
        result_details = await use_case.execute(assessment_id, current_user)
        return result_details
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ApplicationException as e: # Handles 403 (unauthorized), 400 (wrong status) from use case
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        # Log error e
        # import logging
        # logging.exception("Error retrieving assessment results:")
        print(f"Unexpected error retrieving assessment results: {e}") # Basic print for now
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while retrieving assessment results.")
