import json
import logging
from datetime import datetime, timezone
from pathlib import Path


LOG_PATH = Path(
    "/var/log/remediation-api/execution.json.log"
)

logger = logging.getLogger(
    "remediation-api-execution"
)

if not logger.handlers:
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(LOG_PATH)
    handler.setFormatter(
        logging.Formatter("%(message)s")
    )

    logger.addHandler(handler)
    logger.propagate = False


def log_execution_event(
    *,
    remediation_id: str,
    event_id: str,
    action_id: str,
    target: str,
    status: str,
    success: bool,
    changed: bool,
    return_code: int | None,
    message: str,
):
    record = {
        "timestamp": (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        ),
        "level": (
            "INFO" if success else "ERROR"
        ),
        "service": "remediation-api",
        "event": "remediation_execution",
        "remediation_id": remediation_id,
        "incident_id": event_id,
        "action_id": action_id,
        "target": target,
        "status": status,
        "success": success,
        "changed": changed,
        "return_code": return_code,
        "message": message,
    }

    logger.log(
        logging.INFO if success else logging.ERROR,
        json.dumps(record),
    )
