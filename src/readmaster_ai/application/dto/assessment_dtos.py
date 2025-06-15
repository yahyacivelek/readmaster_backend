"""
Data Transfer Objects (DTOs) for Assessment operations.
"""
from pydantic import BaseModel, Field, HttpUrl # HttpUrl for audio_file_url if it's a URL
from typing import Optional, List, Any # List for future use, e.g., listing assessments
from uuid import UUID
from datetime import datetime
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus # Use centralized enum
# from .reading_dtos import ReadingResponseDTO # Potentially for including reading details in response

class StartAssessmentRequestDTO(BaseModel):
    """DTO for a student to request the start of a new assessment."""
    reading_id: UUID = Field(..., description="The ID of the reading material for the assessment.")

class AssessmentResponseBaseDTO(BaseModel):
    """Base DTO for assessment responses, containing common fields shared across different views."""
    assessment_id: UUID
    student_id: UUID
    reading_id: UUID
    status: AssessmentStatus # Uses the AssessmentStatus enum
    assessment_date: datetime
    updated_at: datetime
    audio_file_url: Optional[str] = None # Using str, can be HttpUrl if validated as such upon upload completion
    audio_duration: Optional[int] = Field(None, description="Duration of the audio in seconds.")
    ai_raw_speech_to_text: Optional[str] = Field(None, description="Raw speech-to-text output from AI processing.")
    assigned_by_teacher_id: Optional[UUID] = None
    assigned_by_parent_id: Optional[UUID] = None # Added for parent assignments

class AssessmentResponseDTO(AssessmentResponseBaseDTO):
    """
    Standard DTO for representing an assessment in API responses.
    This can be used when an assessment is created or retrieved.
    """
    # Optionally, include full reading details if needed by the frontend for context.
    # For example, after starting an assessment, the frontend might want reading title.
    # reading: Optional[ReadingResponseDTO] = None
    # Or just specific fields:
    # reading_title: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = True # Ensure enums are represented as their string values in JSON

# Future DTOs could include:
# class UploadAudioDTO(BaseModel):
#     audio_file: UploadFile # For FastAPI file uploads
#
# class AssessmentResultDetailDTO(BaseModel): # For showing results after processing
#     ... (fields from AssessmentResult entity) ...
#     assessment: AssessmentResponseDTO # Nested original assessment details
#
# class StudentAssessmentListItemDTO(AssessmentResponseBaseDTO): # For students listing their assessments
#     reading_title: str # Example of adding specific field for list views
#     # Omit fields like ai_raw_speech_to_text if not needed for list item
#     ai_raw_speech_to_text: Optional[str] = Field(None, exclude=True) # Example of excluding a field
#
# class TeacherAssessmentViewDTO(AssessmentResponseDTO): # For teachers viewing student assessments
#     student_name: Optional[str] = None
#     # Could include student details

from typing import Dict # Add Dict for RequestUploadURLResponseDTO

class RequestUploadURLResponseDTO(BaseModel):
    """DTO for the response when requesting a presigned URL for file upload."""
    upload_url: str = Field(..., description="The presigned URL to which the client should upload the file.")
    blob_name: str = Field(..., description="The name of the blob (file path in storage) that will be created.")
    # For some providers (e.g., S3 presigned POST), additional form fields might be required.
    # For GCS presigned PUT, this is often not needed or just includes headers like Content-Type.
    required_fields: Optional[Dict[str, str]] = Field(None, description="Any required fields or headers for the upload request.")


class ConfirmUploadRequestDTO(BaseModel):
    """DTO for confirming that an audio file has been successfully uploaded to storage."""
    blob_name: str = Field(..., description="The unique blob name (path in storage) of the uploaded file.")
    # file_size: Optional[int] = Field(None, description="Size of the uploaded file in bytes.") # Optional
    # content_type: Optional[str] = Field(None, description="Actual content type of the uploaded file.") # Optional

class ConfirmUploadResponseDTO(BaseModel):
    """DTO for the response after confirming an upload and initiating processing."""
    assessment_id: UUID
    status: AssessmentStatus
    message: str


# --- DTOs for Quiz Submission ---

class QuizAnswerDTO(BaseModel):
    """DTO representing a single answer to a quiz question."""
    question_id: UUID = Field(..., description="The ID of the quiz question being answered.")
    selected_option_id: str = Field(..., description="The ID of the option selected by the student.")

class QuizSubmissionRequestDTO(BaseModel):
    """DTO for submitting a list of quiz answers for an assessment."""
    answers: List[QuizAnswerDTO] = Field(..., description="A list of answers submitted by the student.")

class QuizSubmissionResponseDTO(BaseModel):
    """DTO for the response after submitting quiz answers."""
    assessment_id: UUID
    comprehension_score: float = Field(..., description="The calculated comprehension score (0.0 to 100.0).")
    total_questions: int = Field(..., description="Total number of questions answered.")
    correct_answers: int = Field(..., description="Number of correctly answered questions.")
    message: str = "Quiz answers submitted successfully."


class StudentQuizAnswerResponseDTO(BaseModel): # For displaying submitted answers later, if needed
    """DTO representing a student's answer to a quiz question, for review."""
    question_id: UUID
    selected_option_id: str
    is_correct: bool
    # question_text: Optional[str] = None # Can be enriched by joining with QuizQuestion data
    # correct_option_id_for_review: Optional[str] = None # For review purposes, showing the actual correct answer
    options: Optional[Dict[str, Any]] = Field(None, description="All available options for this question.") # Added to show all options during review

    class Config:
        from_attributes = True


# --- DTOs for Assessment Results ---
from typing import Any # For analysis_data Dict

class SubmittedAnswerDetailDTO(BaseModel):
    """DTO for individual student answer review, including question context."""
    question_id: UUID
    question_text: str = Field(..., description="The text of the quiz question.")
    selected_option_id: str = Field(..., description="The option ID selected by the student.")
    is_correct: bool = Field(..., description="Whether the selected option was correct.")
    correct_option_id: str = Field(..., description="The ID of the correct option for this question.")
    options: Dict[str, Any] = Field(..., description="All available options for this question.") # e.g., {"A": "Text A", "B": "Text B"}

    class Config:
        from_attributes = True


class AssessmentResultDetailDTO(AssessmentResponseBaseDTO):
    """
    Comprehensive DTO for displaying detailed assessment results to a student.
    Inherits common assessment fields from AssessmentResponseBaseDTO.
    """
    reading_title: Optional[str] = Field(None, description="Title of the reading material for context.")

    # From AssessmentResult entity (domain)
    analysis_data: Optional[Dict[str, Any]] = Field(None, description="Detailed AI analysis data (e.g., fluency, pronunciation).")
    comprehension_score: Optional[float] = Field(None, description="Calculated comprehension score based on quiz answers (0-100).")

    # List of submitted answers with details for review by the student
    submitted_answers: List[SubmittedAnswerDetailDTO] = Field([], description="Detailed list of submitted quiz answers for review.")

    class Config:
        from_attributes = True
        use_enum_values = True # Ensure enums like status are serialized as values


# --- DTOs for Assigning Readings ---
from datetime import date # For due_date

class AssignReadingRequestDTO(BaseModel):
    """DTO for a teacher to assign a reading to students or a class."""
    reading_id: UUID = Field(..., description="The ID of the reading material to assign.")
    student_ids: Optional[List[UUID]] = Field(default_factory=list, description="A list of specific student IDs to assign the reading to.")
    class_id: Optional[UUID] = Field(None, description="The ID of a class to assign the reading to all its students. If provided, student_ids might be ignored or augmented.")
    due_date: Optional[date] = Field(None, description="Optional due date for the assignment.") # Conceptual for now

class CreatedAssignmentInfoDTO(BaseModel):
    """DTO providing information about a single assessment created as part of an assignment."""
    assessment_id: UUID
    student_id: UUID
    reading_id: UUID # Included for completeness, though context implies it
    status: AssessmentStatus # Should be PENDING_AUDIO initially

    class Config:
        from_attributes = True
        use_enum_values = True


class AssignmentResponseDTO(BaseModel):
    """DTO for the response after a teacher assigns a reading."""
    message: str = "Reading assigned successfully."
    created_assessments: List[CreatedAssignmentInfoDTO] = Field(default_factory=list)
    skipped_students: Optional[List[UUID]] = Field(default_factory=list, description="List of student IDs for whom assessment creation was skipped (e.g., invalid ID, not a student).")


# --- DTOs for Parent Assigning Readings ---

class ParentAssignReadingRequestDTO(BaseModel):
    reading_id: UUID = Field(..., description="The ID of the reading material to assign.")
    due_date: Optional[date] = Field(None, description="Optional due date for the assignment.")

    class Config:
        from_attributes = True


class AssignmentUpdateDTO(BaseModel): # Could be used by Teacher or Parent
    """DTO for updating an existing assignment, e.g., its due date."""
    due_date: Optional[date] = Field(None, description="New due date for the assignment.")
    # Potentially other fields like notes, or status if assignments can be paused/resumed.

    class Config:
        from_attributes = True
