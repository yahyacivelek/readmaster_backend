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
from readmaster_ai.application.dto.user_dtos import UserResponseDTO, ParentChildCreateRequestDTO, UserCreateDTO
from readmaster_ai.application.dto.progress_dtos import StudentProgressSummaryDTO
from readmaster_ai.application.dto.assessment_dtos import (
    AssessmentResultDetailDTO,
    ParentAssignReadingRequestDTO,
    AssessmentResponseDTO, # For assignment responses
    AssignmentUpdateDTO,
)
from readmaster_ai.application.dto.assessment_list_dto import PaginatedAssessmentListResponseDTO, AssessmentListItemDTO, AssessmentStudentInfoDTO, AssessmentReadingInfoDTO


# Domain Entities
from readmaster_ai.domain.entities.assessment import Assessment # Added for new use cases

# Value Objects
from readmaster_ai.domain.value_objects.common_enums import AssessmentStatus # Added

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


class CreateChildAccountUseCase: # Renamed from CreateStudentByParentUseCase
    """Use case for an authenticated parent to create a new student account (their child)."""
    def __init__(self, user_repository: UserRepository): # Renamed user_repo to user_repository
        self.user_repository = user_repository

    async def execute(self, parent_user: DomainUser, child_data: ParentChildCreateRequestDTO) -> UserResponseDTO: # Changed child_data type and return type
        """
        Executes the student creation process by a parent.

        Args:
            parent_user: The authenticated parent (DomainUser).
            child_data: DTO containing data for the new student (child).

        Returns:
            A UserResponseDTO for the created student.

        Raises:
            ForbiddenException: If the requesting user is not a parent.
            ApplicationException: If email already exists or other validation fails (e.g., from user_repo.create).
        """
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not authorized to create a child account.")

        existing_user = await self.user_repository.get_by_email(child_data.email)
        if existing_user:
            raise ApplicationException(f"User with email {child_data.email} already exists.", status_code=409)

        hashed_password = pwd_context.hash(child_data.password)

        # Using UserCreateDTO as an intermediary for user creation by repository
        # The repository's create_user method should expect a User entity or a compatible DTO.
        # For consistency, if user_repository.create_user_with_role exists and takes UserCreateDTO:
        user_create_dto = UserCreateDTO(
            email=child_data.email,
            password=hashed_password, # Store hashed password
            first_name=child_data.first_name,
            last_name=child_data.last_name,
            preferred_language=child_data.preferred_language,
            role=UserRole.STUDENT # Explicitly set role to student
        )
        # This assumes create_user_with_role or similar exists that takes UserCreateDTO
        # If not, we'd map to DomainUser like the original code and call `self.user_repository.create()`
        created_student_entity = await self.user_repository.create_user_with_role(user_create_dto)

        # Link parent to child
        await self.user_repository.link_parent_to_student(parent_id=parent_user.user_id, student_id=created_student_entity.user_id)

        return UserResponseDTO.model_validate(created_student_entity)


# Placeholder for BaseUseCase if common functionality is needed later
class BaseUseCase: # Added placeholder
    pass

class ParentAssignReadingUseCase(BaseUseCase):
    def __init__(self,
                 assessment_repository: AssessmentRepository,
                 user_repository: UserRepository,
                 reading_repository: ReadingRepository):
        self.assessment_repository = assessment_repository
        self.user_repository = user_repository
        self.reading_repository = reading_repository

    async def execute(self, parent_user: DomainUser, child_id: UUID, assign_data: ParentAssignReadingRequestDTO) -> AssessmentResponseDTO:
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not authorized or not found.")

        is_child = await self.user_repository.is_parent_of_student(parent_user.user_id, child_id)
        if not is_child:
            raise ForbiddenException("Student is not a child of this parent.")

        reading = await self.reading_repository.get_by_id(assign_data.reading_id)
        if not reading:
            raise NotFoundException(resource_name="Reading", resource_id=str(assign_data.reading_id))

        assessment = Assessment( # Domain entity
            student_id=child_id,
            reading_id=assign_data.reading_id,
            assigned_by_parent_id=parent_user.user_id,
            status=AssessmentStatus.PENDING_AUDIO,
            # due_date from assign_data.due_date is ignored as Assessment entity doesn't have it.
        )

        await self.assessment_repository.create(assessment) # Changed add to create
        return AssessmentResponseDTO.model_validate(assessment)


class ListChildAssignmentsUseCase(BaseUseCase):
    def __init__(self,
                 assessment_repository: AssessmentRepository,
                 user_repository: UserRepository,
                 reading_repository: ReadingRepository): # Added reading_repository for enriching items
        self.assessment_repository = assessment_repository
        self.user_repository = user_repository
        self.reading_repository = reading_repository


    async def execute(self, parent_user: DomainUser, child_id: UUID, page: int, size: int) -> PaginatedAssessmentListResponseDTO:
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not authorized or not found.")

        is_child = await self.user_repository.is_parent_of_student(parent_user.user_id, child_id)
        if not is_child:
            raise ForbiddenException("Student is not a child of this parent.")

        child_user = await self.user_repository.get_by_id(child_id)
        if not child_user: # Should not happen if is_child passed, but good check
            raise NotFoundException(resource_name="Child", resource_id=str(child_id))

        assessments_page = await self.assessment_repository.list_by_child_and_assigner(
            student_id=child_id,
            parent_id=parent_user.user_id,
            page=page,
            size=size
        )

        items_dto: List[AssessmentListItemDTO] = []
        for assessment_entity in assessments_page.items:
            reading_info_dto = None
            if assessment_entity.reading_id: # Should always be true for an assignment
                reading = await self.reading_repository.get_by_id(assessment_entity.reading_id)
                if reading:
                    reading_info_dto = AssessmentReadingInfoDTO(reading_id=reading.reading_id, title=reading.title)

            student_info_dto = AssessmentStudentInfoDTO(
                student_id=child_user.user_id,
                first_name=child_user.first_name,
                last_name=child_user.last_name,
                # grade: This would typically come from Class context, which parent-assigned readings might not have.
                # For now, leave as None or derive if possible.
                grade=None
            )

            items_dto.append(
                AssessmentListItemDTO(
                    assessment_id=assessment_entity.assessment_id,
                    status=assessment_entity.status,
                    assessment_date=assessment_entity.assessment_date,
                    updated_at=assessment_entity.updated_at,
                    student=student_info_dto,
                    reading=reading_info_dto if reading_info_dto else AssessmentReadingInfoDTO(reading_id=assessment_entity.reading_id, title="Unknown Reading"),
                    user_relationship_context="Your Child" # For parent view
                )
            )

        return PaginatedAssessmentListResponseDTO(
            items=items_dto,
            page=assessments_page.page,
            size=assessments_page.size,
            total_count=assessments_page.total_count
        )


class UpdateChildAssignmentUseCase(BaseUseCase):
    def __init__(self, assessment_repository: AssessmentRepository, user_repository: UserRepository):
        self.assessment_repository = assessment_repository
        self.user_repository = user_repository

    async def execute(self, parent_user: DomainUser, child_id: UUID, assignment_id: UUID, update_data: AssignmentUpdateDTO) -> AssessmentResponseDTO:
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not authorized or not found.")

        assessment = await self.assessment_repository.get_by_id(assignment_id)
        if not assessment:
            raise NotFoundException(resource_name="Assignment (Assessment)", resource_id=str(assignment_id))

        if assessment.student_id != child_id or assessment.assigned_by_parent_id != parent_user.user_id:
            raise ForbiddenException("User is not authorized to update this assignment.")

        if update_data.due_date:
            # Assessment entity does not have due_date yet. This is a no-op for now.
            # assessment.due_date = update_data.due_date
            pass

        await self.assessment_repository.update(assessment) # Will save other changes if any were made to entity
        return AssessmentResponseDTO.model_validate(assessment)


class DeleteChildAssignmentUseCase(BaseUseCase):
    def __init__(self, assessment_repository: AssessmentRepository, user_repository: UserRepository):
        self.assessment_repository = assessment_repository
        self.user_repository = user_repository

    async def execute(self, parent_user: DomainUser, child_id: UUID, assignment_id: UUID) -> None:
        if parent_user.role != UserRole.PARENT:
            raise ForbiddenException("User is not authorized or not found.")

        assessment = await self.assessment_repository.get_by_id(assignment_id)
        if not assessment:
            # If deleting a non-existent resource is fine (e.g. for idempotency), return None.
            # For assignments, it's better to ensure it existed and belonged to them.
            raise NotFoundException(resource_name="Assignment (Assessment)", resource_id=str(assignment_id))

        if assessment.student_id != child_id or assessment.assigned_by_parent_id != parent_user.user_id:
            raise ForbiddenException("User is not authorized to delete this assignment.")

        await self.assessment_repository.delete(assessment_id)
        return None
