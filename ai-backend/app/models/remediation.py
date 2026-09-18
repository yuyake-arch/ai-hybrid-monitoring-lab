from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RemediationAction(str, Enum):
    ENSURE_ZABBIX_AGENT_RUNNING = "ENSURE_ZABBIX_AGENT_RUNNING"


class RemediationRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RemediationStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RemediationProposal(BaseModel):
    remediation_id: str
    event_id: Optional[str] = None

    host: str
    target_host: str

    action_id: RemediationAction
    action_description: str

    risk: RemediationRisk
    status: RemediationStatus = RemediationStatus.PENDING_APPROVAL

    approval_required: bool = True

    ai_recommended_actions: list[str] = Field(default_factory=list)

