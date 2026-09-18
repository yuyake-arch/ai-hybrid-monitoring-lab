import os
import secrets

from fastapi import Header, HTTPException


def verify_service_token(
    x_remediation_token: str | None = Header(
        default=None,
        alias="X-Remediation-Token",
    ),
) -> None:
    expected_token = os.getenv(
        "REMEDIATION_API_TOKEN"
    )

    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="Remediation API authentication is not configured",
        )

    if (
        x_remediation_token is None
        or not secrets.compare_digest(
            x_remediation_token,
            expected_token,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid remediation service token",
        )
