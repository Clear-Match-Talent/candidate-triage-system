"""SQLite persistence layer for runs and data."""
import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path(__file__).resolve().parents[1] / "runs.db"
DATA_DB_PATH = Path(__file__).resolve().parents[1] / "data.db"
LOG_PATH = Path(__file__).resolve().parents[1] / "runs" / "db_errors.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(str(LOG_PATH))
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

STANDARDIZED_INLINE_MAX_ROWS = 200
STANDARDIZED_CHUNK_ROWS = 200


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_data_connection():
    """Get data.db connection"""
    conn = sqlite3.connect(str(DATA_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            run_name TEXT NOT NULL,
            role_label TEXT NOT NULL,
            state TEXT NOT NULL,
            message TEXT,
            outputs TEXT,
            standardized_data TEXT,
            chat_messages TEXT,
            agent_session_key TEXT,
            pending_action TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS standardized_chunks (
            run_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (run_id, chunk_index)
        )
    """)
    
    conn.commit()
    conn.close()


def create_candidate_batch(role_id: str, name: str, status: str) -> str:
    """Create a candidate batch and return its ID."""
    batch_id = str(uuid.uuid4())
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO candidate_batches (id, role_id, name, status)
            VALUES (?, ?, ?, ?)
            """,
            (batch_id, role_id, name, status),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to create candidate batch role_id=%s", role_id)
        conn.rollback()
        raise
    finally:
        conn.close()
    return batch_id


def insert_batch_file_upload(
    batch_id: str,
    filename: str,
    row_count: int,
    headers: List[str],
) -> str:
    """Insert a batch file upload record and return its ID."""
    upload_id = str(uuid.uuid4())
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO batch_file_uploads (id, batch_id, filename, row_count, headers)
            VALUES (?, ?, ?, ?, ?)
            """,
            (upload_id, batch_id, filename, row_count, json.dumps(headers)),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to insert batch upload batch_id=%s", batch_id)
        conn.rollback()
        raise
    finally:
        conn.close()
    return upload_id


def get_candidate_batch(batch_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a candidate batch by ID."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM candidate_batches WHERE id = ?", (batch_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def get_role_name(role_id: str) -> Optional[str]:
    """Fetch role name by ID."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM roles WHERE id = ?", (role_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return row["name"]
    finally:
        conn.close()


def list_batch_file_uploads(batch_id: str) -> List[Dict[str, Any]]:
    """List uploaded files for a batch with parsed headers."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, batch_id, filename, uploaded_at, row_count, headers
            FROM batch_file_uploads
            WHERE batch_id = ?
            ORDER BY uploaded_at ASC
            """,
            (batch_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    uploads: List[Dict[str, Any]] = []
    for row in rows:
        headers = []
        if row["headers"]:
            try:
                headers = json.loads(row["headers"])
            except json.JSONDecodeError:
                headers = []
        uploads.append(
            {
                "id": row["id"],
                "batch_id": row["batch_id"],
                "filename": row["filename"],
                "uploaded_at": row["uploaded_at"],
                "row_count": row["row_count"],
                "headers": headers,
            }
        )
    return uploads


def list_standardized_candidates(batch_id: str) -> List[Dict[str, Any]]:
    """List standardized candidates for a batch."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                first_name,
                last_name,
                full_name,
                linkedin_url,
                location,
                current_company,
                current_title
            FROM raw_candidates
            WHERE batch_id = ? AND status = 'standardized'
            ORDER BY created_at ASC
            """,
            (batch_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def list_raw_candidates(
    batch_id: str,
    exclude_duplicates: bool = True,
) -> List[Dict[str, Any]]:
    """List raw candidates for a batch with parsed JSON payloads."""
    conn = get_data_connection()
    cursor = conn.cursor()
    where_clause = "batch_id = ?"
    params: Tuple[Any, ...] = (batch_id,)
    if exclude_duplicates:
        where_clause += " AND status != 'duplicate'"
    try:
        cursor.execute(
            f"""
            SELECT
                id,
                first_name,
                last_name,
                full_name,
                linkedin_url,
                location,
                current_company,
                current_title,
                raw_data,
                standardized_data,
                status,
                created_at
            FROM raw_candidates
            WHERE {where_clause}
            ORDER BY created_at ASC
            """,
            params,
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    candidates: List[Dict[str, Any]] = []
    for row in rows:
        raw_data = None
        if row["raw_data"]:
            try:
                raw_data = json.loads(row["raw_data"])
            except json.JSONDecodeError:
                raw_data = None
        standardized_data = None
        if row["standardized_data"]:
            try:
                standardized_data = json.loads(row["standardized_data"])
            except json.JSONDecodeError:
                standardized_data = None
        candidates.append(
            {
                "id": row["id"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "full_name": row["full_name"],
                "linkedin_url": row["linkedin_url"],
                "location": row["location"],
                "current_company": row["current_company"],
                "current_title": row["current_title"],
                "raw_data": raw_data,
                "standardized_data": standardized_data,
                "status": row["status"],
                "created_at": row["created_at"],
            }
        )
    return candidates


def get_batch_metrics(batch_id: str) -> Dict[str, int]:
    """Return aggregate metrics for a batch."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS file_count,
                COALESCE(SUM(row_count), 0) AS total_uploaded
            FROM batch_file_uploads
            WHERE batch_id = ?
            """,
            (batch_id,),
        )
        uploads_row = cursor.fetchone()
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'duplicate' THEN 1 ELSE 0 END), 0)
                    AS deduplicated_count,
                COALESCE(SUM(CASE WHEN status = 'standardized' THEN 1 ELSE 0 END), 0)
                    AS final_count
            FROM raw_candidates
            WHERE batch_id = ?
            """,
            (batch_id,),
        )
        candidates_row = cursor.fetchone()
    finally:
        conn.close()

    return {
        "file_count": int(uploads_row["file_count"] or 0),
        "total_uploaded": int(uploads_row["total_uploaded"] or 0),
        "deduplicated_count": int(candidates_row["deduplicated_count"] or 0),
        "final_count": int(candidates_row["final_count"] or 0),
    }


def update_candidate_batch_status(batch_id: str, status: str) -> None:
    """Update status for a candidate batch."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE candidate_batches SET status = ? WHERE id = ?",
            (status, batch_id),
        )
        conn.commit()
    except Exception:
        logger.exception(
            "Failed to update candidate batch status batch_id=%s status=%s",
            batch_id,
            status,
        )
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_raw_candidates(
    batch_id: str,
    role_id: str,
    candidates: List[Dict[str, Any]],
) -> None:
    """Insert raw candidates for a batch."""
    if not candidates:
        return
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        rows: List[Tuple[Any, ...]] = []
        for candidate in candidates:
            rows.append(
                (
                    str(uuid.uuid4()),
                    batch_id,
                    role_id,
                    candidate.get("first_name"),
                    candidate.get("last_name"),
                    candidate.get("full_name"),
                    candidate.get("linkedin_url"),
                    candidate.get("location"),
                    candidate.get("current_company"),
                    candidate.get("current_title"),
                    json.dumps(candidate.get("raw_data"))
                    if candidate.get("raw_data") is not None
                    else None,
                    json.dumps(candidate.get("standardized_data"))
                    if candidate.get("standardized_data") is not None
                    else None,
                    candidate.get("status"),
                )
            )
        cursor.executemany(
            """
            INSERT INTO raw_candidates (
                id,
                batch_id,
                role_id,
                first_name,
                last_name,
                full_name,
                linkedin_url,
                location,
                current_company,
                current_title,
                raw_data,
                standardized_data,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to insert raw candidates batch_id=%s", batch_id)
        conn.rollback()
        raise
    finally:
        conn.close()


def _prepare_standardized_data(standardized_data: Optional[List[Dict[str, Any]]]) -> Tuple[Optional[str], Optional[List[Tuple[int, str]]]]:
    if not standardized_data:
        return None, None
    if len(standardized_data) <= STANDARDIZED_INLINE_MAX_ROWS:
        return json.dumps(standardized_data), None
    chunks: List[Tuple[int, str]] = []
    for idx in range(0, len(standardized_data), STANDARDIZED_CHUNK_ROWS):
        chunk_index = idx // STANDARDIZED_CHUNK_ROWS
        payload = json.dumps(standardized_data[idx:idx + STANDARDIZED_CHUNK_ROWS])
        chunks.append((chunk_index, payload))
    marker = {
        "_chunked": True,
        "total_rows": len(standardized_data),
        "chunk_rows": STANDARDIZED_CHUNK_ROWS,
    }
    return json.dumps(marker), chunks


def _load_standardized_chunks(conn: sqlite3.Connection, run_id: str) -> Optional[List[Dict[str, Any]]]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT payload FROM standardized_chunks WHERE run_id = ? ORDER BY chunk_index ASC",
        (run_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    merged: List[Dict[str, Any]] = []
    for row in rows:
        payload = row["payload"] if isinstance(row, sqlite3.Row) else row[0]
        merged.extend(json.loads(payload))
    return merged


def save_run(run_status) -> None:
    """Save or update a run"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        standardized_payload, standardized_chunks = _prepare_standardized_data(run_status.standardized_data)

        cursor.execute("""
            INSERT OR REPLACE INTO runs 
            (run_id, created_at, run_name, role_label, state, message, outputs, 
             standardized_data, chat_messages, agent_session_key, pending_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_status.run_id,
            run_status.created_at,
            run_status.run_name,
            run_status.role_label,
            run_status.state,
            run_status.message,
            json.dumps(run_status.outputs) if run_status.outputs else None,
            standardized_payload,
            json.dumps(run_status.chat_messages) if run_status.chat_messages else None,
            run_status.agent_session_key,
            json.dumps(run_status.pending_action) if run_status.pending_action else None,
        ))

        cursor.execute("DELETE FROM standardized_chunks WHERE run_id = ?", (run_status.run_id,))
        if standardized_chunks:
            cursor.executemany(
                "INSERT INTO standardized_chunks (run_id, chunk_index, payload) VALUES (?, ?, ?)",
                [(run_status.run_id, idx, payload) for idx, payload in standardized_chunks],
            )

        conn.commit()
    except Exception:
        logger.exception("Failed to save run_id=%s", run_status.run_id)
        conn.rollback()
        raise
    finally:
        conn.close()


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a run by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    standardized_data = None
    if row["standardized_data"]:
        try:
            parsed = json.loads(row["standardized_data"])
            if isinstance(parsed, dict) and parsed.get("_chunked"):
                standardized_data = _load_standardized_chunks(conn, run_id)
            else:
                standardized_data = parsed
        except Exception:
            logger.exception("Failed to load standardized_data for run_id=%s", run_id)
            standardized_data = None
    else:
        standardized_data = _load_standardized_chunks(conn, run_id)

    conn.close()

    return {
        "run_id": row["run_id"],
        "created_at": row["created_at"],
        "run_name": row["run_name"],
        "role_label": row["role_label"],
        "state": row["state"],
        "message": row["message"],
        "outputs": json.loads(row["outputs"]) if row["outputs"] else None,
        "standardized_data": standardized_data,
        "chat_messages": json.loads(row["chat_messages"]) if row["chat_messages"] else None,
        "agent_session_key": row["agent_session_key"],
        "pending_action": json.loads(row["pending_action"]) if row["pending_action"] else None,
    }


def list_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """List recent runs"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    
    runs = []
    for row in rows:
        standardized_data = None
        if row["standardized_data"]:
            try:
                parsed = json.loads(row["standardized_data"])
                if isinstance(parsed, dict) and parsed.get("_chunked"):
                    standardized_data = _load_standardized_chunks(conn, row["run_id"])
                else:
                    standardized_data = parsed
            except Exception:
                logger.exception("Failed to load standardized_data for run_id=%s", row["run_id"])
                standardized_data = None
        else:
            standardized_data = _load_standardized_chunks(conn, row["run_id"])

        runs.append({
            "run_id": row["run_id"],
            "created_at": row["created_at"],
            "run_name": row["run_name"],
            "role_label": row["role_label"],
            "state": row["state"],
            "message": row["message"],
            "outputs": json.loads(row["outputs"]) if row["outputs"] else None,
            "standardized_data": standardized_data,
            "chat_messages": json.loads(row["chat_messages"]) if row["chat_messages"] else None,
            "agent_session_key": row["agent_session_key"],
            "pending_action": json.loads(row["pending_action"]) if row["pending_action"] else None,
        })
    
    conn.close()
    return runs


def delete_run(run_id: str) -> None:
    """Delete a run"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM standardized_chunks WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
    conn.commit()
    conn.close()


# Initialize database on module import
init_db()
