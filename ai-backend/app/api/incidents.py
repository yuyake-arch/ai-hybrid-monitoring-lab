import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.incident import IncidentRequest, IncidentAnalysis
from app.services.incident_analyzer import analyze_incident
from app.services.incident_repository import (
    save_incident,
    get_incidents,
    get_incident_by_event_id,
)

from app.services.llm_service import analyze_with_llm
from app.services.structured_logger import log_incident_event
from app.services.splunk_service import SplunkService

router = APIRouter(
    prefix="/incident",
    tags=["Incident Analysis"],
)


HOST_MAPPING = {
    "Monitoring-EC2": "aws-mon-core-01",
}

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

@router.post("/analyze", response_model=IncidentAnalysis)
def analyze(incident: IncidentRequest):

    start_time = time.perf_counter()

    # Step 1: Prevent duplicate Zabbix events
    if incident.event_id:
        existing = get_incident_by_event_id(
            incident.event_id
        )

        if existing:
            return IncidentAnalysis(
                host=existing["host"],
                severity=existing["severity"],
                summary=existing["summary"],
                possible_causes=existing["possible_causes"],
                recommended_actions=existing["recommended_actions"],
                confidence=existing["confidence"],
                analysis_source=existing["analysis_source"],
            )


    # Step 2: Retrieve operational context from Splunk 
    incident_time = resolve_incident_time(incident)

    splunk_host = HOST_MAPPING.get(
        incident.host,
        incident.host,
    )

    splunk_result = splunk_service.search_incident_context(
        host=splunk_host,
        incident_time=incident_time,
        window_minutes=10,
        max_results=20,
    )

    splunk_evidence = splunk_result["events"]
    splunk_available = splunk_result["available

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


@router.get("/")
def list_incidents():
    return get_incidents()
