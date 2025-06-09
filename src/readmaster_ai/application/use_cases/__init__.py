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
# CreateAssessmentUseCase was here, but it's more specific, keeping it separate for now unless grouped later
from .create_assessment_use_case import CreateAssessmentUseCase


__all__ = [
    "CreateUserUseCase",
    "GetUserProfileUseCase",
    "UpdateUserProfileUseCase",
    "CreateAssessmentUseCase", # Keep it if it's considered a primary use case exposed here
    "CreateReadingUseCase",
    "GetReadingUseCase",
    "ListReadingsUseCase",
    "UpdateReadingUseCase",
    "DeleteReadingUseCase",
    "AddQuizQuestionToReadingUseCase",
    "GetQuizQuestionUseCase",
    "ListQuizQuestionsByReadingUseCase",
    "UpdateQuizQuestionUseCase",
    "DeleteQuizQuestionUseCase",
    # Assessment Use Cases
    "StartAssessmentUseCase",
    "RequestAssessmentAudioUploadURLUseCase",
    "ConfirmAudioUploadUseCase",
    "SubmitQuizAnswersUseCase",
    "GetAssessmentResultDetailsUseCase", # Added
]

from .assessment_use_cases import (
    StartAssessmentUseCase,
    RequestAssessmentAudioUploadURLUseCase,
    ConfirmAudioUploadUseCase,
    SubmitQuizAnswersUseCase,
    GetAssessmentResultDetailsUseCase,
    AssignReadingUseCase # Added
)
from .class_use_cases import (
    CreateClassUseCase,
    GetClassDetailsUseCase,
    ListClassesByTeacherUseCase,
    UpdateClassUseCase,
    DeleteClassUseCase,
    AddStudentToClassUseCase,
    RemoveStudentFromClassUseCase,
    ListStudentsInClassUseCase
)
from .progress_use_cases import ( # Added
    GetStudentProgressSummaryUseCase,
    GetClassProgressReportUseCase
)
from .parent_use_cases import ( # Added
    ListParentChildrenUseCase,
    GetChildProgressForParentUseCase,
    GetChildAssessmentResultForParentUseCase
)

__all__ = [
    # ... (existing user, assessment, reading, quiz question use cases) ...
    "CreateUserUseCase",
    "GetUserProfileUseCase",
    "UpdateUserProfileUseCase",
    "CreateAssessmentUseCase",
    "CreateReadingUseCase",
    "GetReadingUseCase",
    "ListReadingsUseCase",
    "UpdateReadingUseCase",
    "DeleteReadingUseCase",
    "AddQuizQuestionToReadingUseCase",
    "GetQuizQuestionUseCase",
    "ListQuizQuestionsByReadingUseCase",
    "UpdateQuizQuestionUseCase",
    "DeleteQuizQuestionUseCase",
    "StartAssessmentUseCase",
    "RequestAssessmentAudioUploadURLUseCase",
    "ConfirmAudioUploadUseCase",
    "SubmitQuizAnswersUseCase",
    "GetAssessmentResultDetailsUseCase",
    "AssignReadingUseCase", # Added
    # Class Use Cases
    "CreateClassUseCase",
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
]
