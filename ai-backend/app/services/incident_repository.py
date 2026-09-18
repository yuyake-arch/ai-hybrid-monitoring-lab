import json
import sqlite3

from app.models.db import get_connection
from app.models.incident import (
    IncidentRequest,
    IncidentAnalysis,
)


def save_incident(
    incident: IncidentRequest,
    analysis: IncidentAnalysis
) -> int | None:

    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO incidents (
                event_id,
                host,
                trigger,
                severity,
                message,
                summary,
                observed_evidence,
                possible_causes,
                recommended_actions,
                confidence,
                analysis_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident.event_id,
                incident.host,
                incident.trigger,
                incident.severity,
                incident.message,
                analysis.summary,
                json.dumps(
                    analysis.observed_evidence
                ),
                json.dumps(
                    analysis.possible_causes
                ),
                json.dumps(
                    analysis.recommended_actions
                ),
                analysis.confidence,
                analysis.analysis_source,
            )
        )

        conn.commit()

        return cursor.lastrowid

    except sqlite3.IntegrityError:
        conn.rollback()

        print(
            f"[INFO] Duplicate event ignored: "
            f"{incident.event_id}"
        )

        return None

    finally:
        conn.close()


def get_incident_by_event_id(
    event_id: str
) -> dict | None:

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM incidents
            WHERE event_id = ?
            """,
            (event_id,)
        ).fetchone()

        if row is None:
            return None

        incident = dict(row)

        incident["observed_evidence"] = json.loads(
            incident["observed_evidence"] or "[]"
        )

        incident["possible_causes"] = json.loads(
            incident["possible_causes"]
        )

        incident["recommended_actions"] = json.loads(
            incident["recommended_actions"]
        )

        return incident

    finally:
        conn.close()


def get_incidents() -> list[dict]:

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT *
            FROM incidents
            ORDER BY id DESC
            """
        ).fetchall()

        incidents = []

        for row in rows:
            incident = dict(row)

            incident["observed_evidence"] = json.loads(
                incident["observed_evidence"] or "[]"
            )

            incident["possible_causes"] = json.loads(
                incident["possible_causes"]
            )

            incident["recommended_actions"] = json.loads(
                incident["recommended_actions"]
            )

            incidents.append(incident)

        return incidents

    finally:
        conn.close()

def claim_incident(
    event_id: str,
) -> bool:

    conn = get_connection()

    try:
        conn.execute(
            """
            INSERT INTO incident_processing (
                event_id
            )
            VALUES (?)
            """,
            (event_id,),
        )

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        conn.rollback()
        return False

    finally:
        conn.close()


def release_incident_claim(
    event_id: str,
) -> None:

    conn = get_connection()

    try:
        conn.execute(
            """
            DELETE FROM incident_processing
            WHERE event_id = ?
            """,
            (event_id,),
        )

        conn.commit()

    finally:
        conn.close()
