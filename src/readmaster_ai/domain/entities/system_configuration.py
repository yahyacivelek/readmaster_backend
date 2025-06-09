"""
Domain Entity for System Configuration settings.
"""
from typing import Any, Optional
from datetime import datetime, timezone # Added timezone

class SystemConfiguration:
    """
    Represents a system configuration setting.
    The 'key' is the unique identifier for the configuration.
    'value' can be of various types (str, int, bool, dict, list)
    and will be stored as JSONB in the database.
    """
    key: str
    value: Any
    description: Optional[str]
    updated_at: datetime

    def __init__(self,
                 key: str,
                 value: Any,
                 description: Optional[str] = None,
                 updated_at: Optional[datetime] = None):
        if not key:
            raise ValueError("SystemConfiguration key cannot be empty.")

        self.key = key
        self.value = value
        self.description = description
        # Ensure updated_at is always set, defaulting to now if not provided.
        # Use timezone-aware datetime objects.
        self.updated_at = updated_at if updated_at else datetime.now(timezone.utc)

    def update_value(self, new_value: Any, new_description: Optional[str] = None):
        """Updates the value and optionally the description of the configuration."""
        self.value = new_value
        if new_description is not None: # Allow clearing description by passing ""
            self.description = new_description
        self.updated_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<SystemConfiguration(key='{self.key}', value={self.value}, updated_at='{self.updated_at.isoformat()}')>"
