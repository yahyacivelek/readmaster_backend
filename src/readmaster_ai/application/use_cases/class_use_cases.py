"""
Use cases related to Class (ClassEntity) management by Teachers.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Tuple, Optional

# Domain Entities and Repositories
from readmaster_ai.domain.entities.class_entity import ClassEntity as DomainClassEntity
from readmaster_ai.domain.entities.user import User as DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole # For role checks
from readmaster_ai.domain.repositories.class_repository import ClassRepository
from readmaster_ai.domain.repositories.user_repository import UserRepository # To validate student existence

# Application DTOs
from readmaster_ai.application.dto.class_dtos import ClassCreateDTO, ClassUpdateDTO # AddStudentToClassRequestDTO not needed as arg directly
# from readmaster_ai.application.dto.user_dtos import UserResponseDTO # For return types if transforming here

# Shared Exceptions
from readmaster_ai.shared.exceptions import ApplicationException, NotFoundException, ForbiddenException


class CreateClassUseCase:
    """Use case for a teacher to create a new class."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, class_data: ClassCreateDTO, teacher: DomainUser) -> DomainClassEntity:
        """
        Executes the class creation process.
        Args:
            class_data: DTO containing data for the new class.
            teacher: The authenticated teacher (DomainUser) creating the class.
        Returns:
            The created DomainClassEntity.
        Raises:
            ForbiddenException: If the user is not a teacher.
        """
        if teacher.role not in [UserRole.TEACHER, UserRole.ADMIN]: # Allow Admin to also create classes
            raise ForbiddenException("Only teachers or admins can create classes.")

        new_class = DomainClassEntity(
            class_id=uuid4(), # Application generates ID
            class_name=class_data.class_name,
            grade_level=class_data.grade_level,
            created_by_teacher_id=teacher.user_id, # Set teacher ID from context
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        created_class = await self.class_repo.create(new_class)
        return created_class

class GetClassDetailsUseCase: # Renamed from GetClassUseCase for clarity
    """Use case for retrieving details of a specific class, including its students."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, class_id: UUID, user_requesting: DomainUser) -> DomainClassEntity:
        """
        Retrieves a class and its student list.
        Args:
            class_id: The ID of the class to retrieve.
            user_requesting: The user (teacher or admin) requesting the class details.
        Returns:
            The DomainClassEntity with its students list populated.
        Raises:
            NotFoundException: If the class is not found.
            ForbiddenException: If the user is not authorized to view the class.
        """
        class_obj = await self.class_repo.get_by_id(class_id) # Repo impl should load students
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        # Authorization: Teacher who created it or an Admin can view.
        if user_requesting.role != UserRole.ADMIN and class_obj.created_by_teacher_id != user_requesting.user_id:
            raise ForbiddenException("You are not authorized to view this class.")

        # The ClassRepositoryImpl.get_by_id is expected to populate class_obj.students
        return class_obj

class ListClassesByTeacherUseCase:
    """Use case for listing classes associated with a teacher."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, teacher: DomainUser, page: int, size: int) -> Tuple[List[DomainClassEntity], int]:
        """
        Lists classes for the given teacher. Admins can also use this.
        Args:
            teacher: The teacher (or admin) for whom to list classes.
            page: Page number for pagination.
            size: Number of items per page.
        Returns:
            A tuple: list of DomainClassEntity and total count.
        Raises:
            ForbiddenException: If user is not a teacher or admin.
        """
        # An admin might be able to list classes for a specific teacher_id (passed as param),
        # or all classes. For now, if admin, they list their own (if they created any).
        # This use case is "by teacher_id" from the repo, so teacher.user_id is used.
        if teacher.role not in [UserRole.TEACHER, UserRole.ADMIN]:
            raise ForbiddenException("Only teachers or admins can list classes in this context.")

        return await self.class_repo.list_by_teacher_id(teacher.user_id, page, size)

class UpdateClassUseCase:
    """Use case for a teacher to update their class."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, class_id: UUID, update_data: ClassUpdateDTO, teacher: DomainUser) -> DomainClassEntity:
        """
        Updates a class.
        Args:
            class_id: ID of the class to update.
            update_data: DTO with fields to update.
            teacher: The authenticated teacher.
        Returns:
            The updated DomainClassEntity.
        Raises:
            NotFoundException, ForbiddenException, ApplicationException.
        """
        class_obj = await self.class_repo.get_by_id(class_id) # Fetch first to check ownership
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        if user_is_authorized_to_modify_class(class_obj, teacher):
            update_values = update_data.model_dump(exclude_unset=True)
            if "class_name" in update_values:
                class_obj.class_name = update_values["class_name"]
            if "grade_level" in update_values:
                class_obj.grade_level = update_values["grade_level"]
            class_obj.updated_at = datetime.now(timezone.utc) # Update timestamp

            updated_class = await self.class_repo.update(class_obj)
            if not updated_class: # Should be handled by repo if not found during update, but as safety
                 raise ApplicationException("Failed to update class, class may have been deleted.", status_code=500)
            # The repo's update might return students, or not. Ensure consistency.
            # For now, assume it returns the class without re-fetching all students.
            return updated_class
        else:
            raise ForbiddenException("You are not authorized to update this class.")


class DeleteClassUseCase:
    """Use case for a teacher to delete their class."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, class_id: UUID, teacher: DomainUser) -> bool:
        """Deletes a class. Returns True if successful."""
        class_obj = await self.class_repo.get_by_id(class_id) # Fetch for ownership check
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        if not user_is_authorized_to_modify_class(class_obj, teacher):
            raise ForbiddenException("You are not authorized to delete this class.")

        return await self.class_repo.delete(class_id)

class AddStudentToClassUseCase:
    """Use case for a teacher to add a student to their class."""
    def __init__(self, class_repo: ClassRepository, user_repo: UserRepository):
        self.class_repo = class_repo
        self.user_repo = user_repo # To validate student

    async def execute(self, class_id: UUID, student_id: UUID, teacher: DomainUser) -> bool:
        """Adds student to class. Returns True if successful."""
        class_obj = await self.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        if not user_is_authorized_to_modify_class(class_obj, teacher):
            raise ForbiddenException("You are not authorized to modify students in this class.")

        student_to_add = await self.user_repo.get_by_id(student_id)
        if not student_to_add:
            raise NotFoundException(resource_name="Student", resource_id=str(student_id))
        if student_to_add.role != UserRole.STUDENT:
            raise ApplicationException(f"User {student_id} is not a student and cannot be added to a class.", status_code=400)

        # Repository handles if student is already in class (idempotency)
        return await self.class_repo.add_student_to_class(class_id, student_id)

class RemoveStudentFromClassUseCase:
    """Use case for a teacher to remove a student from their class."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, class_id: UUID, student_id: UUID, teacher: DomainUser) -> bool:
        """Removes student from class. Returns True if successful (student was in class and removed)."""
        class_obj = await self.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        if not user_is_authorized_to_modify_class(class_obj, teacher):
            raise ForbiddenException("You are not authorized to modify students in this class.")

        # Existence of student ID itself is not checked here, only if the association exists.
        # UserRepo could be used if explicit student entity check is needed first.
        removed = await self.class_repo.remove_student_from_class(class_id, student_id)
        if not removed:
            # This means student was not in the class, or class_id/student_id was wrong at DB level.
            # Consider if this should be an error or just return False.
            # For now, if repo returns False, it means no change was made.
            # If NotFoundException for class/student is preferred, repo should raise it.
            pass # Or raise ApplicationException("Student not found in class or removal failed.", status_code=400)
        return removed

class ListStudentsInClassUseCase:
    """Use case for a teacher to list students in one of their classes."""
    def __init__(self, class_repo: ClassRepository):
        self.class_repo = class_repo

    async def execute(self, class_id: UUID, teacher: DomainUser) -> List[DomainUser]:
        class_obj = await self.class_repo.get_by_id(class_id) # Fetches class, also for auth check
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        if not user_is_authorized_to_modify_class(class_obj, teacher): # Modify implies view students too
            raise ForbiddenException("You are not authorized to view students in this class.")

        return await self.class_repo.get_students_in_class(class_id)

# --- Helper for authorization ---
def user_is_authorized_to_modify_class(class_obj: DomainClassEntity, user: DomainUser) -> bool:
    """Checks if a user (teacher/admin) is authorized to modify a class."""
    if user.role == UserRole.ADMIN:
        return True # Admins can modify any class
    if user.role == UserRole.TEACHER and class_obj.created_by_teacher_id == user.user_id:
        return True # Teachers can modify their own classes
    return False
