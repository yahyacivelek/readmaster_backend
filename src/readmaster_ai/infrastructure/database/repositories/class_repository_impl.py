"""
Concrete implementation of the ClassRepository interface using SQLAlchemy.
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete, func, and_
from sqlalchemy.orm import selectinload, joinedload

from readmaster_ai.domain.entities.class_entity import ClassEntity as DomainClassEntity
from readmaster_ai.domain.entities.user import DomainUser # For student object
from readmaster_ai.domain.value_objects.common_enums import UserRole # For role conversion
from readmaster_ai.domain.repositories.class_repository import ClassRepository
from readmaster_ai.infrastructure.database.models import ClassModel, UserModel, StudentsClassesAssociation
from readmaster_ai.shared.exceptions import ApplicationException, NotFoundException


# Consider moving _user_model_to_domain to a shared converters module
# to avoid duplication with UserRepositoryImpl.
def _user_model_to_domain(model: UserModel) -> Optional[DomainUser]:
    """Converts a UserModel SQLAlchemy object to a DomainUser domain entity."""
    if not model:
        return None
    return DomainUser(
        user_id=model.user_id,
        email=model.email,
        password_hash=model.password_hash, # Be cautious with this
        first_name=model.first_name,
        last_name=model.last_name,
        role=UserRole(model.role), # Convert string from DB to Enum
        created_at=model.created_at,
        updated_at=model.updated_at,
        preferred_language=model.preferred_language
    )

def _class_model_to_domain(model: ClassModel, students: Optional[List[DomainUser]] = None) -> Optional[DomainClassEntity]:
    """Converts a ClassModel SQLAlchemy object to a DomainClassEntity domain entity."""
    if not model:
        return None

    domain_class = DomainClassEntity(
        class_id=model.class_id,
        class_name=model.class_name,
        grade_level=model.grade_level,
        created_by_teacher_id=model.created_by_teacher_id,
        created_at=model.created_at,
        updated_at=model.updated_at
    )
    # The ClassEntity domain model has a `students: List[Student]` attribute.
    # We initialize it here if students are provided (e.g. from eager loading).
    if students:
        # Ensure these are actually Student domain entities or compatible DomainUser
        domain_class.students = students
    else:
        # Ensure the attribute exists even if not loaded, as per domain entity definition
        domain_class.students = []

    return domain_class


class ClassRepositoryImpl(ClassRepository):
    """SQLAlchemy implementation of the class repository."""
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, class_obj: DomainClassEntity) -> DomainClassEntity:
        """Creates a new class in the database."""
        model = ClassModel(
            class_id=class_obj.class_id, # Application/use case generates ID
            class_name=class_obj.class_name,
            grade_level=class_obj.grade_level,
            created_by_teacher_id=class_obj.created_by_teacher_id,
            created_at=class_obj.created_at, # Domain entity sets these
            updated_at=class_obj.updated_at  # Domain entity sets these
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

        domain_entity = _class_model_to_domain(model)
        if not domain_entity: # Should not happen
            raise ApplicationException("Failed to map created ClassModel back to domain entity.", status_code=500)
        return domain_entity

    async def get_by_id(self, class_id: UUID) -> Optional[DomainClassEntity]:
        """Retrieves a class by its ID, optionally eager loading its students."""
        stmt = select(ClassModel).where(ClassModel.class_id == class_id)\
            .options(selectinload(ClassModel.students).joinedload(UserModel.classes_enrolled).noload('*')) # Example of complex loading
            # Simpler: .options(selectinload(ClassModel.students))
            # The above selectinload on ClassModel.students refers to the relationship defined in ClassModel.
            # This relationship should point to UserModel via the association table.

        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        domain_students = []
        if model.students: # model.students should be a list of UserModel instances
            for student_model in model.students:
                student_domain = _user_model_to_domain(student_model)
                if student_domain:
                    domain_students.append(student_domain)

        return _class_model_to_domain(model, students=domain_students)


    async def list_by_teacher_id(self, teacher_id: UUID, page: int = 1, size: int = 20) -> Tuple[List[DomainClassEntity], int]:
        """Lists classes created by a specific teacher with pagination."""
        offset = (page - 1) * size

        # Query for fetching the items
        query = select(ClassModel).where(ClassModel.created_by_teacher_id == teacher_id)
        # Query for counting total matching items
        count_query = select(func.count(ClassModel.class_id)).select_from(ClassModel)\
            .where(ClassModel.created_by_teacher_id == teacher_id)

        total_count_result = await self.session.execute(count_query)
        total_count = total_count_result.scalar_one()

        query = query.order_by(ClassModel.class_name).limit(size).offset(offset) # Order by name for consistency

        result = await self.session.execute(query)
        models = result.scalars().all()

        # For list view, students are not typically eager loaded for each class.
        domain_classes = [_class_model_to_domain(m) for m in models if _class_model_to_domain(m) is not None]
        return domain_classes, total_count

    async def update(self, class_obj: DomainClassEntity) -> Optional[DomainClassEntity]:
        """Updates an existing class."""
        if not class_obj.class_id:
            raise ValueError("Class ID must be provided for an update operation.")

        update_data = {
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "updated_at": class_obj.updated_at # Domain entity should have updated this
        }

        stmt = (
            sqlalchemy_update(ClassModel)
            .where(ClassModel.class_id == class_obj.class_id)
            .values(**update_data)
            .returning(ClassModel)
        )
        result = await self.session.execute(stmt)
        updated_model = result.scalar_one_or_none()

        if not updated_model:
            return None # Class not found or update failed to return model

        await self.session.flush()
        # Students are not updated via this method directly; use add/remove student methods.
        # If the updated_model needs its student list populated for the return value:
        # student_models = await self.get_students_in_class_models(updated_model.class_id) # Helper needed
        # domain_students = [_user_model_to_domain(s) for s in student_models if s]
        # return _class_model_to_domain(updated_model, students=domain_students)
        return _class_model_to_domain(updated_model) # Returns without students list populated by this update

    async def delete(self, class_id: UUID) -> bool:
        """Deletes a class by its ID."""
        # Database ON DELETE CASCADE on Students_Classes.class_id should handle disassociation.
        stmt = sqlalchemy_delete(ClassModel).where(ClassModel.class_id == class_id)
        result = await self.session.execute(stmt)
        # await self.session.flush() # Not strictly needed if autocommit or if rowcount is sufficient
        return result.rowcount > 0

    async def add_student_to_class(self, class_id: UUID, student_id: UUID) -> bool:
        """Adds a student to a class association."""
        # 1. Verify class exists
        class_model = await self.session.get(ClassModel, class_id)
        if not class_model:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        # 2. Verify student exists and is a student
        student_model = await self.session.get(UserModel, student_id)
        if not student_model:
            raise NotFoundException(resource_name="Student", resource_id=str(student_id))
        if UserRole(student_model.role) != UserRole.STUDENT: # Ensure UserRole(str_val) works
            raise ApplicationException(f"User {student_id} is not a student.", status_code=400)

        # 3. Check if association already exists (optional, DB constraint might handle)
        # This check can prevent trying to insert a duplicate if DB has unique constraint
        existing_assoc_stmt = select(StudentsClassesAssociation).where(
            StudentsClassesAssociation.c.class_id == class_id,
            StudentsClassesAssociation.c.student_id == student_id
        )
        existing_assoc_result = await self.session.execute(existing_assoc_stmt)
        if existing_assoc_result.scalar_one_or_none() is not None:
            return True # Already associated, consider this a success or idempotent

        # 4. Create association
        assoc_stmt = StudentsClassesAssociation.insert().values(
            class_id=class_id,
            student_id=student_id
            # joined_at has default in DB model
        )
        await self.session.execute(assoc_stmt)
        await self.session.flush() # Persist the change
        return True

    async def remove_student_from_class(self, class_id: UUID, student_id: UUID) -> bool:
        """Removes a student from a class association."""
        stmt = StudentsClassesAssociation.delete().where(
            StudentsClassesAssociation.c.class_id == class_id,
            StudentsClassesAssociation.c.student_id == student_id
        )
        result = await self.session.execute(stmt)
        # await self.session.flush() # Persist if needed before returning, but delete usually is.
        return result.rowcount > 0 # True if a row was deleted

    async def get_students_in_class(self, class_id: UUID) -> List[DomainUser]:
        """Retrieves a list of students (DomainUser) enrolled in a specific class."""
        # This query joins UserModel with StudentsClassesAssociation table
        stmt = (
            select(UserModel)
            .join(StudentsClassesAssociation, UserModel.user_id == StudentsClassesAssociation.c.student_id)
            .where(StudentsClassesAssociation.c.class_id == class_id)
            .where(UserModel.role == UserRole.STUDENT.value) # Filter by role string value for DB
            .order_by(UserModel.last_name, UserModel.first_name) # Optional ordering
        )
        result = await self.session.execute(stmt)
        student_models = result.scalars().all()

        domain_students = [_user_model_to_domain(s_model) for s_model in student_models if _user_model_to_domain(s_model) is not None]
        return domain_students
