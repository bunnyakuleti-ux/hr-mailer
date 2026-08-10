"""
SQLite persistence layer — survives Render free-tier restarts.
Uses only Python built-ins (sqlite3, json, os).
"""
import sqlite3
import json
import os
import time
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "hr_mailer.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                email TEXT,
                name  TEXT,
                credentials_json TEXT,
                created_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                campaign_id TEXT PRIMARY KEY,
                data_json   TEXT,
                created_at  REAL
            )
        """)
        conn.commit()
    logger.info(f"Database ready at {DB_PATH}")


# ── Sessions ────────────────────────────────────────────────────────────────

def save_session(token: str, email: str, name: str, credentials: dict):
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO sessions (token, email, name, credentials_json, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (token, email, name, json.dumps(credentials), time.time()))
        conn.commit()


def get_session(token: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ).fetchone()
    if not row:
        return None
    creds = json.loads(row["credentials_json"])
    return {
        **creds,
        "email": row["email"],
        "name": row["name"],
    }


def delete_session(token: str):
    with _get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def session_exists(token: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE token = ?", (token,)
        ).fetchone()
    return row is not None


# ── Campaigns ────────────────────────────────────────────────────────────────

def save_campaign(campaign_id: str, data: dict):
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO campaigns (campaign_id, data_json, created_at)
            VALUES (?, ?, ?)
        """, (campaign_id, json.dumps(data), time.time()))
        conn.commit()


def load_campaign(campaign_id: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT data_json FROM campaigns WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
    if not row:
        return None
    return json.loads(row["data_json"])


def load_all_campaigns() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT data_json FROM campaigns ORDER BY created_at DESC"
        ).fetchall()
    return [json.loads(r["data_json"]) for r in rows]


# Initialise on import
init_db()
