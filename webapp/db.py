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


def list_role_documents(role_id: str) -> List[Dict[str, Any]]:
    """List role documents for a role."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, role_id, doc_type, filename, file_path, uploaded_at
            FROM role_documents
            WHERE role_id = ?
            ORDER BY uploaded_at DESC
            """,
            (role_id,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_role_document_by_type(
    role_id: str, doc_type: str
) -> Optional[Dict[str, Any]]:
    """Fetch the latest role document for a given type."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, role_id, doc_type, filename, file_path, uploaded_at
            FROM role_documents
            WHERE role_id = ? AND doc_type = ?
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (role_id, doc_type),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def get_role_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a role document by ID."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, role_id, doc_type, filename, file_path, uploaded_at
            FROM role_documents
            WHERE id = ?
            """,
            (doc_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def create_role_document(
    role_id: str, doc_type: str, filename: str, file_path: str
) -> str:
    """Create a role document record."""
    doc_id = str(uuid.uuid4())
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO role_documents (id, role_id, doc_type, filename, file_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, role_id, doc_type, filename, file_path),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to create role document role_id=%s", role_id)
        conn.rollback()
        raise
    finally:
        conn.close()
    return doc_id


def update_role_document(doc_id: str, filename: str, file_path: str) -> None:
    """Update a role document record."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE role_documents
            SET filename = ?, file_path = ?, uploaded_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (filename, file_path, doc_id),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to update role document doc_id=%s", doc_id)
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_role_document(doc_id: str) -> None:
    """Delete a role document record."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM role_documents WHERE id = ?", (doc_id,))
        conn.commit()
    except Exception:
        logger.exception("Failed to delete role document doc_id=%s", doc_id)
        conn.rollback()
        raise
    finally:
        conn.close()


def _parse_role_criteria_row(row: sqlite3.Row) -> Dict[str, Any]:
    must_haves = []
    if row["must_haves"]:
        try:
            must_haves = json.loads(row["must_haves"])
        except json.JSONDecodeError:
            must_haves = []

    gating_params = {}
    if row["gating_params"]:
        try:
            gating_params = json.loads(row["gating_params"])
        except json.JSONDecodeError:
            gating_params = {}

    nice_to_haves = []
    if row["nice_to_haves"]:
        try:
            nice_to_haves = json.loads(row["nice_to_haves"])
        except json.JSONDecodeError:
            nice_to_haves = []

    return {
        "id": row["id"],
        "role_id": row["role_id"],
        "version": row["version"],
        "must_haves": must_haves,
        "gating_params": gating_params,
        "nice_to_haves": nice_to_haves,
        "is_locked": bool(row["is_locked"]),
        "created_at": row["created_at"],
    }


def get_latest_role_criteria(role_id: str) -> Optional[Dict[str, Any]]:
    """Return the latest criteria configuration for a role."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id,
                role_id,
                version,
                must_haves,
                gating_params,
                nice_to_haves,
                is_locked,
                created_at
            FROM role_criteria
            WHERE role_id = ?
            ORDER BY version DESC, created_at DESC
            LIMIT 1
            """,
            (role_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_role_criteria_row(row)
    finally:
        conn.close()


def list_role_criteria_history(role_id: str) -> List[Dict[str, Any]]:
    """Return all criteria configurations for a role."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id,
                role_id,
                version,
                must_haves,
                gating_params,
                nice_to_haves,
                is_locked,
                created_at
            FROM role_criteria
            WHERE role_id = ?
            ORDER BY version DESC, created_at DESC
            """,
            (role_id,),
        )
        rows = cursor.fetchall()
        return [_parse_role_criteria_row(row) for row in rows]
    finally:
        conn.close()


def create_role_criteria(
    role_id: str,
    must_haves: List[str],
    gating_params: Dict[str, Any],
    nice_to_haves: List[str],
) -> Dict[str, Any]:
    """Create a new criteria configuration version for a role."""
    criteria_id = str(uuid.uuid4())
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COALESCE(MAX(version), 0) AS max_version
            FROM role_criteria
            WHERE role_id = ?
            """,
            (role_id,),
        )
        row = cursor.fetchone()
        version = int(row["max_version"] or 0) + 1
        cursor.execute(
            """
            INSERT INTO role_criteria (
                id,
                role_id,
                version,
                must_haves,
                gating_params,
                nice_to_haves,
                is_locked
            )
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                criteria_id,
                role_id,
                version,
                json.dumps(must_haves),
                json.dumps(gating_params),
                json.dumps(nice_to_haves),
            ),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to create role criteria role_id=%s", role_id)
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "id": criteria_id,
        "role_id": role_id,
        "version": version,
        "must_haves": must_haves,
        "gating_params": gating_params,
        "nice_to_haves": nice_to_haves,
        "is_locked": False,
    }


def get_role_criteria(criteria_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a role criteria record by ID."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM role_criteria WHERE id = ?", (criteria_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_role_criteria_row(row)
    finally:
        conn.close()


def lock_role_criteria(criteria_id: str) -> Optional[Dict[str, Any]]:
    """Lock a criteria version and return the updated record."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE role_criteria
            SET is_locked = 1
            WHERE id = ?
            """,
            (criteria_id,),
        )
        conn.commit()
        cursor.execute("SELECT * FROM role_criteria WHERE id = ?", (criteria_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_role_criteria_row(row)
    except Exception:
        logger.exception("Failed to lock role criteria id=%s", criteria_id)
        conn.rollback()
        raise
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


def list_duplicate_candidates(batch_id: str) -> List[Dict[str, Any]]:
    """List duplicate candidates for a batch."""
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
                created_at
            FROM raw_candidates
            WHERE batch_id = ? AND status = 'duplicate'
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


def list_candidates_by_ids(candidate_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch candidates by ID with parsed standardized data."""
    if not candidate_ids:
        return []
    conn = get_data_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in candidate_ids)
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
                standardized_data
            FROM raw_candidates
            WHERE id IN ({placeholders})
            """,
            tuple(candidate_ids),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    candidates: List[Dict[str, Any]] = []
    for row in rows:
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
                "standardized_data": standardized_data,
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


def approve_candidate_batch(batch_id: str) -> Optional[Dict[str, Any]]:
    """Approve a candidate batch and return the updated record."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE candidate_batches
            SET status = 'approved', approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (batch_id,),
        )
        conn.commit()
        cursor.execute("SELECT * FROM candidate_batches WHERE id = ?", (batch_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    except Exception:
        logger.exception("Failed to approve candidate batch batch_id=%s", batch_id)
        conn.rollback()
        raise
    finally:
        conn.close()


def get_latest_criteria_version(role_id: str) -> Optional[Dict[str, Any]]:
    """Return the latest criteria version for a role."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, role_id, version, criteria_data, created_at
            FROM criteria_versions
            WHERE role_id = ?
            ORDER BY version DESC, created_at DESC
            LIMIT 1
            """,
            (role_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def get_criteria_version(criteria_version_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a criteria version by ID."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, role_id, version, criteria_data, created_at
            FROM criteria_versions
            WHERE id = ?
            """,
            (criteria_version_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        criteria_data = {}
        if data.get("criteria_data"):
            try:
                criteria_data = json.loads(data["criteria_data"])
            except json.JSONDecodeError:
                criteria_data = {}
        data["criteria_data"] = criteria_data
        return data
    finally:
        conn.close()


def ensure_criteria_version(criteria: Dict[str, Any]) -> str:
    """Ensure criteria_versions row exists for a role_criteria record."""
    criteria_id = criteria.get("id")
    if not criteria_id:
        raise ValueError("criteria id is required")
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM criteria_versions WHERE id = ?",
            (criteria_id,),
        )
        row = cursor.fetchone()
        if row:
            return row["id"]
        criteria_payload = {
            "must_haves": criteria.get("must_haves") or [],
            "gating_params": criteria.get("gating_params") or {},
            "nice_to_haves": criteria.get("nice_to_haves") or [],
            "is_locked": bool(criteria.get("is_locked")),
        }
        cursor.execute(
            """
            INSERT INTO criteria_versions (id, role_id, version, criteria_data)
            VALUES (?, ?, ?, ?)
            """,
            (
                criteria_id,
                criteria.get("role_id"),
                criteria.get("version"),
                json.dumps(criteria_payload),
            ),
        )
        conn.commit()
        return criteria_id
    except Exception:
        logger.exception("Failed to ensure criteria version id=%s", criteria_id)
        conn.rollback()
        raise
    finally:
        conn.close()


def list_random_standardized_candidate_ids(
    batch_id: str, limit: int = 50
) -> List[str]:
    """Return random standardized candidate IDs for a batch."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id
            FROM raw_candidates
            WHERE batch_id = ? AND status = 'standardized'
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (batch_id, limit),
        )
        rows = cursor.fetchall()
        return [row["id"] for row in rows]
    finally:
        conn.close()


def create_test_run(
    role_id: str, criteria_version_id: str, candidate_ids: List[str]
) -> str:
    """Create a test run record and return its ID."""
    test_run_id = str(uuid.uuid4())
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO test_runs (id, role_id, criteria_version_id, candidate_ids)
            VALUES (?, ?, ?, ?)
            """,
            (test_run_id, role_id, criteria_version_id, json.dumps(candidate_ids)),
        )
        conn.commit()
    except Exception:
        logger.exception("Failed to create test run role_id=%s", role_id)
        conn.rollback()
        raise
    finally:
        conn.close()
    return test_run_id


def get_test_run(test_run_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a test run record by ID."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM test_runs WHERE id = ?", (test_run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        candidate_ids = []
        if data.get("candidate_ids"):
            try:
                candidate_ids = json.loads(data["candidate_ids"])
            except json.JSONDecodeError:
                candidate_ids = []
        data["candidate_ids"] = candidate_ids
        return data
    finally:
        conn.close()


def count_test_run_results(test_run_id: str) -> int:
    """Return count of results stored for a test run."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM test_run_results WHERE test_run_id = ?",
            (test_run_id,),
        )
        row = cursor.fetchone()
        return int(row["total"] or 0)
    finally:
        conn.close()


def list_test_run_results(test_run_id: str) -> List[Dict[str, Any]]:
    """List test run results with parsed evaluations."""
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id,
                candidate_id,
                candidate_name,
                candidate_linkedin,
                criteria_evaluations,
                final_bucket,
                created_at
            FROM test_run_results
            WHERE test_run_id = ?
            ORDER BY created_at ASC
            """,
            (test_run_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    results: List[Dict[str, Any]] = []
    for row in rows:
        evaluations = {}
        if row["criteria_evaluations"]:
            try:
                evaluations = json.loads(row["criteria_evaluations"])
            except json.JSONDecodeError:
                evaluations = {}
        results.append(
            {
                "id": row["id"],
                "candidate_id": row["candidate_id"],
                "candidate_name": row["candidate_name"],
                "candidate_linkedin": row["candidate_linkedin"],
                "criteria_evaluations": evaluations,
                "final_bucket": row["final_bucket"],
                "created_at": row["created_at"],
            }
        )
    return results


def insert_test_run_result(
    test_run_id: str,
    candidate_id: str,
    candidate_name: str,
    candidate_linkedin: Optional[str],
    criteria_evaluations: Dict[str, Any],
    final_bucket: str,
) -> str:
    """Insert a single test run result row."""
    result_id = str(uuid.uuid4())
    conn = get_data_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO test_run_results (
                id,
                test_run_id,
                candidate_id,
                candidate_name,
                candidate_linkedin,
                criteria_evaluations,
                final_bucket
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                test_run_id,
                candidate_id,
                candidate_name,
                candidate_linkedin,
                json.dumps(criteria_evaluations),
                final_bucket,
            ),
        )
        conn.commit()
    except Exception:
        logger.exception(
            "Failed to insert test run result test_run_id=%s candidate_id=%s",
            test_run_id,
            candidate_id,
        )
        conn.rollback()
        raise
    finally:
        conn.close()
    return result_id


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
