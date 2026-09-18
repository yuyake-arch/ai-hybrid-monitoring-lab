import sqlite3
from pathlib import Path


DB_PATH = Path("incidents.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                host TEXT NOT NULL,
                trigger TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                summary TEXT,
                observed_evidence TEXT,
                possible_causes TEXT,
                recommended_actions TEXT,
                confidence TEXT,
                analysis_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS remediation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                remediation_id TEXT UNIQUE NOT NULL,
                event_id TEXT NTO NULL,

                host TEXT NOT NULL,
                target_host TEXT NOT NULL,

                action_id TEXT NOT NULL,
                action_description TEXT NOT NULL,

                risk TEXT NOT NULL,
                status TEXT NOT NULL,

                approval_required INTEGER NOT NULL DEFAULT 1,

                ai_recommended_actions TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                approved_by TEXT,
                approved_at TIMESTAMP,

                decision_by TEXT,
                decision_at TIMESTAMP,
                executed_by TEXT,
                changed INTEGER,
                return_code INTEGER,

                execution_started_at TIMESTAMP,
                execution_finished_at TIMESTAMP,

                success INTEGER,
                result_summary TEXT,
                execution_output TEXT,

                UNIQUE(event_id, action_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS incident_processing (
                event_id TEXT PRIMARY KEY,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        conn.commit()

    finally:

        conn.close()
