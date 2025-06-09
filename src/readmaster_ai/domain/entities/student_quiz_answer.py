from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4
from datetime import datetime

if TYPE_CHECKING: # Added to import QuizQuestion for type hint
    from .quiz_question import QuizQuestion

class StudentQuizAnswer:
    answer_id: UUID
    assessment_id: UUID # FK
    question_id: UUID # FK
    student_id: UUID # FK (denormalized in ERD)
    selected_option_id: str
    is_correct: Optional[bool]
    answered_at: datetime

    def __init__(self, assessment_id: UUID, question_id: UUID, student_id: UUID, selected_option_id: str = "", # Mandatory fields
                 answer_id: Optional[UUID] = None,
                 is_correct: Optional[bool] = None,
                 answered_at: Optional[datetime] = None):
        self.answer_id = answer_id if answer_id else uuid4()
        self.assessment_id = assessment_id
        self.question_id = question_id
        self.student_id = student_id
        self.selected_option_id = selected_option_id
        self.is_correct = is_correct # This might be set after validation against QuizQuestion.correct_option_id
        self.answered_at = answered_at if answered_at else datetime.utcnow()

    def mark_correctness(self, question: QuizQuestion): # Pass the QuizQuestion to check
        if question.question_id == self.question_id: # Ensure it's the correct question
            self.is_correct = question.validate_answer(self.selected_option_id)
        else:
            # Handle mismatch or raise error
            print(f"Error: Question ID mismatch when marking correctness for answer {self.answer_id}.")
