from fastapi import FastAPI, HTTPException
from app.config.targets import ALLOWED_TARGETS
from fastapi import Depends, FastAPI, HTTPException

from app.security.auth import verify_service_token

from app.models.remediation import (
    RemediationExecutionRequest,
    RemediationExecutionResponse,
)
from app.services.action_registry import get_action_policy
from app.services.ansible_executor import (
    execute_playbook,
)
from app.services.execution_logger import (
    log_execution_event,
)


app = FastAPI(
    title="Remediation Execution API",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "remediation-api",
    }


@app.post(
    "/remediation/execute",
    response_model=RemediationExecutionResponse,
    dependencies=[
        Depends(verify_service_token)
    ],
)
def execute_remediation(
    request: RemediationExecutionRequest,
):

    policy = get_action_policy(
        request.action_id
    )

    if policy is None:
        raise HTTPException(
            status_code=403,
            detail="Action is not allowlisted",
        )

    if request.target not in ALLOWED_TARGETS:
        raise HTTPException(
            status_code=403,
            detail="Target is not allowlisted",
        )

    result = execute_playbook(
        playbook_name=policy["playbook"],
        target=request.target,
    )

    execution_status = (
        "SUCCESS"
        if result["success"]
        else "FAILED"
    )

    log_execution_event(
        remediation_id=request.remediation_id,
        event_id=request.event_id,
        action_id=request.action_id,
        target=request.target,
        status=execution_status,
        success=result["success"],
        changed=result["changed"],
        return_code=result["return_code"],
        message=result["message"],
    )

    if not result["success"]:
        return RemediationExecutionResponse(
            remediation_id=request.remediation_id,
            action_id=request.action_id,
            target=request.target,
            status="FAILED",
            success=False,
            changed=result["changed"],
            return_code=result["return_code"],
            message=result["message"],
        )

    return RemediationExecutionResponse(
        remediation_id=request.remediation_id,
        action_id=request.action_id,
        target=request.target,
        status="SUCCESS",
        success=True,
        changed=result["changed"],
        return_code=result["return_code"],
        message=result["message"],
    )

