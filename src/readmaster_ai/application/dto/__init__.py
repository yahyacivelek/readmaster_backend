"""
Data Transfer Objects (DTOs) for Readmaster.ai.

This package contains Pydantic models used for transferring data
between layers of the application, particularly between the
presentation layer (API request/response models) and the
application layer (use case inputs/outputs).
"""

from .assessment_dto import CreateAssessmentDTO

__all__ = [
    "CreateAssessmentDTO",
]
