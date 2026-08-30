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
                possible_causes TEXT,
                recommended_actions TEXT,
                confidence TEXT,
                analysis_source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    finally:

        conn.close()
