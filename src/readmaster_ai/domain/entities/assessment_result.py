from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

class AssessmentResult:
    result_id: UUID
    assessment_id: UUID # FK
    analysis_data: Optional[Dict[str, Any]] # JSONB in DB
    comprehension_score: Optional[float]
    created_at: datetime

    def __init__(self, assessment_id: UUID, # assessment_id is mandatory
                 result_id: Optional[UUID] = None,
                 analysis_data: Optional[Dict[str, Any]] = None,
                 comprehension_score: Optional[float] = None,
                 created_at: Optional[datetime] = None):
        self.result_id = result_id if result_id else uuid4()
        self.assessment_id = assessment_id
        self.analysis_data = analysis_data if analysis_data is not None else {} # Ensure it's a dict
        self.comprehension_score = comprehension_score
        self.created_at = created_at if created_at else datetime.utcnow()

    def generate_report(self) -> Dict[str, Any]:
        # Logic to generate a structured report from analysis_data and comprehension_score
        report = {
            "assessment_id": str(self.assessment_id),
            "result_id": str(self.result_id),
            "comprehension_score": self.comprehension_score,
            "analysis_details": self.analysis_data,
            "generated_at": self.created_at.isoformat()
        }
        print(f"Generated report for result {self.result_id}.")
        return report

    def calculate_metrics(self): # Potentially updates analysis_data or other fields
        # This method might be used if metrics are derived post-creation or need recalculation
        print(f"Calculating metrics for result {self.result_id}.")
        # e.g., self.analysis_data['words_per_minute'] = ...
        pass
