from pydantic import BaseModel


class RemediationExecutionRequest(BaseModel):
    remediation_id: str
    event_id: str
    action_id: str
    target: str


class RemediationExecutionResponse(BaseModel):
    remediation_id: str
    action_id: str
    target: str
    status: str
    success: bool
    changed: bool
    return_code: int | None = None
    message: str
