"""
Abstract repository interfaces for domain entities.

This package defines the contracts (interfaces) that repository
implementations in the infrastructure layer must adhere to.
These interfaces allow the domain and application layers to remain
independent of specific data storage technologies.
"""

from .user_repository import UserRepository
from .assessment_repository import AssessmentRepository

__all__ = [
    "UserRepository",
    "AssessmentRepository",
]
