from pydantic import BaseModel
from typing import Optional, List

class StudentProgressSummaryDTO(BaseModel):
    student_id: str
    total_readings: int
    completed_readings: int
    average_reading_time: float
    last_reading_date: Optional[str]
    reading_level: str
    reading_speed: float
    accuracy_score: float
    comprehension_score: float
    recent_readings: List[str]

    class Config:
        from_attributes = True
