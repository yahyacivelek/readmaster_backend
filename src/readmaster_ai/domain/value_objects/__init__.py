"""
Value Objects for the Readmaster.ai domain.

This package contains objects that represent descriptive aspects of the domain
that do not have a conceptual identity. They are typically immutable.
"""

from .common_enums import (
    UserRole,
    DifficultyLevel,
    AssessmentStatus,
    NotificationType
)
from .permissions import Permission, ROLE_PERMISSIONS

__all__ = [
    "UserRole",
    "DifficultyLevel",
    "AssessmentStatus",
    "NotificationType",
    "Permission",
    "ROLE_PERMISSIONS",
]
