import json
import logging
from datetime import datetime, timezone
from pathlib import Path


LOG_PATH = Path("/var/log/ai-backend/analysis.json.log")


logger = logging.getLogger("ai-backend-incident")

if not logger.handlers:
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(LOG_PATH)

    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.propagate = False


def log_incident_event(
    *,
    level: str,
    event: str,
    incident_id: str,
    host: str,
    source: str,
    severity: str,
    duration_ms: int,
    analysis_source: str | None = None,
):
    record = {
        "timestamp": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "level": level.upper(),
        "service": "ai-backend",
        "event": event,
        "incident_id": incident_id,
        "host": host,
        "source": source,
        "severity": severity.lower(),
        "duration_ms": duration_ms,
    }

    if analysis_source:
        record["analysis_source"] = analysis_source

    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        json.dumps(record),
    )


def log_remediation_event(
    *,
    level: str,
    event: str,
    remediation_id: str,
    incident_id: str,
    host: str,
    action_id: str,
    status: str,
    actor: str | None = None,
):
    record = {
        "timestamp": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "level": level.upper(),
        "service": "ai-backend",
        "event": event,
        "remediation_id": remediation_id,
        "incident_id": incident_id,
        "host": host,
        "action_id": action_id,
        "status": status,
    }

    if actor:
        record["actor"] = actor

    logger.log(
        getattr(
            logging,
            level.upper(),
            logging.INFO,
        ),
        json.dumps(record),
    )

def log_remediation_execution_completed(
    *,
    level: str,
    remediation_id: str,
    incident_id: str,
    host: str,
    target_host: str,
    action_id: str,
    status: str,
    actor: str,
    success: bool,
    changed: bool,
    return_code: int | None,
):
    record = {
        "timestamp": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "level": level.upper(),
        "service": "ai-backend",
        "event": "remediation_execution_completed",
        "remediation_id": remediation_id,
        "incident_id": incident_id,
        "host": host,
        "target_host": target_host,
        "action_id": action_id,
        "status": status,
        "actor": actor,
        "success": success,
        "changed": changed,
        "return_code": return_code,
    }

    logger.log(
        getattr(
            logging,
            level.upper(),
            logging.INFO,
        ),
        json.dumps(record),
    )
