"""
Use cases related to Assessment operations.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Optional, Tuple # Added Tuple for ListAssessmentsByReadingIdUseCase

# Domain Entities and Repositories
from readmaster_ai.domain.entities.assessment import Assessment as DomainAssessment
# AssessmentStatus is imported by AssessmentListItemDTO, but if used directly:
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus, UserRole, NotificationType as NotificationTypeEnum
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository
from readmaster_ai.domain.repositories.class_repository import ClassRepository # For AssignReadingUseCase
from readmaster_ai.domain.repositories.user_repository import UserRepository # For AssignReadingUseCase
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository # For SubmitQuizAnswersUseCase
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository # For SubmitQuizAnswersUseCase
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository # For SubmitQuizAnswersUseCase & GetDetails
from readmaster_ai.domain.entities.student_quiz_answer import StudentQuizAnswer as DomainStudentQuizAnswer # For SubmitQuizAnswersUseCase
from readmaster_ai.domain.entities.assessment_result import AssessmentResult as DomainAssessmentResult # For SubmitQuizAnswersUseCase & GetDetails

# Application DTOs
from readmaster_ai.application.dto.assessment_dtos import (
    StartAssessmentRequestDTO,
    RequestUploadURLResponseDTO,
    ConfirmUploadRequestDTO,
    ConfirmUploadResponseDTO,
    QuizSubmissionRequestDTO,
    QuizSubmissionResponseDTO,
    QuizAnswerDTO,
    AssessmentResultDetailDTO,
    SubmittedAnswerDetailDTO,
    AssignReadingRequestDTO, # For AssignReadingUseCase
    CreatedAssignmentInfoDTO, # For AssignReadingUseCase
    AssignmentResponseDTO # For AssignReadingUseCase
)
# DTOs for ListAssessmentsByReadingIdUseCase
from readmaster_ai.application.dto.assessment_list_dto import (
    PaginatedAssessmentListResponseDTO,
    AssessmentListItemDTO,
    AssessmentStudentInfoDTO,
    AssessmentReadingInfoDTO
)
from readmaster_ai.application.interfaces.file_storage_interface import FileStorageInterface # For RequestUploadURL
from readmaster_ai.infrastructure.ai.tasks import process_assessment_audio_task # For ConfirmUpload

# Shared Exceptions
from readmaster_ai.shared.exceptions import NotFoundException, ApplicationException, ForbiddenException

# For AssignReadingUseCase notifications
from readmaster_ai.domain.repositories.notification_repository import NotificationRepository
from readmaster_ai.domain.entities.notification import Notification as DomainNotification
from readmaster_ai.domain.services.notification_service import NotificationService, WebSocketNotificationObserver
from readmaster_ai.presentation.websockets.connection_manager import manager as global_connection_manager


class StartAssessmentUseCase:
    def __init__(self, assessment_repo: AssessmentRepository, reading_repo: ReadingRepository):
        self.assessment_repo = assessment_repo
        self.reading_repo = reading_repo
    async def execute(self, request_data: StartAssessmentRequestDTO, student: DomainUser) -> DomainAssessment:
        reading = await self.reading_repo.get_by_id(request_data.reading_id)
        if not reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(request_data.reading_id))
        new_assessment = DomainAssessment(
            assessment_id=uuid4(), student_id=student.user_id, reading_id=request_data.reading_id,
            status=AssessmentStatus.PENDING_AUDIO, assessment_date=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        return await self.assessment_repo.create(new_assessment)

class RequestAssessmentAudioUploadURLUseCase:
    def __init__(self, assessment_repo: AssessmentRepository, file_storage_service: FileStorageInterface):
        self.assessment_repo = assessment_repo
        self.file_storage_service = file_storage_service
    async def execute(self, assessment_id: UUID, student: DomainUser, content_type: str = "audio/wav") -> RequestUploadURLResponseDTO:
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment: raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))
        if assessment.student_id != student.user_id: raise ApplicationException("User not authorized.", status_code=403)
        if assessment.status != AssessmentStatus.PENDING_AUDIO:
            raise ApplicationException(f"Status is '{assessment.status.value}', expected PENDING_AUDIO.", status_code=400)
        file_extension = "wav"
        if content_type == "audio/mpeg": file_extension = "mp3"
        elif content_type == "audio/ogg": file_extension = "ogg"
        elif content_type == "audio/mp4": file_extension = "m4a"
        blob_name = f"assessments_audio/{assessment.assessment_id}.{file_extension}"
        upload_url, required_fields = await self.file_storage_service.get_presigned_upload_url(blob_name, content_type)
        return RequestUploadURLResponseDTO(upload_url=upload_url, blob_name=blob_name, required_fields=required_fields)

class ConfirmAudioUploadUseCase:
    def __init__(self, assessment_repo: AssessmentRepository):
        self.assessment_repo = assessment_repo
    async def execute(self, assessment_id: UUID, student: DomainUser, request_data: ConfirmUploadRequestDTO) -> ConfirmUploadResponseDTO:
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment: raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))
        if assessment.student_id != student.user_id: raise ApplicationException("User not authorized.", status_code=403)
        if assessment.status != AssessmentStatus.PENDING_AUDIO:
            raise ApplicationException(f"Status is '{assessment.status.value}', expected PENDING_AUDIO.", status_code=400)
        assessment.audio_file_url = request_data.blob_name
        assessment.status = AssessmentStatus.PROCESSING
        assessment.updated_at = datetime.now(timezone.utc)
        updated_assessment = await self.assessment_repo.update(assessment)
        if not updated_assessment: raise ApplicationException("Failed to update assessment status.", status_code=500)
        try:
            process_assessment_audio_task.delay(str(updated_assessment.assessment_id))
        except Exception as e:
            print(f"Critical: Failed to dispatch Celery task for assessment {updated_assessment.assessment_id}: {e}")
            # Potentially revert status or raise specific error
        return ConfirmUploadResponseDTO(assessment_id=updated_assessment.assessment_id, status=updated_assessment.status,
                                      message="Audio upload confirmed. Processing has been initiated.")

class SubmitQuizAnswersUseCase:
    def __init__(self, assessment_repo: AssessmentRepository, quiz_question_repo: QuizQuestionRepository,
                 student_answer_repo: StudentQuizAnswerRepository, assessment_result_repo: AssessmentResultRepository):
        self.assessment_repo = assessment_repo
        self.quiz_question_repo = quiz_question_repo
        self.student_answer_repo = student_answer_repo
        self.assessment_result_repo = assessment_result_repo
    async def execute(self, assessment_id: UUID, student: DomainUser, submission_data: QuizSubmissionRequestDTO) -> QuizSubmissionResponseDTO:
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment: raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))
        if assessment.student_id != student.user_id: raise ApplicationException("User not authorized.", status_code=403)
        if assessment.status != AssessmentStatus.COMPLETED:
             raise ApplicationException(f"Status is '{assessment.status.value}'. Quiz can only be submitted for COMPLETED assessments.", status_code=400)
        student_answers_to_create: List[DomainStudentQuizAnswer] = []
        correct_count = 0
        total_questions_answered = len(submission_data.answers) if submission_data.answers else 0
        if total_questions_answered > 0:
            reading_quiz_questions = await self.quiz_question_repo.list_by_reading_id(assessment.reading_id)
            questions_map = {q.question_id: q for q in reading_quiz_questions}
            for answer_dto in submission_data.answers:
                question = questions_map.get(answer_dto.question_id)
                if not question: raise ApplicationException(f"Question ID {answer_dto.question_id} not found.", status_code=400)
                is_correct = question.validate_answer(answer_dto.selected_option_id)
                if is_correct: correct_count += 1
                student_answers_to_create.append(DomainStudentQuizAnswer(
                    answer_id=uuid4(), assessment_id=assessment_id, question_id=answer_dto.question_id,
                    student_id=student.user_id, selected_option_id=answer_dto.selected_option_id,
                    is_correct=is_correct, answered_at=datetime.now(timezone.utc)
                ))
        if student_answers_to_create: await self.student_answer_repo.bulk_create(student_answers_to_create)
        comprehension_score = (correct_count / total_questions_answered) * 100.0 if total_questions_answered > 0 else 0.0
        assessment_result = await self.assessment_result_repo.get_by_assessment_id(assessment_id)
        if not assessment_result:
            assessment_result = DomainAssessmentResult(result_id=uuid4(), assessment_id=assessment_id,
                                                     analysis_data=assessment.ai_raw_speech_to_text if assessment.ai_raw_speech_to_text else {},
                                                     comprehension_score=round(comprehension_score, 2))
        else:
            assessment_result.comprehension_score = round(comprehension_score, 2)
        await self.assessment_result_repo.create_or_update(assessment_result)
        return QuizSubmissionResponseDTO(assessment_id=assessment_id, comprehension_score=round(comprehension_score, 2),
                                       total_questions=total_questions_answered, correct_answers=correct_count)

class GetAssessmentResultDetailsUseCase:
    def __init__(self, assessment_repo: AssessmentRepository, assessment_result_repo: AssessmentResultRepository,
                 student_answer_repo: StudentQuizAnswerRepository, quiz_question_repo: QuizQuestionRepository,
                 reading_repo: ReadingRepository):
        self.assessment_repo = assessment_repo; self.assessment_result_repo = assessment_result_repo
        self.student_answer_repo = student_answer_repo; self.quiz_question_repo = quiz_question_repo
        self.reading_repo = reading_repo
    async def execute(self, assessment_id: UUID, student: DomainUser) -> AssessmentResultDetailDTO:
        assessment = await self.assessment_repo.get_by_id(assessment_id)
        if not assessment: raise NotFoundException(resource_name="Assessment", resource_id=str(assessment_id))
        if assessment.student_id != student.user_id: raise ApplicationException("User not authorized.", status_code=403)
        if assessment.status not in [AssessmentStatus.COMPLETED, AssessmentStatus.ERROR]:
             raise ApplicationException(f"Results not ready. Status: {assessment.status.value}", status_code=400)
        assessment_result_domain = await self.assessment_result_repo.get_by_assessment_id(assessment_id)
        student_answers_domain = await self.student_answer_repo.list_by_assessment_id(assessment_id)
        reading_domain = await self.reading_repo.get_by_id(assessment.reading_id)
        if not reading_domain: raise NotFoundException("Reading for assessment", str(assessment.reading_id))
        quiz_questions_domain = await self.quiz_question_repo.list_by_reading_id(assessment.reading_id)
        quiz_questions_map = {q.question_id: q for q in quiz_questions_domain}
        submitted_answers_details: List[SubmittedAnswerDetailDTO] = []
        if student_answers_domain:
            for ans_domain in student_answers_domain:
                question_domain = quiz_questions_map.get(ans_domain.question_id)
                if question_domain:
                    submitted_answers_details.append(SubmittedAnswerDetailDTO(
                        question_id=ans_domain.question_id, question_text=question_domain.question_text,
                        selected_option_id=ans_domain.selected_option_id,
                        is_correct=ans_domain.is_correct if ans_domain.is_correct is not None else False,
                        correct_option_id=question_domain.correct_option_id,
                        options=question_domain.options if question_domain.options else {}
                    ))
        return AssessmentResultDetailDTO(
            assessment_id=assessment.assessment_id, student_id=assessment.student_id, reading_id=assessment.reading_id,
            status=assessment.status, assessment_date=assessment.assessment_date, updated_at=assessment.updated_at,
            audio_file_url=assessment.audio_file_url, audio_duration=assessment.audio_duration,
            ai_raw_speech_to_text=assessment.ai_raw_speech_to_text, assigned_by_teacher_id=assessment.assigned_by_teacher_id,
            reading_title=reading_domain.title,
            analysis_data=assessment_result_domain.analysis_data if assessment_result_domain else None,
            comprehension_score=assessment_result_domain.comprehension_score if assessment_result_domain else None,
            submitted_answers=submitted_answers_details
        )

class AssignReadingUseCase:
    def __init__(self, assessment_repo: AssessmentRepository, reading_repo: ReadingRepository,
                 class_repo: ClassRepository, user_repo: UserRepository,
                 notification_repo: NotificationRepository):
        self.assessment_repo = assessment_repo; self.reading_repo = reading_repo
        self.class_repo = class_repo; self.user_repo = user_repo
        self.notification_repo = notification_repo
        self.notification_service = NotificationService()
        try:
            ws_observer = WebSocketNotificationObserver(global_connection_manager)
            self.notification_service.subscribe(ws_observer)
        except Exception as e: print(f"Warning: Failed to init WebSocketObserver in AssignReadingUseCase: {e}")
    async def execute(self, request_data: AssignReadingRequestDTO, teacher: DomainUser) -> AssignmentResponseDTO:
        if teacher.role != UserRole.TEACHER and teacher.role != UserRole.ADMIN:
            raise ForbiddenException("Only teachers or admins can assign readings.")
        reading = await self.reading_repo.get_by_id(request_data.reading_id)
        if not reading: raise NotFoundException("Reading", str(request_data.reading_id))
        target_student_ids: set[UUID] = set(request_data.student_ids or [])
        if request_data.class_id:
            class_obj = await self.class_repo.get_by_id(request_data.class_id)
            if not class_obj: raise NotFoundException("Class", str(request_data.class_id))
            if class_obj.created_by_teacher_id != teacher.user_id and teacher.role != UserRole.ADMIN:
                raise ForbiddenException(f"Not authorized for class ID {request_data.class_id}.")
            students_in_class = await self.class_repo.get_students_in_class(request_data.class_id)
            for student_in_class in students_in_class:
                if student_in_class: target_student_ids.add(student_in_class.user_id)
        if not target_student_ids: raise ApplicationException("No students for assignment.", status_code=400)
        created_assessments_info: List[CreatedAssignmentInfoDTO] = []
        skipped_students_info: List[UUID] = []
        current_time = datetime.now(timezone.utc)
        for student_id in list(target_student_ids):
            student_user = await self.user_repo.get_by_id(student_id)
            if not student_user or student_user.role != UserRole.STUDENT:
                skipped_students_info.append(student_id); continue
            new_assessment = DomainAssessment(
                assessment_id=uuid4(), student_id=student_id, reading_id=request_data.reading_id,
                assigned_by_teacher_id=teacher.user_id, status=AssessmentStatus.PENDING_AUDIO,
                assessment_date=current_time, updated_at=current_time
            )
            try:
                created_assessment = await self.assessment_repo.create(new_assessment)
                created_assessments_info.append(CreatedAssignmentInfoDTO(
                    assessment_id=created_assessment.assessment_id, student_id=created_assessment.student_id,
                    reading_id=created_assessment.reading_id, status=created_assessment.status
                ))
                notification_message = f"You have a new reading assignment: '{reading.title}'."
                new_db_notification = DomainNotification(
                    notification_id=uuid4(), user_id=student_id, type=NotificationTypeEnum.ASSIGNMENT,
                    message=notification_message, related_entity_id=created_assessment.assessment_id
                )
                await self.notification_repo.create(new_db_notification)
                notification_payload_for_ws = {
                    "notificationId": str(new_db_notification.notification_id), "message": new_db_notification.message,
                    "relatedEntityId": str(new_db_notification.related_entity_id), "type": new_db_notification.type.value,
                    "isRead": new_db_notification.is_read, "createdAt": new_db_notification.created_at.isoformat()
                }
                await self.notification_service.notify(student_id, NotificationTypeEnum.ASSIGNMENT.value, notification_payload_for_ws)
            except Exception as e:
                print(f"Failed to create assessment or notify for student {student_id}: {e}")
                skipped_students_info.append(student_id)
        return AssignmentResponseDTO(
            created_assessments=created_assessments_info, skipped_students=skipped_students_info,
            message=f"Reading assigned. {len(created_assessments_info)} created. {len(skipped_students_info)} skipped."
        )

class ListAssessmentsByReadingIdUseCase:
    def __init__(self,
                 assessment_repo: AssessmentRepository,
                 reading_repo: ReadingRepository,
                 user_repo: UserRepository):
        self.assessment_repo = assessment_repo
        self.reading_repo = reading_repo
        self.user_repo = user_repo

    async def execute(self, reading_id: UUID, current_user: DomainUser, page: int, size: int) -> PaginatedAssessmentListResponseDTO:
        # Step 1: Validate Reading Material
        reading = await self.reading_repo.get_by_id(reading_id)
        if not reading:
            raise NotFoundException(f"Reading material with ID {reading_id} not found.")

        # Step 2: Fetch Assessments from Repository
        assessments_tuple: Tuple[List[DomainAssessment], int] = await self.assessment_repo.list_by_reading_id(
            reading_id=reading_id,
            user_id=current_user.user_id,
            role=current_user.role,
            page=page,
            size=size
        )
        domain_assessments, total_count = assessments_tuple

        # Step 3: Map to DTOs
        list_item_dtos: List[AssessmentListItemDTO] = []
        for assessment in domain_assessments:
            student_entity = await self.user_repo.get_by_id(assessment.student_id)
            student_info = AssessmentStudentInfoDTO(
                student_id=assessment.student_id,
                first_name=student_entity.first_name if student_entity else None,
                last_name=student_entity.last_name if student_entity else None,
                grade=None # Placeholder: Grade determination needs more context/queries
            )

            # Reading info comes from the already fetched 'reading' object
            reading_info = AssessmentReadingInfoDTO(
                reading_id=reading.reading_id,
                title=reading.title
            )

            user_relationship_context = None
            if current_user.role == UserRole.TEACHER:
                # Placeholder: Specific class name requires more complex logic or repo changes
                user_relationship_context = "Student in one of your classes"
            elif current_user.role == UserRole.PARENT:
                user_relationship_context = "Your Child"

            list_item_dtos.append(
                AssessmentListItemDTO(
                    assessment_id=assessment.assessment_id,
                    status=assessment.status, # This should be AssessmentStatus enum
                    assessment_date=assessment.assessment_date,
                    updated_at=assessment.updated_at,
                    student=student_info,
                    reading=reading_info,
                    user_relationship_context=user_relationship_context
                )
            )

        return PaginatedAssessmentListResponseDTO(
            items=list_item_dtos,
            page=page,
            size=size,
            total_count=total_count
        )
