from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone

# Enums are now in value_objects
# from enum import Enum # No longer needed here
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus

if TYPE_CHECKING:
    from .assessment_result import AssessmentResult
    from .student_quiz_answer import StudentQuizAnswer # Corrected name


class Assessment:
    assessment_id: UUID
    student_id: UUID # FK
    reading_id: UUID # FK
    assigned_by_teacher_id: Optional[UUID] # FK, from ERD
    assigned_by_parent_id: Optional[UUID] # FK
    audio_file_url: Optional[str]
    audio_duration: Optional[int] # In seconds, as per ERD
    status: AssessmentStatus
    assessment_date: datetime
    ai_raw_speech_to_text: Optional[str]
    # result: Optional[AssessmentResult] # One-to-one, managed by repository
    # quiz_answers: List[StudentQuizAnswer] # One-to-many, managed by repository
    updated_at: datetime
    due_date: Optional[date] # Changed to date type

    def __init__(self, student_id: UUID, reading_id: UUID, # student_id and reading_id are mandatory
                 assessment_id: Optional[UUID] = None,
                 assigned_by_teacher_id: Optional[UUID] = None,
                 assigned_by_parent_id: Optional[UUID] = None,
                 audio_file_url: Optional[str] = None, audio_duration: Optional[int] = None,
                 status: AssessmentStatus = AssessmentStatus.PENDING_AUDIO,
                 assessment_date: Optional[datetime] = None,
                 ai_raw_speech_to_text: Optional[str] = None,
                 updated_at: Optional[datetime] = None,
                 due_date: Optional[date] = None): # Changed due_date to date type in constructor
        self.assessment_id = assessment_id if assessment_id else uuid4()
        self.student_id = student_id
        self.reading_id = reading_id
        self.assigned_by_teacher_id = assigned_by_teacher_id
        self.assigned_by_parent_id = assigned_by_parent_id
        self.audio_file_url = audio_file_url
        self.audio_duration = audio_duration
        self.status = status
        
        # Ensure timezone-aware UTC datetimes
        now = datetime.now(timezone.utc)
        self.assessment_date = assessment_date.replace(tzinfo=timezone.utc) if assessment_date and assessment_date.tzinfo is None else (assessment_date or now)
        self.ai_raw_speech_to_text = ai_raw_speech_to_text
        self.due_date = due_date # Store due_date as date
        self.result: Optional[AssessmentResult] = None # Initialize as None
        self.quiz_answers: List[StudentQuizAnswer] = [] # Initialize as empty list
        self.updated_at = updated_at.replace(tzinfo=timezone.utc) if updated_at and updated_at.tzinfo is None else (updated_at or now)


    def process_audio(self) -> bool:
        # Logic to trigger audio processing (e.g., send to AI service)
        # This would typically be handled by an application service.
        if self.audio_file_url and self.status == AssessmentStatus.PENDING_AUDIO:
            print(f"Assessment {self.assessment_id}: Processing audio file {self.audio_file_url}.")
            self.status = AssessmentStatus.PROCESSING
            self.updated_at = datetime.now(timezone.utc)
            # In a real system, this would likely enqueue a task for an AI worker.
            return True
        print(f"Assessment {self.assessment_id}: Cannot process. Audio URL: {self.audio_file_url}, Status: {self.status}")
        return False

    def calculate_scores(self) -> bool:
        # Logic to calculate scores based on AI analysis and quiz answers
        # This would be invoked after AI processing and quiz submission.
        # Updates self.result (AssessmentResult)
        if self.status == AssessmentStatus.PROCESSING: # Or some other appropriate status
            print(f"Assessment {self.assessment_id}: Calculating scores.")
            from .assessment_result import AssessmentResult # Local import
            # Example: self.result = AssessmentResult(assessment_id=self.assessment_id, analysis_data={"dummy": "data"}, comprehension_score=0.0)
            self.status = AssessmentStatus.COMPLETED
            self.updated_at = datetime.now(timezone.utc)
            return True
        print(f"Assessment {self.assessment_id}: Cannot calculate scores. Status: {self.status}")
        return False

    def add_quiz_answer(self, answer: StudentQuizAnswer):
        self.quiz_answers.append(answer)
        self.updated_at = datetime.now(timezone.utc)
        print(f"Quiz answer added to assessment {self.assessment_id}")


    def set_result(self, result: AssessmentResult):
        self.result = result
        self.updated_at = datetime.now(timezone.utc)
        print(f"Result set for assessment {self.assessment_id}")
