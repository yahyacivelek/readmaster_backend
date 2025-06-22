from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional
from uuid import UUID, uuid4
from datetime import datetime

if TYPE_CHECKING:
    from .student import Student
    from .teacher import Teacher

class ClassEntity: # Renamed from Class
    class_id: UUID
    class_name: str
    grade_level: Optional[str]
    created_by_teacher_id: UUID # FK
    # students: List[Student] # Managed by repository
    # teachers: List[Teacher] # Managed by repository
    created_at: datetime # From ERD
    updated_at: datetime # From ERD

    def __init__(self, class_name: str = "", created_by_teacher_id: Optional[UUID] = None, # Mandatory fields
                 class_id: Optional[UUID] = None, grade_level: Optional[str] = None,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.class_id = class_id if class_id else uuid4()
        self.class_name = class_name
        self.grade_level = grade_level
        # Ensure created_by_teacher_id is not None if it's truly mandatory for a class entity
        # For now, allowing Optional to match provided code, but consider implications.
        self.created_by_teacher_id = created_by_teacher_id if created_by_teacher_id else uuid4() # Or raise error if None
        self.students: List[Student] = [] # Initialize as empty list
        self.teachers: List[Teacher] = [] # Initialize as empty list
        self.created_at = created_at.replace(tzinfo=None) if created_at else datetime.utcnow().replace(tzinfo=None)
        self.updated_at = updated_at.replace(tzinfo=None) if updated_at else datetime.utcnow().replace(tzinfo=None)


    def add_student(self, student: Student):
        if student not in self.students:
            self.students.append(student)
            print(f"Student {student.email if student else 'N/A'} added to class {self.class_name}.")
            # This change would be persisted by an application service.
            self.updated_at = datetime.utcnow()
        else:
            print(f"Student {student.email if student else 'N/A'} already in class {self.class_name}.")

    def remove_student(self, student: Student):
        if student in self.students:
            self.students.remove(student)
            print(f"Student {student.email if student else 'N/A'} removed from class {self.class_name}.")
            self.updated_at = datetime.utcnow()
        else:
            print(f"Student {student.email if student else 'N/A'} not found in class {self.class_name}.")

    def assign_teacher(self, teacher: Teacher):
        if teacher not in self.teachers:
            self.teachers.append(teacher)
            print(f"Teacher {teacher.email if teacher else 'N/A'} assigned to class {self.class_name}.")
            self.updated_at = datetime.utcnow()
        else:
            print(f"Teacher {teacher.email if teacher else 'N/A'} already assigned to class {self.class_name}.")
