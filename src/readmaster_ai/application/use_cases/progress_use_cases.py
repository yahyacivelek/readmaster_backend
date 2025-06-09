"""
Use cases related to monitoring student and class progress.
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

# Domain Entities and Repositories
from readmaster_ai.domain.entities.user import User as DomainUser
from readmaster_ai.domain.value_objects.common_enums import UserRole, AssessmentStatus # Enums
from readmaster_ai.domain.repositories.user_repository import UserRepository
from readmaster_ai.domain.repositories.class_repository import ClassRepository
from readmaster_ai.domain.repositories.assessment_repository import AssessmentRepository
from readmaster_ai.domain.repositories.assessment_result_repository import AssessmentResultRepository
from readmaster_ai.domain.repositories.reading_repository import ReadingRepository

# Application DTOs
from readmaster_ai.application.dto.progress_dtos import (
    StudentProgressSummaryDTO, ClassProgressReportDTO, AssessmentAttemptSummaryDTO
)
from readmaster_ai.application.dto.user_dtos import UserResponseDTO

# Shared Exceptions
from readmaster_ai.shared.exceptions import NotFoundException, ForbiddenException, ApplicationException

# Configuration for summary display
MAX_RECENT_ASSESSMENTS_SUMMARY = 3

class GetStudentProgressSummaryUseCase:
    """
    Use case to compile a progress summary for a single student.
    """
    def __init__(self,
                 user_repo: UserRepository,
                 assessment_repo: AssessmentRepository,
                 result_repo: AssessmentResultRepository,
                 reading_repo: ReadingRepository):
        self.user_repo = user_repo
        self.assessment_repo = assessment_repo
        self.result_repo = result_repo
        self.reading_repo = reading_repo

    async def _compile_summary_for_student(self, student_user: DomainUser) -> StudentProgressSummaryDTO:
        """Helper to compile progress summary data for a given student domain object."""
        assessments = await self.assessment_repo.list_by_student_ids([student_user.user_id])
        assessment_ids = [a.assessment_id for a in assessments if a] # Ensure 'a' is not None

        results_map: Dict[UUID, Any] = {} # Stores full AssessmentResult domain objects
        if assessment_ids:
            assessment_results_domain = await self.result_repo.list_by_assessment_ids(assessment_ids)
            results_map = {res.assessment_id: res for res in assessment_results_domain if res}

        completed_assessments = [a for a in assessments if a and a.status == AssessmentStatus.COMPLETED]

        total_assigned = len(assessments)
        total_completed = len(completed_assessments)

        comp_scores = [
            results_map[a.assessment_id].comprehension_score
            for a in completed_assessments
            if a.assessment_id in results_map and results_map[a.assessment_id].comprehension_score is not None
        ]
        avg_comp_score = sum(comp_scores) / len(comp_scores) if comp_scores else None

        fluency_scores = []
        for a in completed_assessments:
            res = results_map.get(a.assessment_id)
            if res and res.analysis_data and isinstance(res.analysis_data.get("fluency_score"), (int, float)):
                fluency_scores.append(res.analysis_data["fluency_score"])
        avg_fluency_score = sum(fluency_scores) / len(fluency_scores) if fluency_scores else None

        recent_assessment_summaries: List[AssessmentAttemptSummaryDTO] = []
        sorted_assessments = sorted(assessments, key=lambda a: a.assessment_date if a else datetime.min, reverse=True)

        reading_titles_map: Dict[UUID, str] = {}

        for assessment in sorted_assessments[:MAX_RECENT_ASSESSMENTS_SUMMARY]:
            if not assessment: continue # Skip if None

            reading_title = "N/A"
            if assessment.reading_id not in reading_titles_map:
                reading = await self.reading_repo.get_by_id(assessment.reading_id)
                reading_titles_map[assessment.reading_id] = reading.title if reading else "N/A"
            reading_title = reading_titles_map[assessment.reading_id]

            res_data = results_map.get(assessment.assessment_id)
            comp_score_attempt = res_data.comprehension_score if res_data else None
            fluency_s_attempt = None
            if res_data and res_data.analysis_data and isinstance(res_data.analysis_data.get("fluency_score"), (int, float)):
                 fluency_s_attempt = res_data.analysis_data["fluency_score"]

            recent_assessment_summaries.append(AssessmentAttemptSummaryDTO(
                assessment_id=assessment.assessment_id,
                reading_title=reading_title,
                assessment_date=assessment.assessment_date,
                status=assessment.status.value, # Enum to string value
                comprehension_score=comp_score_attempt,
                fluency_score=fluency_s_attempt
            ))

        return StudentProgressSummaryDTO(
            student_info=UserResponseDTO.model_validate(student_user), # Pydantic v2
            total_assessments_assigned=total_assigned,
            total_assessments_completed=total_completed,
            average_comprehension_score=round(avg_comp_score, 2) if avg_comp_score is not None else None,
            average_fluency_score=round(avg_fluency_score, 2) if avg_fluency_score is not None else None,
            recent_assessments=recent_assessment_summaries
        )

    async def execute(self, student_id: UUID, requesting_user: DomainUser) -> StudentProgressSummaryDTO:
        """
        Executes the student progress summary retrieval.
        Args:
            student_id: The ID of the student whose progress is being requested.
            requesting_user: The user making the request (for authorization).
        Returns:
            A StudentProgressSummaryDTO.
        """
        student_user = await self.user_repo.get_by_id(student_id)
        if not student_user or student_user.role != UserRole.STUDENT:
            raise NotFoundException(resource_name="Student", resource_id=str(student_id))

        # Authorization Logic:
        # A teacher can view progress of students in their classes.
        # An admin can view progress of any student.
        # A student can view their own progress (handled by a different endpoint/use case typically).
        # A parent can view progress of their children.
        if requesting_user.role == UserRole.TEACHER:
            # Need ClassRepository to check if student is in one of teacher's classes.
            # This is a placeholder for a more robust authorization check.
            # For now, this use case focuses on data compilation. Auth is simplified.
            # In a real app, an AuthService or permissions check would be better.
            # Example: if not await auth_service.can_teacher_view_student(teacher, student_id):
            #    raise ForbiddenException("Teacher not authorized for this student's progress.")
            pass # Assuming for now teacher has access if they query.
        elif requesting_user.role != UserRole.ADMIN: # If not teacher and not admin
             raise ForbiddenException("User not authorized to view this student's progress.")

        return await self._compile_summary_for_student(student_user)


class GetClassProgressReportUseCase:
    """
    Use case to compile a progress report for an entire class,
    aggregating summaries for each student in the class.
    """
    def __init__(self,
                 class_repo: ClassRepository,
                 student_progress_uc: GetStudentProgressSummaryUseCase, # Injected
                 user_repo: UserRepository): # For fetching teacher info
        self.class_repo = class_repo
        self.student_progress_uc = student_progress_uc
        self.user_repo = user_repo

    async def execute(self, class_id: UUID, requesting_teacher: DomainUser) -> ClassProgressReportDTO:
        """
        Executes the class progress report generation.
        Args:
            class_id: The ID of the class for the report.
            requesting_teacher: The teacher making the request.
        Returns:
            A ClassProgressReportDTO.
        """
        class_obj = await self.class_repo.get_by_id(class_id) # Repo's get_by_id loads students
        if not class_obj:
            raise NotFoundException(resource_name="Class", resource_id=str(class_id))

        # Authorization: Teacher must own the class or be an Admin
        if requesting_teacher.role != UserRole.ADMIN and class_obj.created_by_teacher_id != requesting_teacher.user_id:
            raise ForbiddenException("Teacher not authorized to view this class report.")

        student_summaries: List[StudentProgressSummaryDTO] = []
        if class_obj.students:
            for student_domain_obj in class_obj.students:
                if student_domain_obj: # Ensure student object is not None
                    # Pass requesting_teacher for context, though _compile_summary_for_student doesn't use it for auth
                    summary = await self.student_progress_uc._compile_summary_for_student(student_domain_obj)
                    student_summaries.append(summary)

        # Calculate overall class averages from the collected student summaries
        class_comp_scores = [s.average_comprehension_score for s in student_summaries if s.average_comprehension_score is not None]
        class_avg_comp = sum(class_comp_scores) / len(class_comp_scores) if class_comp_scores else None

        class_fluency_scores = [s.average_fluency_score for s in student_summaries if s.average_fluency_score is not None]
        class_avg_fluency = sum(class_fluency_scores) / len(class_fluency_scores) if class_fluency_scores else None

        teacher_info_dto = None
        if class_obj.created_by_teacher_id:
            class_teacher_domain = await self.user_repo.get_by_id(class_obj.created_by_teacher_id)
            if class_teacher_domain:
                teacher_info_dto = UserResponseDTO.model_validate(class_teacher_domain) # Pydantic v2

        return ClassProgressReportDTO(
            class_id=class_obj.class_id,
            class_name=class_obj.class_name,
            teacher_info=teacher_info_dto,
            student_progress_summaries=student_summaries,
            class_average_comprehension=round(class_avg_comp, 2) if class_avg_comp is not None else None,
            class_average_fluency=round(class_avg_fluency, 2) if class_avg_fluency is not None else None,
        )
