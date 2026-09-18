from uuid import uuid4

from app.models.incident import IncidentRequest, IncidentAnalysis
from app.models.remediation import (
    RemediationAction,
    RemediationProposal,
    RemediationRisk,
)
from app.services.host_identity import resolve_host_identity


APPROVED_ACTIONS = {
    RemediationAction.ENSURE_ZABBIX_AGENT_RUNNING: {
        "description": "Ensure Zabbix Agent 2 service is running",
        "risk": RemediationRisk.LOW,
        "approval_required": True,
    }
}


def evaluate_remediation(
    incident: IncidentRequest,
    analysis: IncidentAnalysis,
) -> RemediationProposal | None:

    action_id = _match_incident_to_action(incident)

    if action_id is None:
        return None

    policy = APPROVED_ACTIONS[action_id]

    return RemediationProposal(
        remediation_id=f"rem-{uuid4()}",
        event_id=incident.event_id,
        host=incident.host,
        target_host=resolve_host_identity(incident.host),
        action_id=action_id,
        action_description=policy["description"],
        risk=policy["risk"],
        approval_required=policy["approval_required"],
        ai_recommended_actions=analysis.recommended_actions,
    )


def _match_incident_to_action(
    incident: IncidentRequest,
) -> RemediationAction | None:

    zabbix_agent_unavailable_prefix = (
        "Linux: Zabbix agent is not available"
    )

    if incident.trigger.startswith(
        zabbix_agent_unavailable_prefix
    ):
        return (
            RemediationAction
            .ENSURE_ZABBIX_AGENT_RUNNING
        )

    return None

