"""
Abstract repository interfaces for domain entities.

This package defines the contracts (interfaces) that repository
implementations in the infrastructure layer must adhere to.
These interfaces allow the domain and application layers to remain
independent of specific data storage technologies.
"""

from .user_repository import UserRepository
from .assessment_repository import AssessmentRepository
from .reading_repository import ReadingRepository
from .quiz_question_repository import QuizQuestionRepository

__all__ = [
    "UserRepository",
    "AssessmentRepository",
    "ReadingRepository",
    "QuizQuestionRepository",
    "AssessmentResultRepository",
    "StudentQuizAnswerRepository",
    "ClassRepository", # Added
]

from .assessment_result_repository import AssessmentResultRepository
from .student_quiz_answer_repository import StudentQuizAnswerRepository
from .class_repository import ClassRepository # Added
