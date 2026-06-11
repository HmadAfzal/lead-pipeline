import sqlite3
import hashlib
import json
from contextlib import contextmanager

DB_PATH = "leads.db"

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT NOT NULL,
                message TEXT NOT NULL,
                dedup_hash TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                score INTEGER,
                qualification TEXT,
                reasoning TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def make_hash(email: str, message: str) -> str:
    return hashlib.sha256(f"{email.lower()}:{message}".encode()).hexdigest()

def save_lead(name, email, company, message) -> int | None:
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO leads (name, email, company, message, dedup_hash) VALUES (?, ?, ?, ?, ?)",
                (name, email, company, message, make_hash(email, message)),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  

def get_lead(lead_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return dict(row) if row else None

def update_status(lead_id: int, status: str, error: str = None, **fields):
    sets, vals = ["status = ?", "updated_at = CURRENT_TIMESTAMP", "error = ?"], [status, error]
    for k, v in fields.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(lead_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE leads SET {', '.join(sets)} WHERE id = ?", vals)

def get_stuck_leads() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE status IN ('pending', 'processing')"
        ).fetchall()
        return [dict(r) for r in rows]
