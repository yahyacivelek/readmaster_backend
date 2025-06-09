from pydantic import BaseModel, Field
from typing import List, TypeVar, Generic

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    # Optional: Add pages, has_next, has_prev
    # pages: Optional[int] = None
    # has_next: Optional[bool] = None
    # has_prev: Optional[bool] = None
