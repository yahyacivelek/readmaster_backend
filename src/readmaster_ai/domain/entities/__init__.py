# Expose domain entities for easier importing

from .user import User, UserRole
from .student import Student
from .teacher import Teacher
from .parent import Parent
from .admin import Admin
from .reading import Reading, DifficultyLevel
from .assessment import Assessment, AssessmentStatus
from .assessment_result import AssessmentResult
from .quiz_question import QuizQuestion
from .class_entity import ClassEntity # Renamed from Class
from .student_quiz_answer import StudentQuizAnswer
from .progress_tracking import ProgressTracking
from .notification import Notification, NotificationType

__all__ = [
    "User", "UserRole",
    "Student",
    "Teacher",
    "Parent",
    "Admin",
    "Reading", "DifficultyLevel",
    "Assessment", "AssessmentStatus",
    "AssessmentResult",
    "QuizQuestion",
    "ClassEntity",
    "StudentQuizAnswer",
    "ProgressTracking",
    "Notification", "NotificationType",
]
