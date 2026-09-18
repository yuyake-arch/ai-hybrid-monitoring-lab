from fastapi import APIRouter, Depends, HTTPException

from app.security.operator_auth import (
    get_operator_identity,
)

from app.models.remediation import (
    RemediationStatus,
)

from app.services.remediation_client import (
    execute_remediation,
)

from app.services.remediation_repository import (
    get_remediation_by_id,
    get_remediations,
    update_remediation_status,
    mark_remediation_executing,
    complete_remediation_execution,
)

from app.services.structured_logger import (
    log_remediation_event,
    log_remediation_execution_completed,
)


router = APIRouter(
    prefix="/remediation",
    tags=["Remediation"],
)


@router.get("/")
def list_remediations():
    return get_remediations()


@router.get("/{remediation_id}")
def get_remediation(remediation_id: str):

    remediation = get_remediation_by_id(
        remediation_id
    )

    if remediation is None:
        raise HTTPException(
            status_code=404,
            detail="Remediation not found",
        )

    return remediation


@router.post("/{remediation_id}/approve")
def approve_remediation(
    remediation_id: str,
    operator: str = Depends(
        get_operator_identity
    ),
):

    remediation = get_remediation_by_id(
        remediation_id
    )

    if remediation is None:
        raise HTTPException(
            status_code=404,
            detail="Remediation not found",
        )

    updated = update_remediation_status(
        remediation_id,
        RemediationStatus.APPROVED,
        decision_by=operator,
    )

    if not updated:
        raise HTTPException(
            status_code=409,
            detail="Remediation is not pending approval",
        )

    # Status update succeeded 
    log_remediation_event(
        level="INFO",
        event="remediation_approved",
        remediation_id=remediation_id,
        incident_id=remediation["event_id"],
        host=remediation["host"],
        action_id=remediation["action_id"],
        status=RemediationStatus.APPROVED.value,
        actor=operator,
    )

    return get_remediation_by_id(
        remediation_id
    )


@router.post("/{remediation_id}/reject")
def reject_remediation(
    remediation_id: str,
    operator: str = Depends(
        get_operator_identity
    ),
):

    remediation = get_remediation_by_id(
        remediation_id
    )

    if remediation is None:
        raise HTTPException(
            status_code=404,
            detail="Remediation not found",
        )

    updated = update_remediation_status(
        remediation_id,
        RemediationStatus.REJECTED,
        decision_by=operator,
    )

    if not updated:
        raise HTTPException(
            status_code=409,
            detail="Remediation is not pending approval",
        )


    log_remediation_event(
        level="INFO",
        event="remediation_rejected",
        remediation_id=remediation_id,
        incident_id=remediation["event_id"],
        host=remediation["host"],
        action_id=remediation["action_id"],
        status=RemediationStatus.REJECTED.value,
        actor=operator,
    )
    return get_remediation_by_id(
        remediation_id
    )

@router.post("/{remediation_id}/execute")
def execute_approved_remediation(
    remediation_id: str,
    operator: str = Depends(
        get_operator_identity
    ),
):
    remediation = get_remediation_by_id(
        remediation_id
    )

    if remediation is None:
        raise HTTPException(
            status_code=404,
            detail="Remediation not found",
        )

    if (
        remediation["status"]
        != RemediationStatus.APPROVED.value
    ):
        raise HTTPException(
            status_code=409,
            detail="Remediation is not approved for execution",
        )

    marked = mark_remediation_executing(
        remediation_id,
        executed_by=operator,
    )

    if not marked:
        raise HTTPException(
            status_code=409,
            detail="Remediation could not enter EXECUTING state",
        )

    result = execute_remediation(
        remediation_id=remediation_id,
        event_id=remediation["event_id"],
        action_id=remediation["action_id"],
        target=remediation["target_host"],
    )

    success = bool(
        result.get("success", False)
    )

    changed = bool(
	result.get("changed", False)
    )

    return_code = result.get(
	"return_code"
    )

    result_summary = (
        result.get("message")
        or result.get("error")
        or "No execution summary returned"
    )

    completed = complete_remediation_execution(
        remediation_id=remediation_id,
        success=success,
        changed=changed,
        return_code=return_code,
        result_summary=result_summary,
        execution_output=str(result),
    )

    if not completed:
        raise HTTPException(
            status_code=500,
            detail="Failed to persist remediation execution result",
        )

    final_status = (
        RemediationStatus.SUCCESS
        if success
        else RemediationStatus.FAILED
    )

    log_remediation_execution_completed(
        level="INFO" if success else "ERROR",
        remediation_id=remediation_id,
        incident_id=remediation["event_id"],
        host=remediation["host"],
        target_host=remediation["target_host"],
        action_id=remediation["action_id"],
        status=final_status.value,
        actor=operator,
        success=success,
        changed=changed,
        return_code=return_code,
    )

    return get_remediation_by_id(
        remediation_id
    )
