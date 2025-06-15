from uuid import UUID

from readmaster_ai.application.dto.user_dtos import TeacherStudentCreateRequestDTO, UserResponseDTO, UserCreateDTO
from readmaster_ai.domain.repositories.user_repository import UserRepository # Corrected import
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.shared.exceptions import NotAuthorizedError, InvalidInputError, ApplicationException
from readmaster_ai.services.password_service import PasswordService # Assuming a service for hashing

# Placeholder for BaseUseCase if common functionality is needed later
class BaseUseCase:
    pass

class CreateStudentByTeacherUseCase(BaseUseCase):
    def __init__(self, user_repository: UserRepository, password_service: PasswordService): # Corrected type hint
        self.user_repository = user_repository
        self.password_service = password_service

    async def execute(self, teacher_id: UUID, student_data: TeacherStudentCreateRequestDTO) -> UserResponseDTO:
        teacher = await self.user_repository.get_by_id(teacher_id)
        if not teacher or teacher.role != UserRole.TEACHER:
            raise NotAuthorizedError("User is not authorized to create student accounts or teacher not found.")

        # Check if email already exists
        existing_user = await self.user_repository.get_by_email(student_data.email)
        if existing_user:
            raise InvalidInputError(f"User with email {student_data.email} already exists.")

        hashed_password = self.password_service.hash_password(student_data.password)

        user_create_dto = UserCreateDTO(
            email=student_data.email,
            password=hashed_password, # Store hashed password
            first_name=student_data.first_name,
            last_name=student_data.last_name,
            preferred_language=student_data.preferred_language,
            role=UserRole.STUDENT # Explicitly set role to student
        )

        # Assuming user_repository.create_user_with_role handles UserCreateDTO
        # This was added to IUserRepository in the previous subtask's plan
        created_student = await self.user_repository.create_user_with_role(user_create_dto)

        # Unlike parent-child, a teacher creating a student doesn't automatically link them
        # to the teacher directly or to a class. Class assignment is a separate step.

        return UserResponseDTO.model_validate(created_student)
