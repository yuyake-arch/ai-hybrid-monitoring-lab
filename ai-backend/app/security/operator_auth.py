import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


security = HTTPBasic()


def get_operator_identity(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    expected_username = os.getenv(
        "REMEDIATION_OPERATOR_USERNAME"
    )

    expected_password = os.getenv(
        "REMEDIATION_OPERATOR_PASSWORD"
    )

    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Remediation operator authentication is not configured",
        )

    username_valid = secrets.compare_digest(
        credentials.username,
        expected_username,
    )

    password_valid = secrets.compare_digest(
        credentials.password,
        expected_password,
    )

    if not (username_valid and password_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator credentials",
            headers={
                "WWW-Authenticate": "Basic"
            },
        )

    return credentials.username
