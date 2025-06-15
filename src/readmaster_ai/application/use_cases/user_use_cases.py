"""
Use cases related to User operations.
"""
from passlib.context import CryptContext
from uuid import uuid4

from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.value_objects.common_enums import UserRole # For role handling
from readmaster_ai.presentation.schemas.user_schemas import UserCreateRequest, TeacherStudentCreateRequestSchema # DTO for input
from readmaster_ai.shared.exceptions import ApplicationException # For custom error handling

# Setup password hashing context
# Schemes like bcrypt, argon2, scrypt are recommended.
# Using bcrypt as it's widely supported and secure.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class CreateUserUseCase:
    """
    Use case for creating a new user.
    Handles business logic like checking for existing email and hashing password.
    """
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, user_data: UserCreateRequest) -> DomainUser:
        """
        Executes the user creation process.

        Args:
            user_data: DTO containing data for the new user.

        Returns:
            The created DomainUser entity.

        Raises:
            ApplicationException: If email already exists or other validation fails.
        """
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            # Using a specific status code for this known condition
            raise ApplicationException("Email already registered.", status_code=409)

        hashed_password = pwd_context.hash(user_data.password)

        # Determine the role for the new user.
        # If user_data.role is provided and valid, use it. Otherwise, default to STUDENT.
        try:
            # Assuming user_data.role is a string like "student", "teacher", etc.
            user_role_value = user_data.role if hasattr(user_data, 'role') and user_data.role else UserRole.STUDENT.value
            user_role_enum = UserRole(user_role_value)
        except ValueError:
            # If the role string is invalid, default to STUDENT or raise an error
            # For now, defaulting to STUDENT. Consider raising ValidationException for bad role.
            user_role_enum = UserRole.STUDENT
            # raise ApplicationException(f"Invalid role specified: {user_data.role}", status_code=400)


        # Create the domain entity.
        # The DomainUser entity's __init__ should handle default created_at/updated_at.
        # user_id is generated here; alternatively, the repository/DB could generate it.
        new_user = DomainUser(
            user_id=uuid4(),
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_role_enum,
            preferred_language=user_data.preferred_language if hasattr(user_data, 'preferred_language') and user_data.preferred_language else 'en'
        )

        created_user = await self.user_repo.create(new_user)
        return created_user

from readmaster_ai.presentation.schemas.user_schemas import UserUpdateRequest # UserResponse not needed here
from datetime import datetime, timezone # For updated_at

class GetUserProfileUseCase:
    """
    Use case for retrieving a user's profile.
    Currently, it simply returns the user entity provided (e.g., by an auth dependency).
    Can be expanded to include more complex logic like fetching related data if needed.
    """
    def __init__(self, user_repo: UserRepository): # user_repo might be used for future enhancements
        self.user_repo = user_repo

    async def execute(self, current_user: DomainUser) -> DomainUser:
        """
        Executes the profile retrieval.
        Args:
            current_user: The currently authenticated user domain entity.
        Returns:
            The user domain entity (or a DTO representation).
        """
        # For now, the user object from get_current_user is considered fresh enough.
        # If there was a need to re-fetch or fetch additional related data:
        # return await self.user_repo.get_by_id(current_user.user_id)
        return current_user

class UpdateUserProfileUseCase:
    """
    Use case for updating a user's profile.
    Handles applying changes from a DTO to the user entity and persisting them.
    """
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, current_user: DomainUser, update_data: UserUpdateRequest) -> DomainUser:
        """
        Executes the profile update process.
        Args:
            current_user: The current user domain entity (to be updated).
            update_data: DTO containing the fields to update.
        Returns:
            The updated DomainUser entity.
        Raises:
            ApplicationException: If email is taken by another user or other validation fails.
        """
        # Apply updates from DTO to the domain user entity
        # Pydantic's model_dump(exclude_unset=True) ensures only provided fields are considered
        update_values = update_data.model_dump(exclude_unset=True)

        if "email" in update_values and update_values["email"] != current_user.email:
            # Check if the new email is already taken by another user
            existing_user_with_new_email = await self.user_repo.get_by_email(update_values["email"])
            if existing_user_with_new_email and existing_user_with_new_email.user_id != current_user.user_id:
                raise ApplicationException("This email is already registered by another user.", status_code=409)
            current_user.email = update_values["email"]

        # Update other fields if present in the DTO
        if "first_name" in update_values:
            current_user.first_name = update_values["first_name"]
        if "last_name" in update_values:
            current_user.last_name = update_values["last_name"]
        if "preferred_language" in update_values and update_values["preferred_language"] is not None: # Ensure not None
            current_user.preferred_language = update_values["preferred_language"]

        # Password updates should be handled by a separate, dedicated use case for security.
        # Role changes are typically administrative actions, not part of user profile update.

        # Explicitly set updated_at timestamp on the domain entity before saving
        current_user.updated_at = datetime.now(timezone.utc)

        updated_user_domain = await self.user_repo.update(current_user)
        return updated_user_domain


class CreateStudentByTeacherUseCase:
    """Use case for an authenticated teacher to create a new student account."""
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def execute(self, teacher_user: DomainUser, student_data: TeacherStudentCreateRequestSchema) -> DomainUser:
        """
        Executes the student creation process by a teacher.

        Args:
            teacher_user: The authenticated teacher (DomainUser).
            student_data: DTO containing data for the new student.

        Returns:
            The created student DomainUser entity.

        Raises:
            ForbiddenException: If the requesting user is not a teacher.
            ApplicationException: If email already exists or other validation fails.
        """
        if teacher_user.role != UserRole.TEACHER:
            # Note: The prompt used ForbiddenException, but it's not imported in this file.
            # Assuming ApplicationException with a 403 status code is appropriate or ForbiddenException should be imported.
            # For now, using ApplicationException as per existing style of this file for other errors.
            # If ForbiddenException is preferred, it needs to be imported:
            # from readmaster_ai.shared.exceptions import ForbiddenException
            raise ApplicationException("User is not authorized to create a student account.", status_code=403)


        existing_student_by_email = await self.user_repo.get_by_email(student_data.email)
        if existing_student_by_email:
            raise ApplicationException("A user with this email already exists.", status_code=409)

        hashed_password = pwd_context.hash(student_data.password)

        # student_data.role is fixed to "student" by TeacherStudentCreateRequestSchema
        new_student_user = DomainUser(
            user_id=uuid4(),
            email=student_data.email,
            password_hash=hashed_password,
            first_name=student_data.first_name,
            last_name=student_data.last_name,
            role=UserRole.STUDENT, # Role is fixed to STUDENT
            preferred_language=student_data.preferred_language if student_data.preferred_language else 'en',
            # class_id is not set here. Teacher adds student to class in a separate step/use case.
        )

        created_student = await self.user_repo.create(new_student_user)
        return created_student

# Future use cases:
# class ChangePasswordUseCase: ...
