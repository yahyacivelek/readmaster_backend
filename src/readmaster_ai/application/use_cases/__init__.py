"""
Use Cases Layer for Readmaster.ai.

This package contains classes that orchestrate the application's business logic.
Use cases interact with domain entities and repositories, and are typically
invoked by the presentation layer (e.g., API routers) or application services.
They encapsulate specific operations or workflows of the application.
"""

from .user_use_cases import (
    CreateUserUseCase,
    GetUserProfileUseCase,
    UpdateUserProfileUseCase
)
from .reading_use_cases import (
    CreateReadingUseCase,
    GetReadingUseCase,
    ListReadingsUseCase,
    UpdateReadingUseCase,
    DeleteReadingUseCase
)
from .quiz_question_use_cases import (
    AddQuizQuestionToReadingUseCase,
    GetQuizQuestionUseCase,
    ListQuizQuestionsByReadingUseCase,
    UpdateQuizQuestionUseCase,
    DeleteQuizQuestionUseCase
)
from .create_assessment_use_case import CreateAssessmentUseCase
from .assessment_use_cases import (
    StartAssessmentUseCase,
    RequestAssessmentAudioUploadURLUseCase,
    ConfirmAudioUploadUseCase,
    SubmitQuizAnswersUseCase,
    GetAssessmentResultDetailsUseCase,
    AssignReadingUseCase,
    ListAssessmentsByReadingIdUseCase, # Added new use case
)
from .class_use_cases import (
    CreateClassUseCase, # Note: Also in user_use_cases for some reason in provided content, but should be distinct
    GetClassDetailsUseCase,
    ListClassesByTeacherUseCase,
    UpdateClassUseCase,
    DeleteClassUseCase,
    AddStudentToClassUseCase,
    RemoveStudentFromClassUseCase,
    ListStudentsInClassUseCase
)
from .progress_use_cases import (
    GetStudentProgressSummaryUseCase,
    GetClassProgressReportUseCase
)
from .parent_use_cases import (
    ListParentChildrenUseCase,
    GetChildProgressForParentUseCase,
    GetChildAssessmentResultForParentUseCase
)
from .notification_use_cases import ( # Added
    ListUserNotificationsUseCase,
    MarkNotificationAsReadUseCase,
    MarkAllNotificationsAsReadUseCase
)
from .system_config_use_cases import ( # Added
    GetSystemConfigurationUseCase,
    UpdateSystemConfigurationUseCase,
    ListSystemConfigurationsUseCase
)

__all__ = [
    # User Use Cases
    "CreateUserUseCase",
    "GetUserProfileUseCase",
    "UpdateUserProfileUseCase",
    # Reading Use Cases
    "CreateReadingUseCase",
    "GetReadingUseCase",
    "ListReadingsUseCase",
    "UpdateReadingUseCase",
    "DeleteReadingUseCase",
    # QuizQuestion Use Cases
    "AddQuizQuestionToReadingUseCase",
    "GetQuizQuestionUseCase",
    "ListQuizQuestionsByReadingUseCase",
    "UpdateQuizQuestionUseCase",
    "DeleteQuizQuestionUseCase",
    # Assessment Use Cases (including create_assessment_use_case.py)
    "CreateAssessmentUseCase",
    "StartAssessmentUseCase",
    "RequestAssessmentAudioUploadURLUseCase",
    "ConfirmAudioUploadUseCase",
    "SubmitQuizAnswersUseCase",
    "GetAssessmentResultDetailsUseCase",
    "AssignReadingUseCase",
    "ListAssessmentsByReadingIdUseCase", # Added new use case
    # Class Use Cases
    # "CreateClassUseCase", # Already listed if it's the same one. Assuming class_use_cases.CreateClassUseCase is the one.
    "GetClassDetailsUseCase",
    "ListClassesByTeacherUseCase",
    "UpdateClassUseCase",
    "DeleteClassUseCase",
    "AddStudentToClassUseCase",
    "RemoveStudentFromClassUseCase",
    "ListStudentsInClassUseCase",
    # Progress Use Cases
    "GetStudentProgressSummaryUseCase",
    "GetClassProgressReportUseCase",
    # Parent Use Cases
    "ListParentChildrenUseCase",
    "GetChildProgressForParentUseCase",
    "GetChildAssessmentResultForParentUseCase",
    # Notification Use Cases
    "ListUserNotificationsUseCase",
    "MarkNotificationAsReadUseCase",
    "MarkAllNotificationsAsReadUseCase",
    # System Configuration Use Cases
    "GetSystemConfigurationUseCase",
    "UpdateSystemConfigurationUseCase",
    "ListSystemConfigurationsUseCase",
]
