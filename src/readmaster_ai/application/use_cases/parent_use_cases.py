"""
Use cases specific to Parent users, such as viewing their children's progress
and assessment results.
"""
from typing import List, Optional
from uuid import UUID
from uuid import uuid4 # For generating user_id

# Domain Entities and Repositories
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository # For reused UC
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository # For reused UC
from readmaster_ai.domain.repositories.student_quiz_answer_repository import StudentQuizAnswerRepository # For reused UC
from readmaster_ai.domain.repositories.quiz_question_repository import QuizQuestionRepository # For reused UC
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository # For reused UC


# Application DTOs
from readmaster_ai.application.dto.user_dtos import UserResponseDTO # For listing children
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from readmaster_ai.application.dto.assessment_dtos import AssessmentResultDetailDTO
from readmaster_ai.presentation.schemas.user_schemas import ParentChildCreateRequestSchema # Input DTO

# Reused Use Cases for fetching detailed data
from readmaster_ai.application.use_cases.progress_use_cases import GetStudentProgressSummaryUseCase
from readmaster_ai.application.use_cases.assessment_use_cases import GetAssessmentResultDetailsUseCase
# Import pwd_context from user_use_cases, or define it if preferred
from readmaster_ai.application.use_cases.user_use_cases import pwd_context

# Shared Exceptions
from readmaster_ai.shared.exceptions import ForbiddenException, NotFoundException, ApplicationException


class ListParentChildrenUseCase:
    """Use case for a parent to list their linked children."""
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, parent_user: DomainUser) -> List[UserResponseDTO]:
        """
        Executes the process of listing a parent's children.
        Args:
            parent_user: The authenticated parent (DomainUser).
        Returns:
            A list of UserResponseDTO objects representing the children.
        Raises:
            ForbiddenException: If the requesting user is not a parent.
        """
        if parent_user.role != UserRole.PARENT:
            # This check might be redundant if the endpoint is already role-protected,
            # but good for defense in depth at the use case layer.
            raise ForbiddenException("User is not a parent.")

        children_domain_list = await self.user_repo.list_children_by_parent_id(parent_user.user_id)
        return [UserResponseDTO.model_validate(child) for child in children_domain_list if child]


class GetChildProgressForParentUseCase:
    """Use case for a parent to view a specific child's progress summary."""
    def __init__(self,
                 user_repo: UserRepository, # To check parent-child link
                 # Pass all repositories needed by GetStudentProgressSummaryUseCase
                 assessment_repo: AssessmentRepository,
                 result_repo: AssessmentResultRepository,
                 reading_repo: ReadingRepository):
        self.user_repo = user_repo
        # Instantiate the reused use case here
        self.student_progress_uc = GetStudentProgressSummaryUseCase(
            user_repo=user_repo, # student_progress_uc needs user_repo to fetch the student by ID
            assessment_repo=assessment_repo,
            result_repo=result_repo,
            reading_repo=reading_repo
        )

    async def execute(self, parent_user: DomainUser, child_student_id: UUID) -> StudentProgressSummaryDTO:
        """
        Executes viewing of a child's progress.
        Args:
            parent_user: The authenticated parent.
            child_student_id: The ID of the child (student) whose progress is to be viewed.
        Returns:
            A StudentProgressSummaryDTO for the child.
        Raises:
            ForbiddenException: If user is not a parent or not linked to the child.
            NotFoundException: If the child student is not found.
        """
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not a parent.")

        is_linked = await self.user_repo.is_parent_of_student(parent_user.user_id, child_student_id)
        if not is_linked:
            raise ForbiddenException("Parent is not authorized to view this student's progress.")

        # The GetStudentProgressSummaryUseCase's `execute` method takes `student_id` and `requesting_user`.
        # The `requesting_user` in that context is for authorization checks (e.g., if a teacher is requesting).
        # Here, the parent `parent_user` is the requester. The primary authorization is `is_linked`.
        # We pass `parent_user` as `requesting_user` to satisfy the signature.
        # The internal authorization of `GetStudentProgressSummaryUseCase` might need to be aware of this
        # or be bypassed if a flag is passed, or we trust `is_linked` check.
        # For now, we assume the `is_linked` check is sufficient primary auth.
        try:
            return await self.student_progress_uc.execute(student_id=child_student_id, requesting_user=parent_user)
        except NotFoundException: # If student_id itself is not found by underlying UC
            raise NotFoundException(resource_name="Student", resource_id=str(child_student_id))


class GetChildAssessmentResultForParentUseCase:
    """Use case for a parent to view a specific assessment result of their child."""
    def __init__(self,
                 user_repo: UserRepository, # To check parent-child link and fetch child
                 # Pass all repositories needed by GetAssessmentResultDetailsUseCase
                 assessment_repo: AssessmentRepository,
                 assessment_result_repo: AssessmentResultRepository,
                 student_answer_repo: StudentQuizAnswerRepository,
                 quiz_question_repo: QuizQuestionRepository,
                 reading_repo: ReadingRepository):
        self.user_repo = user_repo
        # Instantiate the reused use case here
        self.assessment_details_uc = GetAssessmentResultDetailsUseCase(
            assessment_repo=assessment_repo,
            assessment_result_repo=assessment_result_repo,
            student_answer_repo=student_answer_repo,
            quiz_question_repo=quiz_question_repo,
            reading_repo=reading_repo
        )

    async def execute(self, parent_user: DomainUser, child_student_id: UUID, assessment_id: UUID) -> AssessmentResultDetailDTO:
        """
        Executes viewing of a child's specific assessment result.
        Args:
            parent_user: The authenticated parent.
            child_student_id: The ID of the child (student).
            assessment_id: The ID of the assessment.
        Returns:
            An AssessmentResultDetailDTO for the child's assessment.
        """
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not a parent.")

        is_linked = await self.user_repo.is_parent_of_student(parent_user.user_id, child_student_id)
        if not is_linked:
            raise ForbiddenException("Parent is not authorized to view this student's assessment results.")

        # GetAssessmentResultDetailsUseCase's `execute` method takes `assessment_id` and `student` (DomainUser object).
        # We need to fetch the child_user DomainUser object first.
        child_user = await self.user_repo.get_by_id(child_student_id)
        if not child_user or child_user.role != UserRole.STUDENT:
             raise NotFoundException(resource_name="Student", resource_id=str(child_student_id))

        # The reused use case will perform its own check: `assessment.student_id != student.user_id`
        # This will correctly ensure the assessment belongs to the `child_user`.
        try:
            return await self.assessment_details_uc.execute(assessment_id=assessment_id, student=child_user)
        except NotFoundException as e: # If assessment_id is not found or reading for assessment not found
            # Distinguish if it was assessment or related reading. For now, general.
            if e.resource_name == "Assessment":
                 raise NotFoundException(resource_name="Assessment for child", resource_id=str(assessment_id))
            raise # Re-raise other NotFoundExceptions (e.g. Reading for assessment)
        except ForbiddenException: # Should not happen if is_linked and assessment belongs to child
            # This would imply assessment.student_id != child_student_id, which is an inconsistency.
            raise ApplicationException("Assessment does not belong to the specified child.", status_code=403)


class CreateStudentByParentUseCase:
    """Use case for an authenticated parent to create a new student account (their child)."""
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, parent_user: DomainUser, child_data: ParentChildCreateRequestSchema) -> DomainUser:
        """
        Executes the student creation process by a parent.

        Args:
            parent_user: The authenticated parent (DomainUser).
            child_data: DTO containing data for the new student (child).

        Returns:
            The created student DomainUser entity.

        Raises:
            ForbiddenException: If the requesting user is not a parent.
            ApplicationException: If email already exists or other validation fails (e.g., from user_repo.create).
        """
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not authorized to create a child account.")

        existing_student_by_email = await self.user_repo.get_by_email(child_data.email)
        if existing_student_by_email:
            raise ApplicationException("A user with this email already exists.", status_code=409) # Conflict

        hashed_password = pwd_context.hash(child_data.password)

        # child_data.role is fixed to "student" by ParentChildCreateRequestSchema
        # We use UserRole.STUDENT for the domain entity.
        new_student_user = DomainUser(
            user_id=uuid4(), # Generate new UUID for the student
            email=child_data.email,
            password_hash=hashed_password,
            first_name=child_data.first_name,
            last_name=child_data.last_name,
            role=UserRole.STUDENT, # Role is fixed to STUDENT
            preferred_language=child_data.preferred_language if child_data.preferred_language else 'en',
            # class_id will be None by default as parent is creating a general student account.
            # Teacher can later add this student to a class.
        )

        created_student = await self.user_repo.create(new_student_user)

        # Link the parent to the newly created student
        # The relationship_type can be a predefined string.
        await self.user_repo.link_parent_to_student(
            parent_id=parent_user.user_id,
            student_id=created_student.user_id,
            relationship_type="parent" # Or a more generic "guardian" if applicable
        )

        return created_student
