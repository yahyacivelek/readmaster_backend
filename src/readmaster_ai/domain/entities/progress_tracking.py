from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4
from datetime import datetime, date # Ensure date is imported

class ProgressTracking:
    progress_id: UUID
    student_id: UUID # FK
    metric_type: str # e.g., "words_per_minute", "accuracy_score"
    value: float
    period_start_date: Optional[date]
    period_end_date: Optional[date]
    last_calculated_at: datetime

    def __init__(self, student_id: UUID, metric_type: str = "", value: float = 0.0, # Mandatory fields
                 progress_id: Optional[UUID] = None,
                 period_start_date: Optional[date] = None,
                 period_end_date: Optional[date] = None,
                 last_calculated_at: Optional[datetime] = None):
        self.progress_id = progress_id if progress_id else uuid4()
        self.student_id = student_id
        self.metric_type = metric_type
        self.value = value
        self.period_start_date = period_start_date
        self.period_end_date = period_end_date
        self.last_calculated_at = last_calculated_at if last_calculated_at else datetime.utcnow()
