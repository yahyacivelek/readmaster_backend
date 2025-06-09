from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

if TYPE_CHECKING:
    from .student_quiz_answer import StudentQuizAnswer # Corrected name

class QuizQuestion:
    question_id: UUID
    reading_id: UUID # FK
    question_text: str
    options: Optional[Dict[str, Any]] # JSONB in DB, e.g., {"A": "Option A", "B": "Option B"} or list of dicts
    correct_option_id: str # e.g., "A"
    language: str
    # student_answers: List[StudentQuizAnswer] # Managed by repository
    added_by_admin_id: Optional[UUID] # From ERD
    created_at: datetime # From ERD

    def __init__(self, reading_id: UUID, question_text: str = "", correct_option_id: str = "", # Mandatory fields
                 question_id: Optional[UUID] = None,
                 options: Optional[Dict[str, Any]] = None, language: str = 'en',
                 added_by_admin_id: Optional[UUID] = None, created_at: Optional[datetime] = None):
        self.question_id = question_id if question_id else uuid4()
        self.reading_id = reading_id
        self.question_text = question_text
        self.options = options if options is not None else {} # Ensure it's a dict
        self.correct_option_id = correct_option_id
        self.language = language
        self.student_answers: List[StudentQuizAnswer] = [] # Initialize as empty list
        self.added_by_admin_id = added_by_admin_id
        self.created_at = created_at if created_at else datetime.utcnow()


    def validate_answer(self, selected_option_id: str) -> bool:
        is_correct = (selected_option_id == self.correct_option_id)
        print(f"Answer validation for question {self.question_id}: Selected '{selected_option_id}', Correct: '{self.correct_option_id}'. Result: {is_correct}")
        return is_correct
