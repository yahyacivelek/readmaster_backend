"""
Data Transfer Objects (DTOs) for Readmaster.ai.

This package contains Pydantic models used for transferring data
between layers of the application, particularly between the
presentation layer (API request/response models) and the
application layer (use case inputs/outputs).
"""

from .assessment_dto import CreateAssessmentDTO
from .reading_dtos import (
    ReadingBaseDTO,
    ReadingCreateDTO,
    ReadingUpdateDTO,
    ReadingResponseDTO
)
from .quiz_question_dtos import (
    QuizQuestionBaseDTO,
    QuizQuestionCreateDTO,
    QuizQuestionUpdateDTO,
    QuizQuestionResponseDTO
)

__all__ = [
    "CreateAssessmentDTO",
    "ReadingBaseDTO",
    "ReadingCreateDTO",
    "ReadingUpdateDTO",
    "ReadingResponseDTO",
    "QuizQuestionBaseDTO",
    "QuizQuestionCreateDTO",
    "QuizQuestionUpdateDTO",
    "QuizQuestionResponseDTO",
    # Assessment DTOs
    "StartAssessmentRequestDTO",
    "AssessmentResponseBaseDTO",
    "AssessmentResponseDTO",
    "RequestUploadURLResponseDTO",
    "QuizAnswerDTO", # Added
    "QuizSubmissionRequestDTO",
    "QuizSubmissionResponseDTO",
    "StudentQuizAnswerResponseDTO",
    "SubmittedAnswerDetailDTO",
    "AssessmentResultDetailDTO",
    "UserResponseDTO",
    "ClassBaseDTO",
    "ClassCreateDTO",
    "ClassUpdateDTO",
    "ClassResponseDTO",
    "AddStudentToClassRequestDTO",
    # Assignment DTOs
    "AssignReadingRequestDTO",
    "CreatedAssignmentInfoDTO",
    "AssignmentResponseDTO",
    # Progress DTOs
    "AssessmentAttemptSummaryDTO",
    "StudentProgressSummaryDTO",
    "ClassProgressReportDTO",
]

from .assessment_dtos import (
    StartAssessmentRequestDTO,
    AssessmentResponseBaseDTO,
    AssessmentResponseDTO,
    RequestUploadURLResponseDTO,
    QuizAnswerDTO,
    QuizSubmissionRequestDTO,
    QuizSubmissionResponseDTO,
    StudentQuizAnswerResponseDTO,
    SubmittedAnswerDetailDTO,
    AssessmentResultDetailDTO,
    AssignReadingRequestDTO,
    CreatedAssignmentInfoDTO,
    AssignmentResponseDTO
)
from .user_dtos import UserResponseDTO
from .class_dtos import (
    ClassBaseDTO,
    ClassCreateDTO,
    ClassUpdateDTO,
    ClassResponseDTO,
    AddStudentToClassRequestDTO
)
from .progress_dtos import ( # Added
    AssessmentAttemptSummaryDTO,
    StudentProgressSummaryDTO,
    ClassProgressReportDTO
)
