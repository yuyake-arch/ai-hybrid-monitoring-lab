import json
import sqlite3

from datetime import datetime, timezone
from app.models.db import get_connection
from app.models.remediation import RemediationProposal
from app.models.remediation import RemediationStatus


def save_remediation_proposal(
    proposal: RemediationProposal,
) -> bool:

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO remediation_history (
                remediation_id,
                event_id,
                host,
                target_host,
                action_id,
                action_description,
                risk,
                status,
                approval_required,
                ai_recommended_actions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal.remediation_id,
                proposal.event_id,
                proposal.host,
                proposal.target_host,
                proposal.action_id.value,
                proposal.action_description,
                proposal.risk.value,
                proposal.status.value,
                int(proposal.approval_required),
                json.dumps(
                    proposal.ai_recommended_actions
                ),
            ),
        )

        conn.commit()

        return True

    except sqlite3.IntegrityError:

        conn.rollback()

        print(
            f"[INFO] Duplicate remediation ignored: "
            f"event_id={proposal.event_id}, "
            f"action_id={proposal.action_id.value}"
        )

        return False

    finally:
        conn.close()


def get_remediation_by_id(
    remediation_id: str,
) -> dict | None:

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM remediation_history
            WHERE remediation_id = ?
            """,
            (remediation_id,),
        ).fetchone()

        if row is None:
            return None

        return _deserialize_remediation(row)

    finally:
        conn.close()


def get_remediations() -> list[dict]:

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM remediation_history
            ORDER BY id DESC
            """
        ).fetchall()

        return [
            _deserialize_remediation(row)
            for row in rows
        ]

    finally:
        conn.close()


def _deserialize_remediation(row) -> dict:

    remediation = dict(row)

    remediation["approval_required"] = bool(
        remediation["approval_required"]
    )

    if remediation["success"] is not None:
        remediation["success"] = bool(
            remediation["success"]
        )

    remediation["ai_recommended_actions"] = json.loads(
        remediation["ai_recommended_actions"] or "[]"
    )

    return remediation

def update_remediation_status(
    remediation_id: str,
    new_status: RemediationStatus,
    decision_by: str | None = None,
) -> bool:

    conn = get_connection()

    try:
        approved_at = None

        if new_status in (
            RemediationStatus.APPROVED,
            RemediationStatus.REJECTED,
        ):
            decision_at = datetime.now(
                timezone.utc
            ).isoformat()


        cursor = conn.execute(
            """
            UPDATE remediation_history
            SET
                status = ?,
                decision_by = ?,
                decision_at = ?
            WHERE remediation_id = ?
              AND status = ?
            """,
            (
                new_status.value,
                decision_by,
                decision_at,
                remediation_id,
                RemediationStatus.PENDING_APPROVAL.value,
            ),
        )

        conn.commit()

        return cursor.rowcount == 1

    finally:
        conn.close()


def mark_remediation_executing(
    remediation_id: str,
    executed_by: str,
) -> bool:
    conn = get_connection()

    try:
        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        cursor = conn.execute(
            """
            UPDATE remediation_history
            SET
                status = ?,
                execution_started_at = ?,
                executed_by = ?
            WHERE remediation_id = ?
              AND status = ?
            """,
            (
                RemediationStatus.EXECUTING.value,
                started_at,
                executed_by,
                remediation_id,
                RemediationStatus.APPROVED.value,
            ),
        )

        conn.commit()
        return cursor.rowcount == 1

    finally:
        conn.close()

def complete_remediation_execution(
    *,
    remediation_id: str,
    success: bool,
    changed: bool,
    return_code: int | None,
    result_summary: str,
    execution_output: str | None = None,
) -> bool:
    conn = get_connection()

    try:
        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        final_status = (
            RemediationStatus.SUCCESS
            if success
            else RemediationStatus.FAILED
        )

        cursor = conn.execute(
            """
            UPDATE remediation_history
            SET
                status = ?,
                execution_finished_at = ?,
                success = ?,
                changed = ?,
                return_code = ?,
                result_summary = ?,
                execution_output = ?
            WHERE remediation_id = ?
              AND status = ?
            """,
            (
                final_status.value,
                finished_at,
                int(success),
                int(changed),
                return_code,
                result_summary,
                execution_output,
                remediation_id,
                RemediationStatus.EXECUTING.value,
            ),
        )

        conn.commit()
        return cursor.rowcount == 1

    finally:
        conn.close()
