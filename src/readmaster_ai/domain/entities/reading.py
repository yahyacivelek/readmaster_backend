from __future__ import annotations
from typing import List, TYPE_CHECKING, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime

# Enums are now in value_objects
# from enum import Enum # No longer needed here
from readmaster_ai.domain.value_objects.common_enums import DifficultyLevel

if TYPE_CHECKING:
    from .quiz_question import QuizQuestion

class Reading:
    reading_id: UUID
    title: str
    content_text: Optional[str]
    content_image_url: Optional[str]
    age_category: Optional[str]
    difficulty: Optional[DifficultyLevel]
    language: str
    genre: Optional[str]
    # questions: List[QuizQuestion] # Managed by repository / lazy loaded
    added_by_admin_id: Optional[UUID] # From ERD
    created_at: datetime # From ERD
    updated_at: datetime # From ERD


    def __init__(self, reading_id: Optional[UUID] = None, title: str = "", # Added default for title
                 content_text: Optional[str] = None, content_image_url: Optional[str] = None,
                 age_category: Optional[str] = None, difficulty: Optional[DifficultyLevel] = None,
                 language: str = 'en', genre: Optional[str] = None,
                 added_by_admin_id: Optional[UUID] = None,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.reading_id = reading_id if reading_id else uuid4()
        self.title = title
        self.content_text = content_text
        self.content_image_url = content_image_url
        self.age_category = age_category
        self.difficulty = difficulty
        self.language = language
        self.genre = genre
        self.questions: List[QuizQuestion] = [] # Initialize as empty list
        self.added_by_admin_id = added_by_admin_id
        self.created_at = created_at if created_at else datetime.utcnow()
        self.updated_at = updated_at if updated_at else datetime.utcnow()


    def validate_content(self) -> bool:
        # Basic validation, can be expanded
        if not self.title:
            return False
        if not self.content_text and not self.content_image_url: # Must have some content
            return False
        print(f"Content validation for reading '{self.title}' passed.")
        return True

    def generate_quiz(self) -> List[QuizQuestion]: # Should be QuizQuestion entity
        # Logic to generate quiz questions based on the reading content
        # This might involve AI or a predefined set of rules.
        # For now, returns an empty list or placeholder.
        print(f"Generating quiz for reading '{self.title}'.")
        # Example:
        # from .quiz_question import QuizQuestion
        # q1 = QuizQuestion(reading_id=self.reading_id, question_text="What is the main idea?", options=[...], correct_option_id="A")
        # self.questions.append(q1)
        return [] # Placeholder
