"""
Use cases related to Assessment operations.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone

# Domain Entities and Repositories
from readmaster_ai.domain.entities.assessment import Assessment as DomainAssessment
# AssessmentStatus enum is part of DomainAssessment entity file, or use centralized one
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus as AssessmentStatusEnum
from readmaster_ai.domain.entities.user import DomainUser # For student context
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository # To validate reading existence

# Application DTOs
from readmaster_ai.application.dto.assessment_dtos import StartAssessmentRequestDTO

# Shared Exceptions
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException


class StartAssessmentUseCase:
    """
    Use case for a student to start a new assessment for a given reading.
    """
    def __init__(self, assessment_repo: AssessmentRepository, reading_repo: ReadingRepository):
        self.assessment_repo = assessment_repo
        self.reading_repo = reading_repo

    async def execute(self, request_data: StartAssessmentRequestDTO, student: DomainUser) -> DomainAssessment:
        """
        Executes the process of starting a new assessment.

        Args:
            request_data: DTO containing the reading_id for the assessment.
            student: The authenticated student (DomainUser) initiating the assessment.

        Returns:
            The created DomainAssessment entity.

        Raises:
            NotFoundException: If the specified reading material does not exist.
            ApplicationException: For other business rule violations (e.g., duplicate active assessment).
        """
        # 1. Validate that the reading material exists
        reading = await self.reading_repo.get_by_id(request_data.reading_id)
        if not reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(request_data.reading_id))

        # 2. Optional: Implement business logic for concurrent assessments
        #    (e.g., a student cannot have multiple PENDING_AUDIO assessments for the same reading).
        #    This would involve querying existing assessments for the student and reading.
        #    Example:
        #    existing_assessments = await self.assessment_repo.find_active_by_student_and_reading(
        #        student_id=student.user_id, reading_id=request_data.reading_id
        #    )
        #    if existing_assessments:
        #        raise ApplicationException("An active assessment for this reading already exists.", status_code=409)

        # 3. Create a new Assessment domain entity
        new_assessment = DomainAssessment(
            assessment_id=uuid4(), # Application layer generates the ID
            student_id=student.user_id,
            reading_id=request_data.reading_id,
            status=AssessmentStatusEnum.PENDING_AUDIO, # Initial status
            assessment_date=datetime.now(timezone.utc), # Set current time as assessment date
            updated_at=datetime.now(timezone.utc)
            # Other fields like audio_file_url, audio_duration, ai_raw_speech_to_text
            # will be updated in subsequent steps of the assessment process.
            # assigned_by_teacher_id is None here as student initiates.
        )

        # 4. Persist the new assessment using the repository
        created_assessment = await self.assessment_repo.create(new_assessment)

        return created_assessment

# Future assessment-related use cases:
# class UploadAssessmentAudioUseCase: ...
# class SubmitAssessmentForProcessingUseCase: ... (Could be combined with UploadAudio)
from readmaster_ai.application.interfaces.file_storage_interface import FileStorageInterface
from readmaster_ai.application.dto.assessment_dtos import RequestUploadURLResponseDTO


class RequestAssessmentAudioUploadURLUseCase:
    """
    Use case for requesting a presigned URL to upload an assessment audio file.
    """
    def __init__(self, assessment_repo: AssessmentRepository, file_storage_service: FileStorageInterface):
        self.assessment_repo = assessment_repo
        self.file_storage_service = file_storage_service

    async def execute(self, assessment_id: UUID, student: DomainUser, content_type: str = "audio/wav") -> RequestUploadURLResponseDTO:
        """
        Executes the process of generating a presigned URL for audio upload.

        Args:
            assessment_id: The ID of the assessment for which to upload audio.
            student: The authenticated student (DomainUser) making the request.
            content_type: The MIME type of the audio file to be uploaded.

        Returns:
            A DTO containing the presigned URL, blob name, and any required fields/headers.

        Raises:
            NotFoundException: If the assessment is not found.
            ApplicationException: If the user is not authorized, or if the assessment
                                 is not in the correct status for upload.
        """
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))

        # Authorization: Ensure the assessment belongs to the requesting student
        if assessment.student_id != student.user_id:
            raise ApplicationException("User not authorized for this assessment.", status_code=403)

        # Status Check: Ensure assessment is in a state that allows audio upload
        if assessment.status != AssessmentStatusEnum.PENDING_AUDIO:
            raise ApplicationException(
                f"Assessment status is '{assessment.status.value}', "
                f"but expected '{AssessmentStatusEnum.PENDING_AUDIO.value}'. Cannot request upload URL.",
                status_code=400
            )

        # Define a unique blob name for the audio file.
        # Example: "assessments_audio/<assessment_id>.<extension>"
        # The file extension should ideally be derived reliably from content_type.
        file_extension = "wav" # Default extension
        if content_type == "audio/mpeg":
            file_extension = "mp3"
        elif content_type == "audio/ogg":
            file_extension = "ogg"
        elif content_type == "audio/mp4": # m4a
            file_extension = "m4a"
        # Add more mappings as needed, or use a library for MIME type to extension.

        blob_name = f"assessments_audio/{assessment.assessment_id}.{file_extension}"

        # Get the presigned URL from the file storage service.
        # Expiration time for the URL can be configured globally or passed per request.
        upload_url, required_fields = await self.file_storage_service.get_presigned_upload_url(
            blob_name=blob_name,
            content_type=content_type
            # expiration_seconds= can be set here if needed
        )

        # Note: The assessment status is not changed here. It will be updated
        # after the client confirms successful upload and the backend verifies it.

        return RequestUploadURLResponseDTO(
            upload_url=upload_url,
            blob_name=blob_name,
            required_fields=required_fields
        )

# Future assessment-related use cases:
# class ConfirmAudioUploadUseCase: ... (To update assessment status after upload)
from readmaster_ai.application.dto.assessment_dtos import ConfirmUploadRequestDTO, ConfirmUploadResponseDTO
from readmaster_ai.infrastructure.ai.tasks import process_assessment_audio_task # Import Celery task
# Assuming LOCAL_STORAGE_BASE_URL might be part of a broader config or directly from file_storage module for construction
# For now, let's assume the blob_name is self-sufficient or the URL construction logic is encapsulated.
# from readmaster_ai.infrastructure.file_storage.local_storage import LOCAL_STORAGE_BASE_URL


class ConfirmAudioUploadUseCase:
    """
    Use case for confirming that assessment audio has been uploaded
    and for initiating the asynchronous AI processing task.
    """
    def __init__(self, assessment_repo: AssessmentRepository):
        # If FileStorageInterface is needed to verify file existence before confirming, add it here.
        # For this example, we assume client confirmation is trusted to trigger processing.
        self.assessment_repo = assessment_repo

    async def execute(self, assessment_id: UUID, student: DomainUser, request_data: ConfirmUploadRequestDTO) -> ConfirmUploadResponseDTO:
        """
        Executes the audio upload confirmation and processing initiation.

        Args:
            assessment_id: The ID of the assessment.
            student: The authenticated student (DomainUser).
            request_data: DTO containing the blob_name of the uploaded file.

        Returns:
            A DTO confirming the action and the new assessment status.

        Raises:
            NotFoundException: If the assessment is not found.
            ApplicationException: If user is not authorized or assessment is in wrong status.
        """
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))

        if assessment.student_id != student.user_id:
            raise ApplicationException("User not authorized for this assessment.", status_code=403)

        if assessment.status != AssessmentStatusEnum.PENDING_AUDIO:
            # This could be an idempotent call: if already PROCESSING or COMPLETED, just return current state.
            # For now, strict check.
            raise ApplicationException(
                f"Assessment status is '{assessment.status.value}'. "
                f"Cannot confirm upload unless status is '{AssessmentStatusEnum.PENDING_AUDIO.value}'.",
                status_code=400
            )

        # Construct the full audio_file_url. This strategy depends on how blob_names and storage are structured.
        # If blob_name from client is a full path like "assessments_audio/uuid.wav",
        # and your file storage service can derive a serving URL from it, or if you store URLs directly.
        # For the local mock, we might construct a URL based on LOCAL_STORAGE_BASE_URL.
        # This logic might be better placed if the FileStorageService provides a get_public_url(blob_name) method.
        # For now, directly using blob_name assuming it's a usable identifier or relative path.
        assessment.audio_file_url = request_data.blob_name
        assessment.status = AssessmentStatusEnum.PROCESSING # Update status to PROCESSING
        assessment.updated_at = datetime.now(timezone.utc)

        updated_assessment = await self.assessment_repo.update(assessment)
        if not updated_assessment:
            # This should ideally not happen if the get_by_id succeeded and ID is valid.
            raise ApplicationException("Failed to update assessment status after confirming upload.", status_code=500)

        # Dispatch the Celery task for AI processing.
        # Pass assessment_id as a string, as Celery tasks prefer primitive types for arguments.
        try:
            process_assessment_audio_task.delay(str(updated_assessment.assessment_id))
            print(f"Celery task 'process_assessment_audio_task' dispatched for assessment ID: {updated_assessment.assessment_id}")
        except Exception as e:
            # Handle Celery dispatch errors (e.g., broker not available)
            # Log the error. Depending on policy, might revert assessment status or notify admin.
            # For now, we'll assume dispatch is usually reliable if broker is up.
            # If critical, might need a fallback or marking assessment as 'PENDING_PROCESSING_DISPATCH_FAILED'.
            print(f"Critical: Failed to dispatch Celery task for assessment {updated_assessment.assessment_id}: {e}")
            # Optionally, revert status or raise specific error
            # For this example, we proceed, but the task won't run.
            # Consider how to handle this failure robustly in production.
            # assessment.status = AssessmentStatusEnum.PENDING_AUDIO # Example revert
            # await self.assessment_repo.update(assessment)
            # raise ApplicationException("Failed to initiate audio processing. Please try again later or contact support.", status_code=503) # Service Unavailable

        return ConfirmUploadResponseDTO(
            assessment_id=updated_assessment.assessment_id,
            status=updated_assessment.status, # Should be PROCESSING
            message="Audio upload confirmed. Processing has been initiated."
        )

# Future assessment-related use cases:
from readmaster_ai.application.dto.assessment_dtos import (
    QuizSubmissionRequestDTO, QuizSubmissionResponseDTO, QuizAnswerDTO # Added
)
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.domain.entities.student_quiz_answer import StudentQuizAnswer as DomainStudentQuizAnswer
from readmaster_ai.domain.entities.assessment_result import AssessmentResult as DomainAssessmentResult # For creating if not exists


class SubmitQuizAnswersUseCase:
    """
    Use case for a student submitting their answers to a quiz for an assessment.
    Calculates comprehension score and updates the assessment result.
    """
    def __init__(self,
                 assessment_repo: AssessmentRepository,
                 quiz_question_repo: QuizQuestionRepository,
                 student_answer_repo: StudentQuizAnswerRepository,
                 assessment_result_repo: AssessmentResultRepository):
        self.assessment_repo = assessment_repo
        self.quiz_question_repo = quiz_question_repo
        self.student_answer_repo = student_answer_repo
        self.assessment_result_repo = assessment_result_repo

    async def execute(self, assessment_id: UUID, student: DomainUser, submission_data: QuizSubmissionRequestDTO) -> QuizSubmissionResponseDTO:
        """
        Executes the quiz answer submission process.

        Args:
            assessment_id: The ID of the assessment.
            student: The authenticated student (DomainUser).
            submission_data: DTO containing the list of submitted answers.

        Returns:
            A DTO confirming submission and providing the comprehension score.

        Raises:
            NotFoundException: If assessment or related questions are not found.
            ApplicationException: For authorization issues or if assessment is not in correct status.
        """
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))

        if assessment.student_id != student.user_id:
            raise ApplicationException("User not authorized for this assessment.", status_code=403)

        # Validate assessment status. Assuming quiz can only be submitted after AI processing is COMPLETED.
        # This might change if quiz is independent of AI fluency analysis.
        if assessment.status != AssessmentStatusEnum.COMPLETED:
             raise ApplicationException(
                 f"Assessment status is '{assessment.status.value}'. Quiz can only be submitted for COMPLETED assessments.",
                 status_code=400
            )

        student_answers_to_create: List[DomainStudentQuizAnswer] = []
        correct_count = 0

        if not submission_data.answers: # Handle empty submission
            total_questions_answered = 0
            # Potentially raise error if answers are expected:
            # raise ApplicationException("No answers provided in the submission.", status_code=400)
        else:
            total_questions_answered = len(submission_data.answers)

            # Fetch all relevant quiz questions for the reading associated with the assessment
            reading_quiz_questions = await self.quiz_question_repo.list_by_reading_id(assessment.reading_id)
            questions_map = {q.question_id: q for q in reading_quiz_questions}

            for answer_dto in submission_data.answers:
                question = questions_map.get(answer_dto.question_id)
                if not question:
                    # Option: collect all errors and return, or raise immediately.
                    # For now, raising immediately.
                    raise ApplicationException(
                        f"Question ID {answer_dto.question_id} not found for reading ID {assessment.reading_id}.",
                        status_code=400 # Bad request as submitted data is inconsistent
                    )

                is_correct = question.validate_answer(answer_dto.selected_option_id)
                if is_correct:
                    correct_count += 1

                domain_answer = DomainStudentQuizAnswer(
                    answer_id=uuid4(), # Application generates ID
                    assessment_id=assessment_id,
                    question_id=answer_dto.question_id,
                    student_id=student.user_id,
                    selected_option_id=answer_dto.selected_option_id,
                    is_correct=is_correct,
                    answered_at=datetime.now(timezone.utc)
                )
                student_answers_to_create.append(domain_answer)

        if student_answers_to_create:
            await self.student_answer_repo.bulk_create(student_answers_to_create)

        comprehension_score = (correct_count / total_questions_answered) * 100.0 if total_questions_answered > 0 else 0.0

        # Create or Update AssessmentResult with the comprehension score
        assessment_result = await self.assessment_result_repo.get_by_assessment_id(assessment_id)
        if not assessment_result:
            # This implies AI processing (which should create AssessmentResult) hasn't run or failed to create it.
            # For robustness, create one if missing, but log this as a potential issue.
            print(f"Warning: AssessmentResult not found for assessment_id {assessment_id}, creating a new one.")
            assessment_result = DomainAssessmentResult(
                result_id=uuid4(),
                assessment_id=assessment_id,
                analysis_data=assessment.ai_raw_speech_to_text if assessment.ai_raw_speech_to_text else {}, # Carry over AI data if available
                comprehension_score=round(comprehension_score, 2)
            )
        else:
            assessment_result.comprehension_score = round(comprehension_score, 2)

        await self.assessment_result_repo.create_or_update(assessment_result)

        # Optionally, if there's a further status like 'FULLY_COMPLETED' or 'RESULTS_AVAILABLE'
        # assessment.status = AssessmentStatusEnum.RESULTS_AVAILABLE
        # assessment.updated_at = datetime.now(timezone.utc)
        # await self.assessment_repo.update(assessment)

        return QuizSubmissionResponseDTO(
            assessment_id=assessment_id,
            comprehension_score=round(comprehension_score, 2),
            total_questions=total_questions_answered,
            correct_answers=correct_count
        )

# Future assessment-related use cases:
from readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO, SubmittedAnswerDetailDTO # Add these
# Repositories needed: Assessment, AssessmentResult, StudentQuizAnswer, QuizQuestion, Reading
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository # Added

class GetAssessmentResultDetailsUseCase:
    """
    Use case for retrieving detailed results of a specific assessment for a student.
    Combines data from Assessment, AssessmentResult, StudentQuizAnswers, QuizQuestions, and Reading.
    """
    def __init__(self,
                 assessment_repo: AssessmentRepository,
                 assessment_result_repo: AssessmentResultRepository,
                 student_answer_repo: StudentQuizAnswerRepository,
                 quiz_question_repo: QuizQuestionRepository,
                 reading_repo: ReadingRepository):
        self.assessment_repo = assessment_repo
        self.assessment_result_repo = assessment_result_repo
        self.student_answer_repo = student_answer_repo
        self.quiz_question_repo = quiz_question_repo
        self.reading_repo = reading_repo

    async def execute(self, assessment_id: UUID, student: DomainUser) -> AssessmentResultDetailDTO:
        """
        Executes the process of fetching and assembling detailed assessment results.

        Args:
            assessment_id: The ID of the assessment to retrieve results for.
            student: The authenticated student (DomainUser) requesting the results.

        Returns:
            An AssessmentResultDetailDTO containing comprehensive result information.

        Raises:
            NotFoundException: If the assessment or related critical data is not found.
            ApplicationException: For authorization issues or if results are not ready.
        """
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment:
            raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))

        # Authorization: Ensure the assessment belongs to the requesting student.
        # This could be expanded for parent/teacher roles with appropriate checks.
        if assessment.student_id != student.user_id:
            raise ApplicationException("User not authorized to view this assessment's results.", status_code=403)

        # Status Check: Results should only be available for completed or errored assessments.
        # PENDING_AUDIO or PROCESSING assessments do not have final results.
        if assessment.status not in [AssessmentStatusEnum.COMPLETED, AssessmentStatusEnum.ERROR]:
             raise ApplicationException(
                 f"Assessment results are not yet available. Current status: {assessment.status.value}",
                 status_code=400 # Bad Request, as results are not ready to be fetched.
            )

        # Fetch all related data concurrently where possible (though shown sequentially here for clarity)
        assessment_result_domain = await self.assessment_result_repo.get_by_assessment_id(assessment_id)
        student_answers_domain = await self.student_answer_repo.list_by_assessment_id(assessment_id)
        reading_domain = await self.reading_repo.get_by_id(assessment.reading_id)

        if not reading_domain: # Should ideally not happen if assessment exists with a valid reading_id
            raise NotFoundException(resource_name="Reading associated with assessment", resource_id=str(assessment.reading_id))

        quiz_questions_domain = await self.quiz_question_repo.list_by_reading_id(assessment.reading_id)
        quiz_questions_map = {q.question_id: q for q in quiz_questions_domain}

        # Prepare submitted answer details for the DTO
        submitted_answers_details: List[SubmittedAnswerDetailDTO] = []
        if student_answers_domain: # Ensure there are answers to process
            for ans_domain in student_answers_domain:
                question_domain = quiz_questions_map.get(ans_domain.question_id)
                if question_domain: # Should always find a match if data is consistent
                    submitted_answers_details.append(
                        SubmittedAnswerDetailDTO(
                            question_id=ans_domain.question_id,
                            question_text=question_domain.question_text,
                            selected_option_id=ans_domain.selected_option_id,
                            is_correct=ans_domain.is_correct if ans_domain.is_correct is not None else False,
                            correct_option_id=question_domain.correct_option_id,
                            options=question_domain.options if question_domain.options else {}
                        )
                    )
                else:
                    # Log this inconsistency: an answer exists for a question not in the reading's question set.
                    print(f"Warning: Student answer found for question_id {ans_domain.question_id} which is not in reading {assessment.reading_id}'s questions.")

        # Construct the final AssessmentResultDetailDTO
        # Start with base assessment fields from the fetched Assessment domain object
        result_detail_dto_data = {
            "assessment_id": assessment.assessment_id,
            "student_id": assessment.student_id,
            "reading_id": assessment.reading_id,
            "status": assessment.status,
            "assessment_date": assessment.assessment_date,
            "updated_at": assessment.updated_at,
            "audio_file_url": assessment.audio_file_url,
            "audio_duration": assessment.audio_duration,
            "ai_raw_speech_to_text": assessment.ai_raw_speech_to_text,
            "assigned_by_teacher_id": assessment.assigned_by_teacher_id, # From base DTO
            "reading_title": reading_domain.title, # Added from fetched reading
            "analysis_data": assessment_result_domain.analysis_data if assessment_result_domain else None,
            "comprehension_score": assessment_result_domain.comprehension_score if assessment_result_domain else None,
            "submitted_answers": submitted_answers_details
        }

        return AssessmentResultDetailDTO(**result_detail_dto_data)


# Future assessment-related use cases:
from readmaster_ai.application.dto.assessment_dtos import AssignReadingRequestDTO, CreatedAssignmentInfoDTO, AssignmentResponseDTO # Add these
from readmaster_ai.domain.repositories.class_repository import ClassRepository
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.value_objects.common_enums import UserRole # Import UserRole for teacher check
from readmaster_ai.shared.exceptions import ForbiddenException # Import ForbiddenException
# from uuid import uuid4 # Already imported
# from datetime import datetime, timezone, date as py_date # date is not used here, datetime, timezone are
# from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus as AssessmentStatusEnum # Already imported


class AssignReadingUseCase:
    """
    Use case for a teacher to assign a reading to students, either individually or to an entire class.
    This creates new Assessment records for each targeted student.
    """
    def __init__(self,
                 assessment_repo: AssessmentRepository,
                 reading_repo: ReadingRepository,
                 class_repo: ClassRepository,
                 user_repo: UserRepository):
        self.assessment_repo = assessment_repo
        self.reading_repo = reading_repo
        self.class_repo = class_repo
        self.user_repo = user_repo

    async def execute(self, request_data: AssignReadingRequestDTO, teacher: DomainUser) -> AssignmentResponseDTO:
        """
        Executes the reading assignment process.

        Args:
            request_data: DTO containing reading_id, and either student_ids or class_id.
            teacher: The authenticated teacher (DomainUser) performing the assignment.

        Returns:
            An AssignmentResponseDTO summarizing the created assessments and any skipped students.

        Raises:
            ForbiddenException: If the user is not a teacher.
            NotFoundException: If the reading or class is not found.
            ApplicationException: If no students are targeted or other issues occur.
        """
        if teacher.role != UserRole.TEACHER and teacher.role != UserRole.ADMIN : # Allow Admin too
            raise ForbiddenException("Only teachers or admins can assign readings.")

        # Validate Reading
        reading = await self.reading_repo.get_by_id(request_data.reading_id)
        if not reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(request_data.reading_id))

        # Collect target student IDs
        target_student_ids: set[UUID] = set(request_data.student_ids or [])

        if request_data.class_id:
            class_obj = await self.class_repo.get_by_id(request_data.class_id)
            if not class_obj:
                raise NotFoundException(resource_name="Class", resource_id=str(request_data.class_id))

            # Authorization check: Teacher must own the class or be an Admin
            if class_obj.created_by_teacher_id != teacher.user_id and teacher.role != UserRole.ADMIN:
                raise ForbiddenException(f"Teacher not authorized for class ID {request_data.class_id}.")

            students_in_class = await self.class_repo.get_students_in_class(request_data.class_id)
            for student_in_class in students_in_class:
                if student_in_class: # Ensure student object is not None
                    target_student_ids.add(student_in_class.user_id)

        if not target_student_ids:
            raise ApplicationException("No students specified or found for assignment.", status_code=400)

        # Validate student IDs and filter out non-students or invalid IDs
        created_assessments_info: List[CreatedAssignmentInfoDTO] = []
        skipped_students_info: List[UUID] = []

        current_time = datetime.now(timezone.utc)

        for student_id_to_assign in target_student_ids:
            student_user = await self.user_repo.get_by_id(student_id_to_assign)
            if not student_user or student_user.role != UserRole.STUDENT:
                skipped_students_info.append(student_id_to_assign)
                print(f"Skipping user {student_id_to_assign}: Not a valid student.")
                continue

            # Optional: Check for existing active/pending assessment for this student & reading
            # to avoid duplicate assignments if that's the desired business logic.
            # For now, allow re-assignment (creates a new assessment instance).

            new_assessment = DomainAssessment(
                assessment_id=uuid4(), # Application generates ID
                student_id=student_id_to_assign,
                reading_id=request_data.reading_id,
                assigned_by_teacher_id=teacher.user_id, # Link to the assigning teacher
                status=AssessmentStatusEnum.PENDING_AUDIO, # Initial status
                assessment_date=current_time, # Use consistent time for all assignments in this batch
                updated_at=current_time,
                # due_date=request_data.due_date # If due_date was on DomainAssessment
            )

            try:
                created_assessment = await self.assessment_repo.create(new_assessment)
                created_assessments_info.append(
                    CreatedAssignmentInfoDTO(
                        assessment_id=created_assessment.assessment_id,
                        student_id=created_assessment.student_id,
                        reading_id=created_assessment.reading_id,
                        status=created_assessment.status
                    )
                )
                # TODO: Trigger notification for student (Phase 5 - separate task)
            except Exception as e: # Catch error during individual assessment creation
                print(f"Failed to create assessment for student {student_id_to_assign}: {e}")
                skipped_students_info.append(student_id_to_assign)


        return AssignmentResponseDTO(
            created_assessments=created_assessments_info,
            skipped_students=skipped_students_info,
            message=(
                f"Reading assigned. {len(created_assessments_info)} assessments created. "
                f"{len(skipped_students_info)} students skipped or failed."
            )
        )

# Future assessment-related use cases:
# class GetAssessmentStatusUseCase: ... (Could be simpler than full results)
# class ListStudentAssessmentsUseCase: ... (For students to see their assessment history)
# class TeacherGetStudentAssessmentResultUseCase: ... (For teachers)
