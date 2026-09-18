import os
import requests


REMEDIATION_API_URL = os.getenv(
    "REMEDIATION_API_URL"
)

REMEDIATION_API_TOKEN = os.getenv(
    "REMEDIATION_API_TOKEN"
)


def execute_remediation(
    *,
    remediation_id: str,
    event_id: str,
    action_id: str,
    target: str,
) -> dict:

    if not REMEDIATION_API_URL:
        return {
            "success": False,
            "error": "REMEDIATION_API_URL is not configured",
        }

    if not REMEDIATION_API_TOKEN:
        return {
            "success": False,
            "error": "REMEDIATION_API_TOKEN is not configured",
        }

    url = (
        f"{REMEDIATION_API_URL}"
        "/remediation/execute"
    )

    payload = {
        "remediation_id": remediation_id,
        "event_id": event_id,
        "action_id": action_id,
        "target": target,
    }

    headers = {
        "X-Remediation-Token":
            REMEDIATION_API_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=130,
        )

        if response.status_code != 200:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
            }

        return response.json()

    except requests.RequestException as exc:
        return {
            "success": False,
            "error": str(exc),
        }
