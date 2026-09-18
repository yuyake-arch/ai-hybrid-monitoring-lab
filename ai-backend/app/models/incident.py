from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    event_id: Optional[str] = None
    host: str
    trigger: str
    severity: str
    message: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    duration_minutes: Optional[int] = None
    timestamp: Optional[datetime] = None


class IncidentAnalysis(BaseModel):
    host: str
    severity: str
    summary: str
    observed_evidence: list[str] = Field(default_factory=list)
    possible_causes: list[str]
    recommended_actions: list[str]
    confidence: str
    analysis_source: str

class IncidentProcessingAck(BaseModel):
    event_id: str
    status: str = "processing"
    message: str = "Incident is already being processed"


