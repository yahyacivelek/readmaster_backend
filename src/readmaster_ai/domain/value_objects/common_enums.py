"""
Commonly used Enums throughout the domain.
"""
from enum import Enum

class UserRole(Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"
    ADMIN = "admin"

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class AssessmentStatus(Enum):
    PENDING_AUDIO = "pending_audio"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class NotificationType(Enum):
    ASSIGNMENT = "assignment"
    RESULT = "result"
    FEEDBACK = "feedback"
    SYSTEM = "system"
