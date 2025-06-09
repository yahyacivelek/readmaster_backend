"""
Data Transfer Objects (DTOs) for System Configuration management.
"""
from pydantic import BaseModel, Field
from typing import Any, Optional, List # List for potential future use in bulk operations
from datetime import datetime

class SystemConfigBaseDTO(BaseModel):
    """Base DTO for system configuration, containing common fields."""
    key: str = Field(..., min_length=1, max_length=255,
                     description="The unique key for the configuration setting (e.g., 'MAINTENANCE_MODE').")
    value: Any = Field(..., description="The value of the configuration setting. Can be string, number, boolean, list, or dict.")
    description: Optional[str] = Field(None, description="A human-readable description of what this configuration setting controls.")

class SystemConfigResponseDTO(SystemConfigBaseDTO):
    """DTO for representing a system configuration setting in API responses."""
    updated_at: datetime = Field(..., description="Timestamp of when this configuration was last updated.")

    class Config:
        from_attributes = True # For Pydantic v2 (replaces orm_mode)
        # For 'value: Any', Pydantic will try its best to serialize.
        # If 'value' contains complex custom objects not directly JSON-serializable,
        # custom encoders or `model_dump_json()` with custom encoders might be needed at API layer.
        # For standard JSON types (str, int, float, bool, list, dict), it's fine.

class SystemConfigUpdateDTO(BaseModel):
    """
    DTO for updating an existing system configuration setting.
    The 'key' is typically part of the URL path, not the request body for an update.
    """
    value: Any = Field(..., description="The new value for the configuration setting.")
    description: Optional[str] = Field(None, description="Optional new description for the setting. If None, existing description may be preserved or cleared based on use case logic.")

# Example of how a list of configs might be returned (not strictly paginated for now)
# class SystemConfigListResponseDTO(BaseModel):
# items: List[SystemConfigResponseDTO]
# total: int
