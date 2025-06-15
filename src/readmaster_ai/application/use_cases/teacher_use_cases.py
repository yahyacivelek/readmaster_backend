from uuid import UUID
from passlib.context import CryptContext

from readmaster_ai.application.dto.user_dtos import TeacherStudentCreateRequestDTO, UserResponseDTO, UserCreateDTO
from readmaster_ai.domain.repositories.user_repository import UserRepository # Corrected import
from readmaster_ai.domain.entities.user import DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole
from readmaster_ai.shared.exceptions import UnauthorizedException, ValidationException, ApplicationException

# Setup password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Placeholder for BaseUseCase if common functionality is needed later
class BaseUseCase:
    pass

class CreateStudentByTeacherUseCase(BaseUseCase):
    def __init__(self, user_repository: UserRepository): 
        self.user_repository = user_repository

    async def execute(self, teacher_id: UUID, student_data: TeacherStudentCreateRequestDTO) -> UserResponseDTO:
        teacher = await self.user_repository.get_by_id(teacher_id)
        if not teacher or teacher.role != UserRole.TEACHER:
            raise UnauthorizedException("User is not authorized to create student accounts or teacher not found.")

        # Check if email already exists
        existing_user = await self.user_repository.get_by_email(student_data.email)
        if existing_user:
            raise ValidationException(f"User with email {student_data.email} already exists.")

        hashed_password = pwd_context.hash(student_data.password)

        user_create_dto = UserCreateDTO(
            email=student_data.email,
            password=hashed_password, 
            first_name=student_data.first_name,
            last_name=student_data.last_name,
            preferred_language=student_data.preferred_language,
            role=UserRole.STUDENT 
        )

        created_student = await self.user_repository.create_user_with_role(user_create_dto)

        return UserResponseDTO.model_validate(created_student)
