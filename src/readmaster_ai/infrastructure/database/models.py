import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Enum as SQLAlchemyEnum, DateTime, ForeignKey, Integer, Boolean, Float, Date, Table # Removed JSONB
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB # Added JSONB here
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Enum definitions based on document (assuming these will be created in DB via Alembic or manually)
# These are string representations for SQLAlchemy Enum, actual CREATE TYPE happens in SQL/Alembic
# For `User.role`
USER_ROLE_ENUM_VALUES = ['student', 'parent', 'teacher', 'admin']
# For `Assessments.status`
ASSESSMENT_STATUS_ENUM_VALUES = ['pending_audio', 'processing', 'completed', 'error']
# For `Readings.difficulty_level`
DIFFICULTY_LEVEL_ENUM_VALUES = ['beginner', 'intermediate', 'advanced'] # Assuming some values
# For `Notifications.type`
NOTIFICATION_TYPE_ENUM_VALUES = ['assignment', 'result', 'feedback', 'system'] # Assuming some values


# Association Tables (for many-to-many relationships)

StudentsClassesAssociation = Table(
    'Students_Classes', Base.metadata,
    Column('student_id', PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), primary_key=True),
    Column('class_id', PG_UUID(as_uuid=True), ForeignKey('Classes.class_id'), primary_key=True),
    Column('joined_at', DateTime(timezone=True), default=datetime.now(timezone.utc))
)

ParentsStudentsAssociation = Table(
    'Parents_Students', Base.metadata,
    Column('parent_id', PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), primary_key=True),
    Column('student_id', PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), primary_key=True),
    Column('relationship_type', String),
    Column('linked_at', DateTime(timezone=True), default=datetime.now(timezone.utc))
)

TeachersClassesAssociation = Table(
    'Teachers_Classes', Base.metadata,
    Column('teacher_id', PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), primary_key=True),
    Column('class_id', PG_UUID(as_uuid=True), ForeignKey('Classes.class_id'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=datetime.now(timezone.utc))
)


class UserModel(Base):
    __tablename__ = "Users"
    user_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(SQLAlchemyEnum(*USER_ROLE_ENUM_VALUES, name='user_role_enum_sqlalchemy', create_type=False), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    preferred_language = Column(String, default='en')

    # Relationships defined via association tables for roles
    # Student role specific:
    classes_enrolled = relationship("ClassModel", secondary=StudentsClassesAssociation, back_populates="students")
    # Parent role specific:
    children = relationship("UserModel", # Self-referential for parent-student
                            secondary=ParentsStudentsAssociation,
                            primaryjoin=user_id == ParentsStudentsAssociation.c.parent_id,
                            secondaryjoin=user_id == ParentsStudentsAssociation.c.student_id,
                            backref="parents") # 'parents' backref might need adjustment if student can have multiple parents
    # Teacher role specific:
    classes_taught = relationship("ClassModel", secondary=TeachersClassesAssociation, back_populates="teachers")

    # Common relationships
    assessments_taken = relationship("AssessmentModel", foreign_keys="[AssessmentModel.student_id]", back_populates="student", lazy="dynamic")
    assessments_assigned = relationship("AssessmentModel", foreign_keys="[AssessmentModel.assigned_by_teacher_id]", back_populates="assigning_teacher", lazy="dynamic")
    readings_added = relationship("ReadingModel", back_populates="added_by_admin", lazy="dynamic") # Corrected: was added_by_admin_id
    quiz_questions_created = relationship("QuizQuestionModel", back_populates="added_by_admin", lazy="dynamic") # Corrected: was added_by_admin_id
    student_quiz_answers = relationship("StudentQuizAnswerModel", back_populates="student", lazy="dynamic")
    progress_tracking_entries = relationship("ProgressTrackingModel", back_populates="student", lazy="dynamic")
    notifications = relationship("NotificationModel", back_populates="user", lazy="dynamic")

    # For teacher creating classes
    classes_created = relationship("ClassModel", back_populates="creator_teacher")


class ClassModel(Base):
    __tablename__ = "Classes"
    class_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_name = Column(String, nullable=False)
    grade_level = Column(String)
    created_by_teacher_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id'))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    creator_teacher = relationship("UserModel", foreign_keys=[created_by_teacher_id], back_populates="classes_created")
    students = relationship("UserModel", secondary=StudentsClassesAssociation, back_populates="classes_enrolled")
    teachers = relationship("UserModel", secondary=TeachersClassesAssociation, back_populates="classes_taught")


class ReadingModel(Base):
    __tablename__ = "Readings"
    reading_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content_text = Column(Text)
    content_image_url = Column(String)
    age_category = Column(String) # e.g., "6-8 years", "9-12 years"
    difficulty_level = Column(SQLAlchemyEnum(*DIFFICULTY_LEVEL_ENUM_VALUES, name='difficulty_level_enum_sqlalchemy', create_type=False))
    language = Column(String, default='en')
    genre = Column(String)
    added_by_admin_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id')) # Assuming only Admins add readings as per ERD
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    added_by_admin = relationship("UserModel", foreign_keys=[added_by_admin_id], back_populates="readings_added") # Corrected foreign_keys
    assessments = relationship("AssessmentModel", back_populates="reading", lazy="dynamic")
    quiz_questions = relationship("QuizQuestionModel", back_populates="reading", lazy="dynamic")


class AssessmentModel(Base):
    __tablename__ = "Assessments"
    assessment_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), nullable=False, index=True)
    reading_id = Column(PG_UUID(as_uuid=True), ForeignKey('Readings.reading_id'), nullable=False)
    assigned_by_teacher_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), nullable=True) # Nullable if student picks own
    audio_file_url = Column(String)
    audio_duration_seconds = Column(Integer)
    status = Column(SQLAlchemyEnum(*ASSESSMENT_STATUS_ENUM_VALUES, name='assessment_status_enum_sqlalchemy', create_type=False), nullable=False, default='pending_audio', index=True)
    assessment_date = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    ai_raw_speech_to_text = Column(Text)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    student = relationship("UserModel", foreign_keys=[student_id], back_populates="assessments_taken")
    reading = relationship("ReadingModel", back_populates="assessments")
    assigning_teacher = relationship("UserModel", foreign_keys=[assigned_by_teacher_id], back_populates="assessments_assigned")

    result = relationship("AssessmentResultModel", back_populates="assessment", uselist=False, cascade="all, delete-orphan") # One-to-one
    quiz_answers = relationship("StudentQuizAnswerModel", back_populates="assessment", cascade="all, delete-orphan", lazy="dynamic")


class AssessmentResultModel(Base):
    __tablename__ = "AssessmentResults"
    result_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(PG_UUID(as_uuid=True), ForeignKey('Assessments.assessment_id'), nullable=False, unique=True) # Unique for 1-to-1
    analysis_data = Column(JSONB) # For fluency, pronunciation details
    comprehension_score = Column(Float) # Derived from quiz answers
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    assessment = relationship("AssessmentModel", back_populates="result")


class QuizQuestionModel(Base):
    __tablename__ = "QuizQuestions"
    question_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reading_id = Column(PG_UUID(as_uuid=True), ForeignKey('Readings.reading_id'), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSONB) # e.g., [{"id": "A", "text": "..."}, {"id": "B", "text": "..."}]
    correct_option_id = Column(String, nullable=False)
    language = Column(String, default='en')
    added_by_admin_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id')) # Assuming Admin role
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    reading = relationship("ReadingModel", back_populates="quiz_questions")
    added_by_admin = relationship("UserModel", foreign_keys=[added_by_admin_id], back_populates="quiz_questions_created") # Corrected foreign_keys
    student_answers = relationship("StudentQuizAnswerModel", back_populates="question", lazy="dynamic")


class StudentQuizAnswerModel(Base):
    __tablename__ = "StudentQuizAnswers"
    answer_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id = Column(PG_UUID(as_uuid=True), ForeignKey('Assessments.assessment_id'), nullable=False)
    question_id = Column(PG_UUID(as_uuid=True), ForeignKey('QuizQuestions.question_id'), nullable=False)
    student_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), nullable=False) # Denormalized for easier querying
    selected_option_id = Column(String, nullable=False)
    is_correct = Column(Boolean)
    answered_at = Column(DateTime, default=datetime.now(timezone.utc))

    assessment = relationship("AssessmentModel", back_populates="quiz_answers")
    question = relationship("QuizQuestionModel", back_populates="student_answers")
    student = relationship("UserModel", back_populates="student_quiz_answers")


class ProgressTrackingModel(Base):
    __tablename__ = "ProgressTracking"
    progress_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), nullable=False, index=True)
    metric_type = Column(String, nullable=False) # e.g., "words_per_minute", "accuracy_score", "comprehension_avg"
    value = Column(Float, nullable=False)
    period_start_date = Column(Date)
    period_end_date = Column(Date)
    last_calculated_at = Column(DateTime, default=datetime.now(timezone.utc))

    student = relationship("UserModel", back_populates="progress_tracking_entries")


class NotificationModel(Base):
    __tablename__ = "Notifications"
    notification_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('Users.user_id'), nullable=False, index=True)
    type = Column(SQLAlchemyEnum(*NOTIFICATION_TYPE_ENUM_VALUES, name='notification_type_enum_sqlalchemy', create_type=False), nullable=False)
    message = Column(Text, nullable=False)
    related_entity_id = Column(PG_UUID(as_uuid=True), nullable=True) # e.g., assessment_id, class_id
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("UserModel", back_populates="notifications")


class SystemConfigurationModel(Base):
    __tablename__ = "SystemConfigurations"

    key = Column(String, primary_key=True, index=True) # e.g., "DEFAULT_READING_LANGUAGE", "MAX_ASSESSMENTS_PER_DAY"
    value = Column(JSONB, nullable=False) # Store various types of config values (string, number, bool, dict, list)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SystemConfigurationModel(key='{self.key}', value='{self.value}')>"
