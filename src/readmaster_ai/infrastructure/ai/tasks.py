"""
Celery tasks related to AI processing for Readmaster.ai.
These tasks are designed to be run asynchronously by Celery workers.
"""
import time
import asyncio # For running async database operations from a sync Celery task

from readmaster_ai.core.celery_app import celery_app
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.infrastructure.database.repositories.assessment_repository_impl import AssessmentRepositoryImpl
from readmaster_ai.infrastructure.database.config import AsyncSessionLocal, engine as sqlalchemy_engine # For DB session
from readmaster_ai.domain.entities.assessment import AssessmentStatus # For updating status
from readmaster_ai.application.interfaces.ai_analysis_interface import AIAnalysisInterface
from readmaster_ai.infrastructure.ai.ai_service_factory import AIServiceFactory
from readmaster_ai.domain.entities.assessment_result import AssessmentResult as DomainAssessmentResult
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus, NotificationType as NotificationTypeEnum # Using centralized enums

from readmaster_ai.domain.repositories.notification_repository import NotificationRepository # New
from readmaster_ai.infrastructure.database.repositories.notification_repository_impl import NotificationRepositoryImpl # New
from readmaster_ai.domain.entities.notification import Notification as DomainNotification # New
from readmaster_ai.domain.services.notification_service import NotificationService, WebSocketNotificationObserver # New
from readmaster_ai.presentation.websockets.connection_manager import manager as global_connection_manager # New
# from readmaster_ai.domain.repositories.reading_repository import ReadingRepository # For reading title (optional)
# from readmaster_ai.infrastructure.database.repositories.reading_repository_impl import ReadingRepositoryImpl # For reading title


# Renamed helper to reflect its full scope now
async def _process_assessment_and_update_db_async(assessment_id_str: str):
    """
    Asynchronous helper to perform AI processing and update database records for an assessment.
    This function is called from the synchronous Celery task.
    """
    async with AsyncSessionLocal() as session:
        assessment_repo: AssessmentRepository = AssessmentRepositoryImpl(session)
        result_repo: AssessmentResultRepository = AssessmentResultRepositoryImpl(session)
        notification_repo: NotificationRepository = NotificationRepositoryImpl(session) # New repo
        ai_service: AIAnalysisInterface = AIServiceFactory.create_service()
        # reading_repo: ReadingRepository = ReadingRepositoryImpl(session) # Uncomment if fetching reading title

        # Initialize NotificationService and subscribe WebSocket observer for this task execution
        # This assumes NotificationService can be instantiated per task, or a global one is managed carefully.
        # For tasks running in separate processes, a new instance might be safer if it doesn't rely on shared in-memory state
        # that isn't process-safe. The global_connection_manager for WebSockets is an exception as it's process-global (if Redis based) or needs careful handling.
        # For this example, we instantiate it here.
        notification_service = NotificationService()
        # Ensure global_connection_manager is properly initialized and accessible here.
        # If celery workers are separate processes, global_connection_manager (in-memory version) won't be shared from main app.
        # If global_connection_manager uses Redis/external store, it's fine.
        # Assuming global_connection_manager is process-safe or this task runs where it's accessible.
        try:
            ws_observer = WebSocketNotificationObserver(global_connection_manager)
            notification_service.subscribe(ws_observer)
        except Exception as e:
            print(f"[CeleryTask] Warning: Could not subscribe WebSocketNotificationObserver: {e}")
            # Continue without WebSocket notifications if subscription fails

        assessment_id = UUID(assessment_id_str)
        assessment = await assessment_repo.get_by_id(assessment_id)

        if not assessment:
            print(f"[CeleryTask] Assessment {assessment_id_str} not found. Task cannot proceed.")
            # No further action needed here, as there's no assessment to update.
            # Consider logging this as an error or anomaly.
            return

        if not assessment.audio_file_url:
            print(f"[CeleryTask] Assessment {assessment_id_str} has no audio_file_url. Marking as ERROR.")
            assessment.status = AssessmentStatus.ERROR
            assessment.ai_raw_speech_to_text = "Audio file URL missing." # Add detail to raw text
            assessment.updated_at = datetime.now(timezone.utc)
            await assessment_repo.update(assessment)
            await session.commit()
            return

        # Main processing block
        try:
            print(f"[CeleryTask] Starting AI analysis for assessment {assessment_id_str} with audio: {assessment.audio_file_url}")

            # Determine language for AI service (placeholder, could come from assessment or reading entity)
            # language_for_ai = assessment.reading.language if assessment.reading else 'en'
            language_for_ai = 'en' # Defaulting to 'en' for now

            # Call the AI analysis service
            analysis_output = await ai_service.analyze_audio(assessment.audio_file_url, language_for_ai)

            print(f"[CeleryTask] AI analysis completed for {assessment_id_str}. Output snippet: {str(analysis_output)[:200]}...")

            # Store the raw transcription (or part of it) in the Assessment entity
            assessment.ai_raw_speech_to_text = analysis_output.get("transcription", "N/A")

            # Create or update the AssessmentResult entity
            # Check if a result record already exists for this assessment_id
            existing_result = await result_repo.get_by_assessment_id(assessment_id)

            if existing_result:
                result_entity = existing_result
                result_entity.analysis_data = analysis_output
                # Potentially update comprehension_score if re-calculable here, or leave as is
            else:
                result_entity = DomainAssessmentResult(
                    result_id=uuid4(), # Generate new UUID for the result
                    assessment_id=assessment_id,
                    analysis_data=analysis_output,
                    comprehension_score=None # Placeholder, to be calculated based on quiz answers later
                                             # or derived from analysis_output if applicable.
                )

            await result_repo.create_or_update(result_entity) # Upsert the result

            # Update the Assessment status to COMPLETED
            assessment.status = AssessmentStatus.COMPLETED
            assessment.updated_at = datetime.now(timezone.utc)
            await assessment_repo.update(assessment)

            # Create and dispatch notification
            if assessment.status == AssessmentStatus.COMPLETED:
                # reading = await reading_repo.get_by_id(assessment.reading_id) # Optional: for more detail in message
                # reading_title = reading.title if reading else "your recent assessment"
                notification_message = f"Your assessment results for reading ID {assessment.reading_id} are ready."

                # 1. Create Notification in DB
                new_db_notification = DomainNotification(
                    notification_id=uuid4(),
                    user_id=assessment.student_id,
                    type=NotificationTypeEnum.RESULT,
                    message=notification_message,
                    related_entity_id=assessment.assessment_id
                    # is_read defaults to False, created_at defaults to now in entity
                )
                await notification_repo.create(new_db_notification)

                # 2. Prepare payload for real-time WebSocket notification
                notification_payload_for_ws = {
                    "notificationId": str(new_db_notification.notification_id),
                    "message": new_db_notification.message,
                    "relatedEntityId": str(new_db_notification.related_entity_id),
                    "type": new_db_notification.type.value, # Send enum value
                    "isRead": new_db_notification.is_read,
                    "createdAt": new_db_notification.created_at.isoformat()
                }
                # Dispatch real-time notification via NotificationService
                await notification_service.notify(
                    user_id=assessment.student_id,
                    event_type=NotificationTypeEnum.RESULT.value, # Use enum value as event type string
                    data=notification_payload_for_ws
                )

            await session.commit()
            print(f"[CeleryTask] Assessment {assessment_id_str} successfully processed. Status: COMPLETED. Result saved. Notification dispatched.")

        except Exception as e:
            print(f"[CeleryTask] Error during AI processing or DB update for assessment {assessment_id_str}: {e}")
            if assessment:
                assessment.status = AssessmentStatus.ERROR
                assessment.ai_raw_speech_to_text = f"Processing Error: {str(e)[:500]}"
                assessment.updated_at = datetime.now(timezone.utc)
                # Try to update DB even if main transaction failed (e.g. AI service error)
                try:
                    # If session is compromised, a new session might be needed for this update
                    # For now, assume session might still be usable or commit handles it.
                    # If the session was rolled back by context manager, this update won't persist unless committed separately.
                    # The current structure with one session means if commit fails, this error update might also fail.
                    # A robust solution would use a separate session/transaction for the error update.
                    async with AsyncSessionLocal() as error_session: # New session for error update
                        error_assessment_repo = AssessmentRepositoryImpl(error_session)
                        # Fetch fresh assessment to avoid detached instance issues if main session rolled back
                        assessment_for_error_update = await error_assessment_repo.get_by_id(assessment_id)
                        if assessment_for_error_update:
                            assessment_for_error_update.status = AssessmentStatus.ERROR
                            assessment_for_error_update.ai_raw_speech_to_text = f"Processing Error: {str(e)[:500]}"
                            assessment_for_error_update.updated_at = datetime.now(timezone.utc)
                            await error_assessment_repo.update(assessment_for_error_update)
                            await error_session.commit()
                            print(f"[CeleryTask] Assessment {assessment_id_str} status updated to ERROR due to processing failure.")
                        else:
                             print(f"[CeleryTask] CRITICAL: Assessment {assessment_id_str} not found during error update attempt.")
                except Exception as db_error_on_error_update:
                    print(f"[CeleryTask] CRITICAL: Failed to update assessment status to ERROR for {assessment_id_str} "
                          f"after processing error. DB error on error update: {db_error_on_error_update}")
            raise


@celery_app.task(
    name="process_assessment_audio_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60*5, # Retry after 5 minutes
    acks_late=True
)
def process_assessment_audio_task(self, assessment_id_str: str):
    """
    Celery task wrapper for initiating asynchronous AI processing of an assessment's audio.
    Args:
        assessment_id_str: The string representation of the Assessment's UUID.
    """
    print(f"[CeleryTask] Task instance {self.request.id} (attempt {self.request.retries + 1}) "
          f"received for assessment_id: {assessment_id_str}.")

    try:
        # Run the main asynchronous processing logic
        asyncio.run(_process_assessment_and_update_db_async(assessment_id_str))
        print(f"[CeleryTask] Asynchronous processing for {assessment_id_str} completed successfully by wrapper.")
        return {"assessment_id": assessment_id_str, "status": "processing_completed_or_handled"}
    except Exception as e:
        print(f"[CeleryTask] Error in synchronous wrapper for assessment {assessment_id_str}: {type(e).__name__} - {e}")
        # Decide on retry strategy based on the exception type if needed
        # For example, don't retry for non-transient errors like "Assessment not found" if already handled in async part.
        # If _process_assessment_and_update_db_async re-raises, Celery's retry mechanism will take over.
        # This 'raise' here ensures Celery sees the failure if the async part didn't handle it for retry.
        raise self.retry(exc=e) if self.request.retries < (self.max_retries or 0) else e
