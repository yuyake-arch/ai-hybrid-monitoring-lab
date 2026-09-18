import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.incident import (
    IncidentRequest,
    IncidentAnalysis,
    IncidentProcessingAck,
)
from app.services.incident_analyzer import analyze_incident
from app.services.incident_repository import (
    save_incident,
    get_incidents,
    get_incident_by_event_id,
    claim_incident,
    release_incident_claim,
)

from app.services.llm_service import analyze_with_llm
from app.services.structured_logger import log_incident_event
from app.services.splunk_service import SplunkService
from app.services.host_identity import resolve_host_identity

# Remidiation
from app.services.remediation_policy import evaluate_remediation
from app.services.remediation_repository import save_remediation_proposal
from uuid import uuid4

router = APIRouter(
    prefix="/incident",
    tags=["Incident Analysis"],
)



splunk_service = SplunkService()

def resolve_incident_time(incident: IncidentRequest) -> datetime:
    timestamp = getattr(incident, "timestamp", None)

    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp

    if isinstance(timestamp, str) and timestamp:
        try:
            parsed = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed

        except ValueError:
            pass

    return datetime.now(timezone.utc)

@router.post(
    "/analyze",
    response_model=IncidentAnalysis | IncidentProcessingAck,
)
def analyze(incident: IncidentRequest):

    invocation_id = str(uuid4())[:8]

    print(
        f"[DEBUG] /incident/analyze entered: "
        f"time={datetime.now(timezone.utc).isoformat()}, "
        f"invocation={invocation_id}, "
        f"event_id={incident.event_id}"
    )

    start_time = time.perf_counter()

    # Step 1: Prevent duplicate Zabbix events
    if incident.event_id:
        existing = get_incident_by_event_id(
            incident.event_id
        )

        if existing:
            print(
                f"[INFO] Completed duplicate event ignored: "
                f"{incident.event_id}"
            )

            return IncidentAnalysis(
                host=existing["host"],
                severity=existing["severity"],
                summary=existing["summary"],
                observed_evidence=existing["observed_evidence"],
                possible_causes=existing["possible_causes"],
                recommended_actions=existing["recommended_actions"],
                confidence=existing["confidence"],
                analysis_source=existing["analysis_source"],
            )


    # Step 2: Claim event before expensive processing
    event_claimed = False

    if incident.event_id:
        event_claimed = claim_incident(
            incident.event_id
        )

        if not event_claimed:
            print(
                f"[INFO] Event already processing: "
                f"{incident.event_id}"
            )

            return IncidentProcessingAck(
                event_id=incident.event_id
            )


    try:

        # Step 2: Retrieve operational context from Splunk 
        incident_time = resolve_incident_time(incident)

        splunk_host = resolve_host_identity(incident.host)

        splunk_result = splunk_service.search_incident_context(
            host=splunk_host,
            incident_time=incident_time,
            window_minutes=10,
            max_results=20,
        )

        splunk_evidence = splunk_result["events"]
        splunk_available = splunk_result["available"]

        if splunk_available:
            print(
                f"[INFO] Splunk available. "
                f"Retrieved {len(splunk_evidence)} events "
                f"for host={incident.host}"
            )
        else:
            print(
                f"[WARNING] Splunk unavailable "
                f"for host={incident.host}"
            )

        # Step 3: Always create rule-based analysis first
        rule_analysis = analyze_incident(incident)

        # Step 4: Try Gemini
        try:
            final_analysis = analyze_with_llm(
                 incident,
                 rule_analysis,
                 splunk_evidence,
            )

        except Exception as exc:
            print(
                 f"[WARNING] Gemini analysis failed: {exc}"
            )

            final_analysis = IncidentAnalysis(
                host=rule_analysis.host,
                severity=rule_analysis.severity,
                summary=rule_analysis.summary,
                possible_causes=rule_analysis.possible_causes,
                recommended_actions=rule_analysis.recommended_actions,
                confidence="low",
                analysis_source="rule-based-fallback",
            )

        # Step 5: Store result
        save_incident(
            incident,
            final_analysis
        )

        # Step 6: Evaluate remediation policy
        proposal = evaluate_remediation(
            incident,
            final_analysis,
        )

        if proposal:
            saved = save_remediation_proposal(proposal)

            if saved:
                print(
                    f"[INFO] Remediation proposal created: "
                    f"remediation_id={proposal.remediation_id}, "
                    f"event_id={proposal.event_id}, "
                    f"action_id={proposal.action_id.value}, "
                    f"status={proposal.status.value}"
                )
            else:
                print(
                    f"[INFO] Remediation proposal already exists: "
                    f"event_id={proposal.event_id}, "
                    f"action_id={proposal.action_id.value}"
                )

        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        incident_id = incident.event_id or "unknown"

        log_incident_event(
            level="INFO",
            event="incident_analysis_completed",
            incident_id=incident_id,
            host=incident.host,
            source="zabbix",
            severity=incident.severity,
            duration_ms=duration_ms,
            analysis_source=final_analysis.analysis_source,
        )

        return final_analysis

    finally:
        if event_claimed and incident.event_id:
            release_incident_claim(
                incident.event_id
            )


@router.get("/")
def list_incidents():
    return get_incidents()
