"""Minimal internal web UI for Candidate Triage System.

MVP goals:
- Upload one or more CSV exports
- Run pipeline: ingestion (standardize+dedupe) -> evaluation -> bucketing
- Download outputs

Run (dev):
  uvicorn webapp.main:app --reload --port 8000

Notes:
- Requires Python + deps in requirements.txt
- Requires ANTHROPIC_API_KEY in environment for evaluation step
"""

from __future__ import annotations

import csv
import json
import logging
import re
import shutil
import subprocess
import threading
import time
import uuid
from io import StringIO
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import Body, FastAPI, File, Form, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import os
from anthropic import Anthropic
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from webapp.main_tool_calling import execute_data_modification, EXECUTE_PYTHON_TOOL
from webapp import db
from webapp.chatbot_context import build_agent_context, format_field_stats, format_quality_issues
from filtering.evaluator import evaluate_candidate, build_gating_param_list

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "runs"
UPLOADS_DIR = REPO_ROOT / "uploads" / "batches"
ROLE_UPLOADS_DIR = REPO_ROOT / "uploads" / "roles"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STANDARDIZED_FIELDS = [
    "first_name",
    "last_name",
    "full_name",
    "linkedin_url",
    "location",
    "current_company",
    "current_title",
]
logger = logging.getLogger(__name__)
STEPPER_STEPS = [
    {"key": "upload", "label": "Upload"},
    {"key": "map", "label": "Map Fields"},
    {"key": "standardize", "label": "Standardize"},
    {"key": "review", "label": "Review"},
    {"key": "approve", "label": "Approve"},
    {"key": "test_run", "label": "Test Run"},
    {"key": "filter", "label": "Filter"},
    {"key": "results", "label": "Results"},
]
STEPPER_STATUS_MAP = {
    "pending": "map",
    "mapping": "map",
    "standardizing": "standardize",
    "standardized": "review",
    "approved": "test_run",
}
STEPPER_URL_BUILDERS = {
    "map": lambda role_id, batch_id: f"/roles/{role_id}/batches/{batch_id}/map",
    "review": lambda role_id, batch_id: f"/roles/{role_id}/batches/{batch_id}/review",
    "test_run": lambda role_id, batch_id: f"/roles/{role_id}/batches/{batch_id}/test-run",
    "filter": lambda role_id, batch_id: f"/roles/{role_id}/batches/{batch_id}/run",
    "results": lambda role_id, batch_id: f"/roles/{role_id}/batches/{batch_id}/results",
}

RUNS_DIR.mkdir(parents=True, exist_ok=True)
ROLE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Candidate Triage System UI", version="0.1.0")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://34.219.151.160:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize Anthropic client for chat
anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


@dataclass
class RunStatus:
    run_id: str
    created_at: float
    run_name: str
    role_label: str
    state: str  # queued|running|standardized|evaluating|done|error
    message: str = ""
    outputs: Optional[dict] = None
    standardized_data: Optional[list] = None  # CSV data for review
    chat_messages: Optional[list] = None  # Chat history with agent
    agent_session_key: Optional[str] = None  # Clawdbot session for this run
    pending_action: Optional[dict] = None  # Proposed data modification waiting for confirmation


def step_from_batch_status(status: Optional[str]) -> str:
    """Translate batch status into the active workflow step."""
    return STEPPER_STATUS_MAP.get((status or "").lower(), "upload")


def build_stepper_context(
    current_step: str,
    role_id: Optional[str] = None,
    batch_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return stepper payload for templates."""
    step_index = {step["key"]: idx for idx, step in enumerate(STEPPER_STEPS)}
    current_index = step_index.get(current_step, 0)
    steps: List[Dict[str, Any]] = []
    for idx, step in enumerate(STEPPER_STEPS):
        if idx < current_index:
            state = "completed"
        elif idx == current_index:
            state = "active"
        else:
            state = "future"
        url = None
        if role_id and batch_id and step["key"] in STEPPER_URL_BUILDERS:
            url = STEPPER_URL_BUILDERS[step["key"]](role_id, batch_id)
        steps.append(
            {
                "key": step["key"],
                "label": step["label"],
                "state": state,
                "url": url,
            }
        )
    return {"steps": steps, "current": current_step}


# Helper functions for DB <-> RunStatus conversion
def dict_to_runstatus(data: dict) -> RunStatus:
    """Convert database dict to RunStatus dataclass"""
    return RunStatus(**data)


def get_run_or_404(run_id: str) -> Optional[RunStatus]:
    """Get run from DB and convert to RunStatus, return None if not found"""
    data = db.get_run(run_id)
    if not data:
        return None
    return dict_to_runstatus(data)


def save_run_to_db(st: RunStatus) -> None:
    """Save RunStatus to database"""
    db.save_run(st)


def safe_name(s: str) -> str:
    s = (s or "").strip()
    keep = []
    for ch in s:
        if ch.isalnum() or ch in "-_ ":
            keep.append(ch)
    out = "".join(keep).strip().replace(" ", "_")
    return out[:80] if out else "run"


def safe_filename(name: str) -> str:
    raw = (name or "").strip()
    keep = []
    for ch in raw:
        if ch.isalnum() or ch in "-_.":
            keep.append(ch)
    out = "".join(keep).strip()
    if not out:
        out = "file.csv"
    return out[:120]


DOC_TYPE_CONFIG = {
    "jd": {"extensions": {".pdf", ".docx", ".txt"}, "allow_url": False},
    "intake": {"extensions": {".pdf", ".docx", ".txt"}, "allow_url": True},
    "calibration": {"extensions": {".csv"}, "allow_url": False},
}


def read_csv_metadata(file_path: Path) -> Tuple[List[str], int]:
    for encoding in ("utf-8", "latin1"):
        try:
            with file_path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                headers = next(reader, [])
                row_count = sum(1 for _ in reader)
            return headers, row_count
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode CSV: {file_path.name}")


def read_csv_with_fallback(file_path: Path) -> pd.DataFrame:
    """Read CSV with UTF-8 fallback to latin1."""
    try:
        return pd.read_csv(file_path, dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        return pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="latin1")


def normalize_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    return str(value)


def normalize_linkedin_url(value: Optional[str]) -> Optional[str]:
    cleaned = normalize_value(value)
    if not cleaned:
        return None
    lower = cleaned.lower().strip()
    lower = lower.replace("http://", "https://")
    lower = lower.replace("https://www.", "https://")

    if "linkedin.com" in lower:
        match = re.search(r"linkedin\.com/(in|pub)/([^/?#]+)", lower)
        if match:
            username = match.group(2)
        else:
            path = lower.split("linkedin.com", 1)[-1].strip("/")
            username = path.split("/")[-1] if path else ""
        username = username.split("?")[0].split("#")[0].strip("/")
        if not username:
            return None
        return f"https://linkedin.com/in/{username}"

    if lower.startswith("in/"):
        username = lower.split("in/", 1)[-1].strip("/")
        if not username:
            return None
        return f"https://linkedin.com/in/{username}"

    username = re.sub(r"[^a-z0-9_-]+", "", lower)
    if not username:
        return None
    return f"https://linkedin.com/in/{username}"


def extract_json_object(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in AI response")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("AI response is not a JSON object")
    return payload


def split_full_name_with_ai(full_name: str) -> Tuple[str, str]:
    prompt = (
        "Split this person's full name into first_name and last_name.\n"
        "Return ONLY JSON with keys first_name and last_name.\n"
        "If there is only one name, put it in first_name and leave last_name empty.\n"
        f"Name: {full_name}"
    )
    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    text_response = next(
        (block.text for block in response.content if hasattr(block, "text")), ""
    )
    payload = extract_json_object(text_response)
    first_name = normalize_value(payload.get("first_name")) or ""
    last_name = normalize_value(payload.get("last_name")) or ""
    return first_name, last_name


def apply_mappings_to_row(
    row: Dict[str, Optional[str]],
    mappings: Dict[str, str],
) -> Dict[str, Optional[str]]:
    standardized: Dict[str, Optional[str]] = {}
    for source, target in mappings.items():
        if target == "skip" or target == "":
            continue
        # Allow both standard fields and custom fields
        value = normalize_value(row.get(source))
        if value is None:
            continue
        if not standardized.get(target):
            standardized[target] = value
    return standardized


def extract_json_mapping(text: str) -> Dict[str, str]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON mapping found in AI response")
    mapping = json.loads(match.group(0))
    if not isinstance(mapping, dict):
        raise ValueError("AI response mapping is not a JSON object")
    return {str(k): str(v) for k, v in mapping.items()}


def suggest_mappings_for_headers(headers: List[str]) -> Dict[str, str]:
    # Limit headers to prevent context overflow
    limited_headers = headers[:50] if len(headers) > 50 else headers
    
    prompt = f"""Map these CSV columns to standardized fields. Return ONLY valid JSON.

Target fields: {', '.join(STANDARDIZED_FIELDS)}

CSV columns to map:
{chr(10).join(f'- {h}' for h in limited_headers)}

Return a JSON object like this example:
{{"column_name": "target_field", "another_column": "skip"}}

Rules:
- Map to: first_name, last_name, full_name, linkedin_url, location, current_company, current_title
- Use "skip" for columns that don't match any target
- Only map if you're confident (leave uncertain ones as "skip")
- linkedin, LinkedIn URL, profile url -> linkedin_url
- name, full name, candidate name -> full_name
- first, firstname -> first_name
- last, lastname -> last_name
- company, employer, current company -> current_company
- title, job title, position -> current_title
- location, city, area -> location

Return ONLY the JSON object, no explanation:"""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text_response = next(
            (block.text for block in response.content if hasattr(block, "text")), ""
        )
        return extract_json_mapping(text_response)
    except Exception as e:
        # Fallback to simple pattern matching if AI fails
        print(f"AI mapping failed: {e}, using fallback")
        return fallback_mapping(limited_headers)


def fallback_mapping(headers: List[str]) -> Dict[str, str]:
    """Simple pattern matching when AI fails."""
    result = {}
    patterns = {
        "linkedin_url": ["linkedin", "profile url", "linkedin url", "linkedinurl"],
        "full_name": ["name", "full name", "fullname", "candidate name", "candidate.name"],
        "first_name": ["first", "firstname", "first name", "candidate.firstname"],
        "last_name": ["last", "lastname", "last name", "candidate.lastname"],
        "location": ["location", "city", "area", "geography", "candidate.location"],
        "current_company": ["company", "employer", "current company", "organization", "candidate.experiences.0.company"],
        "current_title": ["title", "job title", "position", "role", "candidate.experiences.0.title"],
    }
    
    for header in headers:
        header_lower = header.lower().strip()
        matched = False
        for target, keywords in patterns.items():
            if any(kw in header_lower for kw in keywords):
                result[header] = target
                matched = True
                break
        if not matched:
            result[header] = "skip"
    
    return result


def validate_mapping_payload(
    mappings: Dict[str, Dict[str, str]],
    custom_fields: List[str],
) -> Tuple[bool, str]:
    if not isinstance(mappings, dict):
        return False, "Invalid mappings payload"

    allowed_fields = set(STANDARDIZED_FIELDS) | set(custom_fields or [])
    has_linkedin = False

    for target_field, file_mappings in mappings.items():
        if target_field not in allowed_fields:
            return False, "Invalid target field in mappings"
        if target_field == "linkedin_url":
            has_linkedin = True
        if not isinstance(file_mappings, dict):
            return False, "Invalid mappings payload"
        for source_column in file_mappings.values():
            if not isinstance(source_column, str):
                return False, "Invalid mappings payload"

    if not has_linkedin or not any((mappings.get("linkedin_url") or {}).values()):
        return False, "linkedin_url mapping is required"

    return True, ""


def restandardize_run(run_id: str) -> None:
    """Re-run standardization on existing input files after chat modifications"""
    st = get_run_or_404(run_id)
    if not st:
        return
    st.state = "running"
    st.message = "Re-standardizing data..."
    save_run_to_db(st)
    
    run_dir = RUNS_DIR / st.run_name
    input_dir = run_dir / "input"
    output_dir = run_dir / "output"
    
    # Get all CSV files in input directory
    input_files = list(input_dir.glob("*.csv"))
    
    if not input_files:
        st.state = "error"
        save_run_to_db(st)
        st.message = "No input files found to re-standardize"
        return
    
    python_exe = str(REPO_ROOT / "venv" / "bin" / "python3")
    
    try:
        # Run standardization
        cmd_ingest = [
            python_exe,
            "-m",
            "ingestion.main",
        ] + [str(f) for f in input_files] + [
            "--output-dir",
            str(output_dir),
        ]
        subprocess.run(cmd_ingest, cwd=str(REPO_ROOT), check=True)
        
        # Load standardized data
        standardized = output_dir / "standardized_candidates.csv"
        standardized_rows = []
        with open(standardized, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                standardized_rows.append(row)
        
        st.state = "standardized"
        st.message = f"Re-standardization complete. {len(standardized_rows)} candidates ready for review."
        st.standardized_data = standardized_rows
        st.outputs = {
            "standardized": str(standardized.relative_to(REPO_ROOT)),
            "duplicates": str((output_dir / "duplicates_report.csv").relative_to(REPO_ROOT)) if (output_dir / "duplicates_report.csv").exists() else None,
        }
        save_run_to_db(st)
        
    except subprocess.CalledProcessError as e:
        st.state = "error"
        st.message = f"Re-standardization failed (exit {e.returncode})"
        save_run_to_db(st)
    except Exception as e:
        st.state = "error"
        st.message = f"Unexpected error during re-standardization: {e}"
        save_run_to_db(st)


def run_pipeline(run_id: str, input_paths: List[Path]) -> None:
    st = get_run_or_404(run_id)
    if not st:
        return
    st.state = "running"
    st.message = "Starting…"
    save_run_to_db(st)

    run_dir = RUNS_DIR / st.run_name
    input_dir = run_dir / "input"
    output_dir = run_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy inputs into run folder
    st.message = "Saving uploads…"
    save_run_to_db(st)
    for p in input_paths:
        shutil.copy2(p, input_dir / p.name)

    # Save metadata
    meta = {
        "run_id": st.run_id,
        "run_name": st.run_name,
        "role_label": st.role_label,
        "created_at": st.created_at,
        "input_files": [p.name for p in input_paths],
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    try:
        # 1) ingestion
        st.message = "Standardizing + deduping…"
        save_run_to_db(st)
        # Use python -m ingestion.main with glob
        python_exe = str(REPO_ROOT / "venv" / "bin" / "python3")
        cmd_ingest = [
            python_exe,
            "-m",
            "ingestion.main",
        ] + [str(input_dir / p.name) for p in input_paths] + [
            "--output-dir",
            str(output_dir),
        ]
        subprocess.run(cmd_ingest, cwd=str(REPO_ROOT), check=True)

        # STOP after standardization - load data for review
        standardized = output_dir / "standardized_candidates.csv"
        
        # Load standardized data
        standardized_rows = []
        with open(standardized, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                standardized_rows.append(row)
        
        st.state = "standardized"
        st.message = f"Standardization complete. {len(standardized_rows)} candidates ready for review."
        st.standardized_data = standardized_rows
        st.outputs = {
            "standardized": str(standardized.relative_to(REPO_ROOT)),
            "duplicates": str((output_dir / "duplicates_report.csv").relative_to(REPO_ROOT)) if (output_dir / "duplicates_report.csv").exists() else None,
        }
        save_run_to_db(st)

    except subprocess.CalledProcessError as e:
        st.state = "error"
        st.message = f"Pipeline failed (exit {e.returncode}). Check console logs on the machine running the UI."
        save_run_to_db(st)
    except Exception as e:
        st.state = "error"
        st.message = f"Unexpected error: {e}"
        save_run_to_db(st)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Redirect to roles page as the new entry point
    return RedirectResponse(url="/roles", status_code=302)


@app.get("/roles", response_class=HTMLResponse)
def roles_list(request: Request):
    roles = db.list_roles()
    return templates.TemplateResponse(
        "roles.html",
        {
            "request": request,
            "roles": roles,
        },
    )


@app.get("/roles/{role_id}", response_class=HTMLResponse)
def role_detail(request: Request, role_id: str):
    role = db.get_role(role_id)
    if not role:
        return HTMLResponse("Role not found", status_code=404)
    documents = db.list_role_documents(role_id)
    criteria = db.get_latest_criteria(role_id)
    batches = db.list_candidate_batches(role_id)
    return templates.TemplateResponse(
        "role.html",
        {
            "request": request,
            "role": role,
            "documents": documents,
            "criteria": criteria,
            "batches": batches,
        },
    )


@app.get("/api/roles")
def api_list_roles():
    """API endpoint to list all roles."""
    roles = db.list_roles()
    return JSONResponse({"roles": roles})


@app.post("/api/roles")
def api_create_role(
    name: str = Form(...),
    description: str = Form(default=""),
):
    """API endpoint to create a new role."""
    role_id = uuid.uuid4().hex
    db.create_role(role_id, name, description)
    return RedirectResponse(url=f"/roles/{role_id}", status_code=303)


@app.get("/old", response_class=HTMLResponse)
def old_home(request: Request):
    # Old workflow - keep for backwards compatibility
    recent = [dict_to_runstatus(r) for r in db.list_runs(20)]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "recent": recent,
            "stepper": build_stepper_context("upload"),
        },
    )


@app.post("/api/run")
def create_run(
    request: Request,
    run_name: str = Form(default=""),
    role_label: str = Form(default=""),
    files: List[UploadFile] = File(...),
):
    rid = uuid.uuid4().hex[:10]
    ts = time.strftime("%Y-%m-%d_%H%M")
    rn = safe_name(run_name) if run_name else f"{ts}_{rid}"
    rn = safe_name(rn)

    role = (role_label or "").strip()

    st = RunStatus(
        run_id=rid,
        created_at=time.time(),
        run_name=rn,
        role_label=role,
        state="queued",
        message="Queued",
    )
    save_run_to_db(st)

    # Save uploads into a temp folder first
    tmp_dir = RUNS_DIR / "_tmp" / rid
    tmp_dir.mkdir(parents=True, exist_ok=True)
    input_paths: List[Path] = []

    for f in files:
        fname = safe_name(Path(f.filename or "file.csv").name)
        if not fname.lower().endswith(".csv"):
            fname = fname + ".csv"
        out = tmp_dir / fname
        out.write_bytes(f.file.read())
        input_paths.append(out)

    # Run pipeline in background thread
    t = threading.Thread(target=run_pipeline, args=(rid, input_paths), daemon=True)
    t.start()

    return RedirectResponse(url=f"/runs/{rid}", status_code=303)


@app.post("/api/roles/{role_id}/batches/upload")
def upload_candidate_batch(
    role_id: str,
    files: Optional[List[UploadFile]] = File(default=None),
):
    if not files:
        return JSONResponse({"error": "No files uploaded"}, status_code=400)

    invalid_files = [
        f.filename for f in files if not (f.filename or "").lower().endswith(".csv")
    ]
    if invalid_files:
        return JSONResponse(
            {"error": "Only CSV files are supported", "files": invalid_files},
            status_code=400,
        )

    batch_name = f"Batch {time.strftime('%Y-%m-%d %H:%M')}"
    try:
        batch_id = db.create_candidate_batch(role_id, batch_name, "pending")
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to create batch: {exc}"},
            status_code=500,
        )

    batch_dir = UPLOADS_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    files_payload = []
    total_rows = 0

    for upload in files:
        original_name = Path(upload.filename or "file.csv").name
        filename = safe_filename(original_name)
        if not filename.lower().endswith(".csv"):
            filename = f"{filename}.csv"

        dest = batch_dir / filename
        with dest.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        upload.file.close()

        try:
            headers, row_count = read_csv_metadata(dest)
        except Exception as exc:
            return JSONResponse(
                {"error": f"Failed to read CSV {filename}: {exc}"},
                status_code=400,
            )

        total_rows += row_count
        db.insert_batch_file_upload(batch_id, filename, row_count, headers)
        files_payload.append(
            {
                "filename": filename,
                "row_count": row_count,
                "headers": headers,
            }
        )

    return JSONResponse(
        {
            "batch_id": batch_id,
            "role_id": role_id,
            "files": files_payload,
            "total_rows": total_rows,
        }
    )


def _is_url(path_value: Optional[str]) -> bool:
    return bool(path_value and path_value.startswith("http"))


def _normalize_criteria_lines(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return [str(value).strip()]


def _normalize_gating_params(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "job_hopper": False,
            "bootcamp_only": False,
            "location_mismatch": False,
            "custom_rule": "",
        }
    return {
        "job_hopper": bool(value.get("job_hopper")),
        "bootcamp_only": bool(value.get("bootcamp_only")),
        "location_mismatch": bool(value.get("location_mismatch")),
        "custom_rule": (value.get("custom_rule") or "").strip(),
    }


MAX_DOC_CHARS = 40000


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin1")


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_docx_text(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _load_document_text(doc: Dict[str, Any]) -> str:
    file_path = doc.get("file_path") or ""
    if _is_url(file_path):
        return f"URL: {file_path}"
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_text(path)
    if ext == ".docx":
        return _extract_docx_text(path)
    if ext in {".txt", ".csv"}:
        return _read_text_file(path)
    raise ValueError(f"Unsupported document type: {ext}")


def _truncate_text(text: str, limit: int = MAX_DOC_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[truncated]"


def _extract_criteria_from_text(
    jd_text: str,
    intake_text: Optional[str] = None,
    calibration_text: Optional[str] = None,
) -> Dict[str, List[str]]:
    sections = [
        ("Job Description", jd_text),
    ]
    if intake_text:
        sections.append(("Intake Form", intake_text))
    if calibration_text:
        sections.append(("Calibration Candidates", calibration_text))

    formatted_sections = "\n\n".join(
        f"{label}:\n\"\"\"\n{_truncate_text(text)}\n\"\"\"" for label, text in sections
    )

    prompt = (
        "Analyze the role documents and extract filtering criteria for recruiting.\n"
        "Return ONLY JSON with keys: must_haves, gating_params, nice_to_haves.\n"
        "Each value should be an array of concise strings.\n"
        "Gating params should describe disqualifiers such as job hopping, bootcamp-only, "
        "location mismatch, or other hard blockers.\n\n"
        f"{formatted_sections}"
    )

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text_response = next(
        (block.text for block in response.content if hasattr(block, "text")), ""
    )
    payload = extract_json_object(text_response)

    must_haves = _normalize_criteria_lines(payload.get("must_haves"))
    nice_to_haves = _normalize_criteria_lines(payload.get("nice_to_haves"))
    gating_raw = payload.get("gating_params")
    if isinstance(gating_raw, list):
        gating_params = [str(item).strip() for item in gating_raw if str(item).strip()]
    elif isinstance(gating_raw, dict):
        gating_params = [
            f"{key}: {value}".strip(": ").strip()
            for key, value in gating_raw.items()
            if f"{key}{value}".strip()
        ]
    else:
        gating_params = _normalize_criteria_lines(gating_raw)

    return {
        "must_haves": must_haves,
        "gating_params": gating_params,
        "nice_to_haves": nice_to_haves,
    }


@app.post("/api/roles/{role_id}/documents")
async def upload_role_document(
    role_id: str,
    doc_type: str = Form(...),
    file: Optional[UploadFile] = File(default=None),
    doc_url: str = Form(default=""),
):
    doc_type = (doc_type or "").strip().lower()
    if doc_type not in DOC_TYPE_CONFIG:
        return JSONResponse({"error": "Invalid doc_type"}, status_code=400)

    config = DOC_TYPE_CONFIG[doc_type]
    doc_url = (doc_url or "").strip()

    if file and doc_url:
        return JSONResponse(
            {"error": "Provide either a file or a URL, not both"},
            status_code=400,
        )

    if not file and not doc_url:
        return JSONResponse({"error": "No file or URL provided"}, status_code=400)

    if doc_url and not config["allow_url"]:
        return JSONResponse(
            {"error": "URL uploads not supported for this type"},
            status_code=400,
        )

    existing = db.get_role_document_by_type(role_id, doc_type)

    if doc_url:
        filename = doc_url
        file_path = doc_url
    else:
        original_name = Path(file.filename or "file").name
        filename = safe_filename(original_name)
        ext = Path(filename).suffix.lower()
        if ext not in config["extensions"]:
            return JSONResponse(
                {"error": f"Invalid file type for {doc_type}"},
                status_code=400,
            )

        role_dir = ROLE_UPLOADS_DIR / role_id
        role_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(role_dir / f"{doc_type}_{filename}")
        with open(file_path, "wb") as handle:
            shutil.copyfileobj(file.file, handle)
        file.file.close()

    if existing:
        previous_path = existing.get("file_path")
        db.update_role_document(existing["id"], filename, file_path)
        if (
            previous_path
            and not _is_url(previous_path)
            and previous_path != file_path
        ):
            previous_file = Path(previous_path)
            if previous_file.exists():
                previous_file.unlink()
        doc_id = existing["id"]
    else:
        doc_id = db.create_role_document(role_id, doc_type, filename, file_path)

    return JSONResponse(
        {
            "id": doc_id,
            "role_id": role_id,
            "doc_type": doc_type,
            "filename": filename,
            "file_path": file_path,
        }
    )


@app.get("/api/roles/{role_id}/documents")
def list_role_documents(role_id: str):
    documents = db.list_role_documents(role_id)
    return JSONResponse(
        {
            "role_id": role_id,
            "documents": documents,
        }
    )


@app.delete("/api/roles/{role_id}/documents/{doc_id}")
def delete_role_document(role_id: str, doc_id: str):
    document = db.get_role_document(doc_id)
    if not document or document.get("role_id") != role_id:
        return JSONResponse({"error": "Document not found"}, status_code=404)

    file_path = document.get("file_path")
    if file_path and not _is_url(file_path):
        path = Path(file_path)
        if path.exists():
            path.unlink()

    db.delete_role_document(doc_id)
    return JSONResponse({"success": True, "id": doc_id})


@app.post("/api/roles/{role_id}/analyze-documents")
def analyze_role_documents(role_id: str):
    if not db.get_role_name(role_id):
        return JSONResponse({"error": "Role not found"}, status_code=404)

    jd_doc = db.get_role_document_by_type(role_id, "jd")
    if not jd_doc:
        return JSONResponse(
            {"error": "Job Description document is required"},
            status_code=400,
        )

    try:
        jd_text = _load_document_text(jd_doc)
        intake_doc = db.get_role_document_by_type(role_id, "intake")
        calibration_doc = db.get_role_document_by_type(role_id, "calibration")
        intake_text = _load_document_text(intake_doc) if intake_doc else None
        calibration_text = (
            _load_document_text(calibration_doc) if calibration_doc else None
        )
        criteria = _extract_criteria_from_text(
            jd_text,
            intake_text=intake_text,
            calibration_text=calibration_text,
        )
    except Exception as exc:
        logger.exception("Failed to analyze role documents role_id=%s", role_id)
        return JSONResponse(
            {"error": f"Failed to analyze documents: {exc}"},
            status_code=500,
        )

    return JSONResponse(criteria)


@app.get("/api/roles/{role_id}/criteria")
def get_role_criteria(role_id: str):
    if not db.get_role_name(role_id):
        return JSONResponse({"error": "Role not found"}, status_code=404)

    criteria = db.get_latest_role_criteria(role_id)
    return JSONResponse({"role_id": role_id, "criteria": criteria})


@app.get("/api/roles/{role_id}/criteria/history")
def get_role_criteria_history(role_id: str):
    if not db.get_role_name(role_id):
        return JSONResponse({"error": "Role not found"}, status_code=404)

    history = db.list_role_criteria_history(role_id)
    return JSONResponse({"role_id": role_id, "history": history})


@app.post("/api/roles/{role_id}/criteria")
def create_role_criteria(role_id: str, payload: Dict[str, Any] = Body(...)):
    if not db.get_role_name(role_id):
        return JSONResponse({"error": "Role not found"}, status_code=404)

    latest = db.get_latest_role_criteria(role_id)
    if latest and latest.get("is_locked"):
        return JSONResponse(
            {"error": "Criteria locked after approved test run"},
            status_code=403,
        )

    must_haves = _normalize_criteria_lines(payload.get("must_haves"))
    nice_to_haves = _normalize_criteria_lines(payload.get("nice_to_haves"))
    gating_params = _normalize_gating_params(payload.get("gating_params"))

    try:
        criteria = db.create_role_criteria(
            role_id, must_haves, gating_params, nice_to_haves
        )
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to save criteria: {exc}"},
            status_code=500,
        )

    return JSONResponse({"role_id": role_id, "criteria": criteria})


@app.post("/api/roles/{role_id}/criteria/{criteria_id}/lock")
def lock_role_criteria(role_id: str, criteria_id: str):
    criteria = db.get_role_criteria(criteria_id)
    if not criteria or criteria.get("role_id") != role_id:
        return JSONResponse({"error": "Criteria not found"}, status_code=404)

    if criteria.get("is_locked"):
        return JSONResponse({"role_id": role_id, "criteria": criteria})

    try:
        locked = db.lock_role_criteria(criteria_id)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to lock criteria: {exc}"},
            status_code=500,
        )

    if not locked:
        return JSONResponse({"error": "Criteria not found"}, status_code=404)

    return JSONResponse({"role_id": role_id, "criteria": locked})


@app.post("/api/batches/{batch_id}/suggest-mappings")
def suggest_batch_mappings(batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    uploads = db.list_batch_file_uploads(batch_id)
    files_payload = []

    for upload in uploads:
        headers = upload.get("headers") or []
        try:
            suggested_mappings = suggest_mappings_for_headers(headers)
        except Exception as exc:
            return JSONResponse(
                {"error": f"AI mapping failed: {exc}"},
                status_code=500,
            )
        files_payload.append(
            {
                "filename": upload.get("filename"),
                "headers": headers,
                "suggested_mappings": suggested_mappings,
            }
        )

    return JSONResponse(
        {
            "batch_id": batch_id,
            "files": files_payload,
            "standardized_fields": STANDARDIZED_FIELDS,
        }
    )


@app.post("/api/batches/{batch_id}/apply-mappings")
def apply_batch_mappings(
    batch_id: str,
    payload: Dict[str, Any] = Body(...),
):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    # New grid format: { mappings: {target: {filename: source}}, custom_fields: [] }
    mappings = payload.get("mappings", {})
    custom_fields = payload.get("custom_fields", [])

    if not mappings:
        return JSONResponse({"error": "No mappings provided"}, status_code=400)

    is_valid, error_message = validate_mapping_payload(mappings, custom_fields)
    if not is_valid:
        return JSONResponse({"error": error_message}, status_code=400)

    uploads = db.list_batch_file_uploads(batch_id)
    if not uploads:
        return JSONResponse({"error": "No files found for batch"}, status_code=400)

    # Convert grid format to file-centric format for processing
    # mappings_by_filename: {filename: {source_col: target_field}}
    mappings_by_filename: Dict[str, Dict[str, str]] = {}

    for target_field, file_mappings in mappings.items():
        for filename, source_column in file_mappings.items():
            if filename not in mappings_by_filename:
                mappings_by_filename[filename] = {}
            mappings_by_filename[filename][source_column] = target_field

    total_uploaded = sum(upload.get("row_count") or 0 for upload in uploads)
    seen_linkedin: set[str] = set()
    candidates_payload: List[Dict[str, Any]] = []
    deduplicated_count = 0
    final_count = 0
    name_split_cache: Dict[str, Tuple[str, str]] = {}

    logger.info(
        "Applying mappings for batch %s with %d files and %d custom fields",
        batch_id,
        len(uploads),
        len(custom_fields),
    )

    for upload in uploads:
        filename = upload.get("filename")
        if not filename:
            continue
        file_path = UPLOADS_DIR / batch_id / filename
        if not file_path.exists():
            return JSONResponse(
                {"error": f"Missing file on disk: {filename}"},
                status_code=400,
            )
        df = read_csv_with_fallback(file_path)
        file_mappings = mappings_by_filename.get(filename, {})
        logger.info(
            "Processing %s with %d rows and %d mapped columns",
            filename,
            len(df.index),
            len(file_mappings),
        )

        for _, row in df.iterrows():
            raw_row = row.to_dict()
            standardized_data = apply_mappings_to_row(raw_row, file_mappings)

            full_name = normalize_value(standardized_data.get("full_name"))
            if full_name and not standardized_data.get("first_name") and not standardized_data.get(
                "last_name"
            ):
                cached = name_split_cache.get(full_name)
                if cached:
                    first_name, last_name = cached
                else:
                    parts = full_name.split()
                    if len(parts) == 1:
                        first_name, last_name = parts[0], ""
                    elif len(parts) == 2:
                        first_name, last_name = parts[0], parts[1]
                    else:
                        try:
                            first_name, last_name = split_full_name_with_ai(full_name)
                        except Exception as exc:
                            logger.warning(
                                "AI name split failed for '%s': %s",
                                full_name,
                                exc,
                            )
                            first_name, last_name = parts[0], " ".join(parts[1:])
                    name_split_cache[full_name] = (first_name, last_name)
                standardized_data["first_name"] = first_name
                standardized_data["last_name"] = last_name

            # Handle custom fields
            for custom_field in custom_fields:
                if custom_field in file_mappings.values():
                    # Find which source column maps to this custom field
                    for source_col, target_field in file_mappings.items():
                        if target_field == custom_field:
                            value = normalize_value(raw_row.get(source_col))
                            if value:
                                standardized_data[custom_field] = value

            linkedin_url = normalize_linkedin_url(standardized_data.get("linkedin_url"))
            standardized_data["linkedin_url"] = linkedin_url
            normalized_key = linkedin_url.lower() if linkedin_url else ""
            status = "standardized"
            if normalized_key:
                if normalized_key in seen_linkedin:
                    status = "duplicate"
                    deduplicated_count += 1
                else:
                    seen_linkedin.add(normalized_key)
            if status == "standardized":
                final_count += 1

            candidates_payload.append(
                {
                    "first_name": standardized_data.get("first_name"),
                    "last_name": standardized_data.get("last_name"),
                    "full_name": standardized_data.get("full_name"),
                    "linkedin_url": linkedin_url,
                    "location": standardized_data.get("location"),
                    "current_company": standardized_data.get("current_company"),
                    "current_title": standardized_data.get("current_title"),
                    "raw_data": raw_row,
                    "standardized_data": standardized_data,
                    "status": status,
                }
            )

    try:
        db.insert_raw_candidates(batch_id, batch.get("role_id"), candidates_payload)
        db.update_candidate_batch_status(batch_id, "standardized")
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to apply mappings: {exc}"},
            status_code=500,
        )

    logger.info(
        "Applied mappings for batch %s: total=%d standardized=%d duplicates=%d",
        batch_id,
        total_uploaded,
        final_count,
        deduplicated_count,
    )

    return JSONResponse(
        {
            "success": True,
            "total": total_uploaded,
            "standardized": final_count,
            "duplicates": deduplicated_count,
        }
    )


@app.get("/api/batches/{batch_id}/candidates")
def list_batch_candidates(batch_id: str, view: str = "standardized"):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    normalized_view = (view or "standardized").lower()
    if normalized_view not in {"raw", "standardized", "comparison"}:
        return JSONResponse({"error": "Invalid view"}, status_code=400)

    candidates = db.list_raw_candidates(batch_id, exclude_duplicates=True)
    metrics = db.get_batch_metrics(batch_id)

    custom_field_set: Set[str] = set()
    for candidate in candidates:
        standardized_data = candidate.get("standardized_data") or {}
        if isinstance(standardized_data, dict):
            for key in standardized_data:
                if key not in STANDARDIZED_FIELDS:
                    custom_field_set.add(key)
    custom_fields = sorted(custom_field_set)

    candidates_payload: List[Dict[str, Any]] = []
    for candidate in candidates:
        standardized_data = candidate.get("standardized_data") or {}
        custom_payload: Dict[str, Any] = {}
        if isinstance(standardized_data, dict):
            for field in custom_fields:
                custom_payload[field] = standardized_data.get(field)

        if normalized_view == "raw":
            candidates_payload.append({"raw_data": candidate.get("raw_data")})
            continue

        standardized_payload = {
            "first_name": candidate.get("first_name"),
            "last_name": candidate.get("last_name"),
            "full_name": candidate.get("full_name"),
            "linkedin_url": candidate.get("linkedin_url"),
            "location": candidate.get("location"),
            "current_company": candidate.get("current_company"),
            "current_title": candidate.get("current_title"),
            **custom_payload,
        }

        if normalized_view == "comparison":
            candidates_payload.append(
                {
                    "raw_data": candidate.get("raw_data"),
                    **standardized_payload,
                }
            )
        else:
            candidates_payload.append(standardized_payload)

    return JSONResponse(
        {
            "batch_id": batch_id,
            "batch_name": batch.get("name"),
            "batch_status": batch.get("status"),
            "view": normalized_view,
            "candidates": candidates_payload,
            "custom_fields": custom_fields,
            "total_uploaded": metrics["total_uploaded"],
            "deduplicated_count": metrics["deduplicated_count"],
            "final_count": metrics["final_count"],
            "file_count": metrics["file_count"],
        }
    )


@app.get("/api/batches/{batch_id}/duplicates")
def list_batch_duplicates(batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    duplicates = db.list_duplicate_candidates(batch_id)
    metrics = db.get_batch_metrics(batch_id)
    duplicates_payload = []
    for candidate in duplicates:
        duplicates_payload.append(
            {
                "first_name": candidate.get("first_name"),
                "last_name": candidate.get("last_name"),
                "full_name": candidate.get("full_name"),
                "linkedin_url": candidate.get("linkedin_url"),
            }
        )

    return JSONResponse(
        {
            "batch_id": batch_id,
            "batch_name": batch.get("name"),
            "duplicates": duplicates_payload,
            "deduplicated_count": metrics["deduplicated_count"],
        }
    )


@app.get("/api/batches/{batch_id}/duplicates/export")
def export_batch_duplicates(batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    role_name = db.get_role_name(batch.get("role_id") or "") or batch.get("role_id")
    safe_role = safe_name(role_name or "role")
    date_stamp = time.strftime("%Y-%m-%d")
    filename = f"duplicates_{safe_role}_{date_stamp}.csv"

    duplicates = db.list_duplicate_candidates(batch_id)
    buffer = StringIO()
    fieldnames = ["full_name", "first_name", "last_name", "linkedin_url"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for candidate in duplicates:
        writer.writerow({field: candidate.get(field) or "" for field in fieldnames})

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/batches/{batch_id}/export")
def export_batch_candidates(batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    role_name = db.get_role_name(batch.get("role_id") or "") or batch.get("role_id")
    safe_role = safe_name(role_name or "role")
    date_stamp = time.strftime("%Y-%m-%d")
    filename = f"standardized_{safe_role}_{date_stamp}.csv"

    candidates = db.list_standardized_candidates(batch_id)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=STANDARDIZED_FIELDS)
    writer.writeheader()
    for candidate in candidates:
        writer.writerow({field: candidate.get(field) or "" for field in STANDARDIZED_FIELDS})

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/batches/{batch_id}/approve")
def approve_batch(batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    if batch.get("status") == "approved":
        return JSONResponse(
            {
                "batch_id": batch_id,
                "status": batch.get("status"),
                "approved_at": batch.get("approved_at"),
            }
        )

    try:
        updated = db.approve_candidate_batch(batch_id)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to approve batch: {exc}"},
            status_code=500,
        )

    if not updated:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    return JSONResponse(
        {
            "batch_id": updated.get("id"),
            "status": updated.get("status"),
            "approved_at": updated.get("approved_at"),
        }
    )


def _candidate_display_name(candidate: Dict[str, Any]) -> str:
    full_name = (candidate.get("full_name") or "").strip()
    if full_name:
        return full_name
    first = (candidate.get("first_name") or "").strip()
    last = (candidate.get("last_name") or "").strip()
    if first or last:
        return f"{first} {last}".strip()
    return candidate.get("linkedin_url") or "Unknown"


def _build_empty_evaluations(
    criteria: Dict[str, Any], reason: str
) -> Dict[str, List[Dict[str, str]]]:
    must_haves = criteria.get("must_haves") or []
    gating_params = build_gating_param_list(criteria.get("gating_params"))
    nice_to_haves = criteria.get("nice_to_haves") or []
    make_entries = lambda items: [
        {"criterion": item, "status": "Unsure", "reason": reason}
        for item in items
    ]
    return {
        "must_haves": make_entries(must_haves),
        "gating_params": make_entries(gating_params),
        "nice_to_haves": make_entries(nice_to_haves),
    }


def _criteria_columns(criteria: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "must_haves": criteria.get("must_haves") or [],
        "gating_params": build_gating_param_list(criteria.get("gating_params")),
        "nice_to_haves": criteria.get("nice_to_haves") or [],
    }


def _flatten_evaluations(
    criteria_evaluations: Dict[str, Any]
) -> Dict[str, Dict[str, str]]:
    flattened: Dict[str, Dict[str, str]] = {}
    for section in ("must_haves", "gating_params", "nice_to_haves"):
        for entry in criteria_evaluations.get(section, []) or []:
            if not isinstance(entry, dict):
                continue
            criterion = (entry.get("criterion") or "").strip()
            if not criterion:
                continue
            flattened[criterion] = {
                "status": entry.get("status") or "Unsure",
                "reason": entry.get("reason") or "Insufficient information.",
            }
    return flattened


def run_test_run(
    test_run_id: str,
    candidate_ids: List[str],
    criteria: Dict[str, Any],
) -> None:
    logger.info(
        "Starting test run %s with %d candidates", test_run_id, len(candidate_ids)
    )
    candidates = db.list_candidates_by_ids(candidate_ids)
    candidate_map = {candidate["id"]: candidate for candidate in candidates}
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = Anthropic(api_key=api_key) if api_key else None
    for idx, candidate_id in enumerate(candidate_ids, start=1):
        candidate = candidate_map.get(candidate_id, {})
        candidate_name = _candidate_display_name(candidate)
        candidate_linkedin = candidate.get("linkedin_url")
        try:
            evaluation = evaluate_candidate(candidate, criteria, client=client)
            criteria_evaluations = evaluation.get("evaluations", {})
            final_bucket = evaluation.get("bucket", "Unable to Enrich")
        except Exception as exc:
            logger.exception(
                "Test run evaluation failed test_run_id=%s candidate_id=%s",
                test_run_id,
                candidate_id,
            )
            criteria_evaluations = _build_empty_evaluations(
                criteria, "Evaluation error."
            )
            final_bucket = "Unable to Enrich"
        db.insert_test_run_result(
            test_run_id=test_run_id,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            candidate_linkedin=candidate_linkedin,
            criteria_evaluations=criteria_evaluations,
            final_bucket=final_bucket,
        )
        logger.info(
            "Test run %s progress: %d/%d",
            test_run_id,
            idx,
            len(candidate_ids),
        )


def run_filter_run(
    run_id: str,
    candidates: List[Dict[str, Any]],
    criteria: Dict[str, Any],
) -> None:
    logger.info("Starting filter run %s with %d candidates", run_id, len(candidates))
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = Anthropic(api_key=api_key) if api_key else None
    bucket_counts = {
        "Proceed": 0,
        "Human Review": 0,
        "Dismiss": 0,
        "Unable to Enrich": 0,
    }
    for idx, candidate in enumerate(candidates, start=1):
        candidate_id = candidate.get("id") or ""
        candidate_name = _candidate_display_name(candidate)
        candidate_linkedin = candidate.get("linkedin_url")
        candidate_email = None
        standardized_data = candidate.get("standardized_data") or {}
        if isinstance(standardized_data, dict):
            candidate_email = standardized_data.get("email")
        try:
            evaluation = evaluate_candidate(candidate, criteria, client=client)
            criteria_evaluations = evaluation.get("evaluations", {})
            final_bucket = evaluation.get("bucket", "Unable to Enrich")
        except Exception:
            logger.exception(
                "Filter run evaluation failed run_id=%s candidate_id=%s",
                run_id,
                candidate_id,
            )
            criteria_evaluations = _build_empty_evaluations(
                criteria, "Evaluation error."
            )
            final_bucket = "Unable to Enrich"
        db.insert_filter_result(
            run_id=run_id,
            candidate_id=candidate_id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            candidate_linkedin=candidate_linkedin,
            criteria_evaluations=criteria_evaluations,
            final_determination=final_bucket,
        )
        if final_bucket in bucket_counts:
            bucket_counts[final_bucket] += 1
        db.update_filter_run_progress(run_id, idx, bucket_counts)
        logger.info("Filter run %s progress: %d/%d", run_id, idx, len(candidates))
    db.complete_filter_run(run_id, "completed")


@app.post("/api/roles/{role_id}/test-runs")
def create_test_run(role_id: str, payload: Dict[str, Any] = Body(...)):
    batch_id = payload.get("batch_id")
    criteria_version_id = payload.get("criteria_version_id")

    if not batch_id:
        return JSONResponse({"error": "batch_id is required"}, status_code=400)

    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    criteria_data: Dict[str, Any] = {}
    if criteria_version_id:
        criteria_version = db.get_criteria_version(criteria_version_id)
        if not criteria_version:
            return JSONResponse(
                {"error": "Criteria version not found"},
                status_code=404,
            )
        criteria_data = criteria_version.get("criteria_data") or {}
    else:
        criteria = db.get_latest_role_criteria(role_id)
        if not criteria:
            return JSONResponse(
                {"error": "No criteria configured for role"},
                status_code=400,
            )
        try:
            criteria_version_id = db.ensure_criteria_version(criteria)
        except Exception as exc:
            return JSONResponse(
                {"error": f"Failed to prepare criteria version: {exc}"},
                status_code=500,
            )
        criteria_data = criteria

    candidate_ids = db.list_random_standardized_candidate_ids(batch_id, limit=50)
    if len(candidate_ids) < 50:
        return JSONResponse(
            {"error": "At least 50 standardized candidates are required"},
            status_code=400,
        )

    try:
        test_run_id = db.create_test_run(
            role_id, criteria_version_id, candidate_ids
        )
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to create test run: {exc}"},
            status_code=500,
        )

    threading.Thread(
        target=run_test_run,
        args=(test_run_id, candidate_ids, criteria_data),
        daemon=True,
    ).start()

    return JSONResponse(
        {
            "test_run_id": test_run_id,
            "role_id": role_id,
            "batch_id": batch_id,
            "criteria_version_id": criteria_version_id,
            "candidate_count": len(candidate_ids),
        }
    )


@app.post("/api/batches/{batch_id}/test-run")
def start_batch_test_run(batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    role_id = batch.get("role_id")
    criteria = db.get_latest_role_criteria(role_id)
    if not criteria:
        return JSONResponse(
            {"error": "No criteria configured for role"},
            status_code=400,
        )

    try:
        criteria_version_id = db.ensure_criteria_version(criteria)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to prepare criteria version: {exc}"},
            status_code=500,
        )

    candidate_ids = db.list_random_standardized_candidate_ids(batch_id, limit=50)
    if len(candidate_ids) < 50:
        return JSONResponse(
            {"error": "At least 50 standardized candidates are required"},
            status_code=400,
        )

    try:
        test_run_id = db.create_test_run(
            role_id, criteria_version_id, candidate_ids
        )
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to create test run: {exc}"},
            status_code=500,
        )

    threading.Thread(
        target=run_test_run,
        args=(test_run_id, candidate_ids, criteria),
        daemon=True,
    ).start()

    return JSONResponse(
        {
            "test_run_id": test_run_id,
            "role_id": role_id,
            "batch_id": batch_id,
            "criteria_version_id": criteria_version_id,
            "criteria_version": criteria.get("version"),
            "candidate_count": len(candidate_ids),
        }
    )


@app.get("/api/test-runs/{test_run_id}")
def get_test_run_status(test_run_id: str):
    test_run = db.get_test_run(test_run_id)
    if not test_run:
        return JSONResponse({"error": "Test run not found"}, status_code=404)

    criteria_version = db.get_criteria_version(test_run["criteria_version_id"])
    criteria_data = criteria_version.get("criteria_data") if criteria_version else {}
    criteria_columns = _criteria_columns(criteria_data)

    results = db.list_test_run_results(test_run_id)
    evaluated_count = len(results)
    candidate_count = len(test_run.get("candidate_ids") or [])
    status = "complete" if evaluated_count >= candidate_count else "running"

    bucket_counts = {
        "Proceed": 0,
        "Human Review": 0,
        "Dismiss": 0,
        "Unable to Enrich": 0,
    }
    for result in results:
        bucket = result.get("final_bucket")
        if bucket in bucket_counts:
            bucket_counts[bucket] += 1

    return JSONResponse(
        {
            "test_run_id": test_run_id,
            "role_id": test_run.get("role_id"),
            "criteria_version_id": test_run.get("criteria_version_id"),
            "criteria_version": criteria_version.get("version")
            if criteria_version
            else None,
            "candidate_count": candidate_count,
            "evaluated_count": evaluated_count,
            "status": status,
            "criteria_columns": criteria_columns,
            "results": results,
            "bucket_counts": bucket_counts,
        }
    )


@app.post("/api/test-runs/{test_run_id}/stop")
def stop_test_run(test_run_id: str):
    """Stop a running test run."""
    test_run = db.get_test_run(test_run_id)
    if not test_run:
        return JSONResponse({"error": "Test run not found"}, status_code=404)
    
    # Mark the test run as stopped
    db.update_test_run_status(test_run_id, "stopped")
    
    return JSONResponse({
        "test_run_id": test_run_id,
        "status": "stopped",
        "message": "Test run stopped successfully"
    })


@app.post("/api/batches/{batch_id}/run-full")
def start_full_run(batch_id: str, count: int = 0):
    batch = db.get_candidate_batch(batch_id)
    if not batch:
        return JSONResponse({"error": "Batch not found"}, status_code=404)

    role_id = batch.get("role_id")
    criteria = db.get_latest_role_criteria(role_id)
    if not criteria:
        return JSONResponse(
            {"error": "No criteria configured for role"},
            status_code=400,
        )

    try:
        criteria_version_id = db.ensure_criteria_version(criteria)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to prepare criteria version: {exc}"},
            status_code=500,
        )

    metrics = db.get_batch_metrics(batch_id)
    total_available = metrics.get("final_count", 0)
    if total_available <= 0:
        return JSONResponse(
            {"error": "No standardized candidates available"},
            status_code=400,
        )

    if count < 0:
        return JSONResponse({"error": "count must be positive"}, status_code=400)

    run_count = total_available if count in (0, None) else min(count, total_available)
    run_type = "full"
    randomize = False
    if run_count < total_available:
        run_type = "subset"
        randomize = True

    candidates = db.list_standardized_candidates_for_batch(
        batch_id, limit=run_count, randomize=randomize
    )
    if not candidates:
        return JSONResponse(
            {"error": "No standardized candidates available"},
            status_code=400,
        )

    try:
        run_id = db.create_filter_run(
            role_id=role_id,
            criteria_version_id=criteria_version_id,
            run_type=run_type,
            batch_id=batch_id,
            batch_name=batch.get("name"),
            total_candidates=len(candidates),
        )
    except Exception as exc:
        return JSONResponse(
            {"error": f"Failed to create filter run: {exc}"},
            status_code=500,
        )

    def _run_full() -> None:
        try:
            run_filter_run(run_id, candidates, criteria)
        except Exception:
            logger.exception("Filter run failed run_id=%s", run_id)
            db.complete_filter_run(run_id, "failed")

    threading.Thread(target=_run_full, daemon=True).start()

    return JSONResponse(
        {
            "run_id": run_id,
            "role_id": role_id,
            "batch_id": batch_id,
            "criteria_version_id": criteria_version_id,
            "criteria_version": criteria.get("version"),
            "candidate_count": len(candidates),
            "run_type": run_type,
        }
    )


@app.get("/api/filter-runs/{run_id}")
def get_filter_run_status(run_id: str):
    run = db.get_filter_run(run_id)
    if not run:
        return JSONResponse({"error": "Run not found"}, status_code=404)

    criteria_version = db.get_criteria_version(run["criteria_version_id"])
    criteria_data = criteria_version.get("criteria_data") if criteria_version else {}
    criteria_columns = _criteria_columns(criteria_data)

    results = db.list_filter_results(run_id)
    status = run.get("status") or "running"
    bucket_counts = {
        "Proceed": run.get("proceed_count") or 0,
        "Human Review": run.get("review_count") or 0,
        "Dismiss": run.get("dismiss_count") or 0,
        "Unable to Enrich": run.get("unable_to_enrich_count") or 0,
    }

    return JSONResponse(
        {
            "run_id": run_id,
            "role_id": run.get("role_id"),
            "criteria_version_id": run.get("criteria_version_id"),
            "criteria_version": criteria_version.get("version")
            if criteria_version
            else None,
            "run_type": run.get("run_type"),
            "batch_id": run.get("input_csv_path"),
            "batch_name": run.get("input_csv_filename"),
            "candidate_count": run.get("total_candidates") or 0,
            "evaluated_count": run.get("current_candidate") or 0,
            "status": status,
            "criteria_columns": criteria_columns,
            "results": results,
            "bucket_counts": bucket_counts,
        }
    )


@app.get("/api/batches/{batch_id}/runs/latest")
def get_latest_run_for_batch(batch_id: str, role_id: str):
    latest = db.get_latest_filter_run_for_batch(role_id, batch_id)
    if not latest:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    return JSONResponse(
        {
            "run_id": latest.get("id"),
            "status": latest.get("status"),
            "created_at": latest.get("created_at"),
        }
    )


@app.get("/api/filter-runs/{run_id}/export")
def export_filter_run(run_id: str, bucket: Optional[str] = None):
    run = db.get_filter_run(run_id)
    if not run:
        return JSONResponse({"error": "Run not found"}, status_code=404)

    criteria_version = db.get_criteria_version(run["criteria_version_id"])
    criteria_data = criteria_version.get("criteria_data") if criteria_version else {}
    criteria_columns = _criteria_columns(criteria_data)
    criteria_labels: List[str] = []
    for key in ("must_haves", "gating_params", "nice_to_haves"):
        criteria_labels.extend(criteria_columns.get(key, []))

    results = db.list_filter_results(run_id)
    if bucket and bucket != "All":
        results = [r for r in results if r.get("final_bucket") == bucket]

    custom_fields: Set[str] = set()
    for result in results:
        standardized_data = result.get("standardized_data")
        if isinstance(standardized_data, dict):
            custom_fields.update(standardized_data.keys())

    base_fields = [
        "candidate_id",
        "first_name",
        "last_name",
        "full_name",
        "linkedin_url",
        "location",
        "current_company",
        "current_title",
    ]
    custom_field_list = sorted(custom_fields)
    criteria_headers: List[str] = []
    for label in criteria_labels:
        criteria_headers.append(f"{label} - status")
        criteria_headers.append(f"{label} - reason")
    headers = (
        base_fields
        + custom_field_list
        + ["raw_data_json", "standardized_data_json", "bucket"]
        + criteria_headers
    )

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for result in results:
        standardized_data = result.get("standardized_data") or {}
        raw_data = result.get("raw_data") or {}
        row = {
            "candidate_id": result.get("candidate_id"),
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
            "full_name": result.get("full_name"),
            "linkedin_url": result.get("linkedin_url")
            or result.get("candidate_linkedin"),
            "location": result.get("location"),
            "current_company": result.get("current_company"),
            "current_title": result.get("current_title"),
            "raw_data_json": json.dumps(raw_data, ensure_ascii=False),
            "standardized_data_json": json.dumps(
                standardized_data, ensure_ascii=False
            ),
            "bucket": result.get("final_bucket"),
        }
        for field in custom_field_list:
            row[field] = standardized_data.get(field)
        evaluation_map = _flatten_evaluations(
            result.get("criteria_evaluations") or {}
        )
        for label in criteria_labels:
            entry = evaluation_map.get(label, {})
            row[f"{label} - status"] = entry.get("status", "Unsure")
            row[f"{label} - reason"] = entry.get(
                "reason", "Insufficient information."
            )
        writer.writerow(row)

    filename = f"filter_results_{run_id}.csv"
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str):
    st = get_run_or_404(run_id)
    if not st:
        return HTMLResponse("Run not found", status_code=404)

    run_step_map = {
        "queued": "upload",
        "running": "standardize",
        "standardized": "review",
        "evaluating": "filter",
        "done": "results",
        "error": "results",
    }
    current_step = run_step_map.get(st.state, "results")

    return templates.TemplateResponse(
        "run.html",
        {
            "request": request,
            "run": st,
            "run_json": json.dumps(asdict(st), indent=2),
            "stepper": build_stepper_context(current_step),
        },
    )


@app.get("/roles/{role_id}/batches/{batch_id}/map", response_class=HTMLResponse)
def map_fields_page(request: Request, role_id: str, batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return HTMLResponse("Batch not found", status_code=404)

    return templates.TemplateResponse(
        "map.html",
        {
            "request": request,
            "role_id": role_id,
            "batch_id": batch_id,
            "stepper": build_stepper_context(
                step_from_batch_status(batch.get("status")), role_id, batch_id
            ),
        },
    )


@app.get("/roles/{role_id}/batches/{batch_id}/review", response_class=HTMLResponse)
def review_batch_page(request: Request, role_id: str, batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return HTMLResponse("Batch not found", status_code=404)

    return templates.TemplateResponse(
        "review.html",
        {
            "request": request,
            "role_id": role_id,
            "batch_id": batch_id,
            "stepper": build_stepper_context(
                step_from_batch_status(batch.get("status")), role_id, batch_id
            ),
        },
    )


@app.get("/roles/{role_id}/batches/{batch_id}/duplicates", response_class=HTMLResponse)
def duplicates_page(request: Request, role_id: str, batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return HTMLResponse("Batch not found", status_code=404)

    return templates.TemplateResponse(
        "duplicates.html",
        {
            "request": request,
            "role_id": role_id,
            "batch_id": batch_id,
            "stepper": build_stepper_context(
                step_from_batch_status(batch.get("status")), role_id, batch_id
            ),
        },
    )


@app.get("/roles/{role_id}/batches/{batch_id}/test-run", response_class=HTMLResponse)
def test_run_page(request: Request, role_id: str, batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return HTMLResponse("Batch not found", status_code=404)

    metrics = db.get_batch_metrics(batch_id)
    role_name = db.get_role_name(role_id)
    criteria = db.get_latest_role_criteria(role_id)

    return templates.TemplateResponse(
        "test_run.html",
        {
            "request": request,
            "role_id": role_id,
            "batch_id": batch_id,
            "role_name": role_name,
            "batch_name": batch.get("name"),
            "batch_status": batch.get("status"),
            "file_count": metrics["file_count"],
            "final_count": metrics["final_count"],
            "criteria": criteria,
            "stepper": build_stepper_context(
                step_from_batch_status(batch.get("status")), role_id, batch_id
            ),
        },
    )


@app.get("/roles/{role_id}/batches/{batch_id}/run", response_class=HTMLResponse)
def full_run_page(request: Request, role_id: str, batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return HTMLResponse("Batch not found", status_code=404)

    metrics = db.get_batch_metrics(batch_id)
    role_name = db.get_role_name(role_id)
    criteria = db.get_latest_role_criteria(role_id)

    return templates.TemplateResponse(
        "run_full.html",
        {
            "request": request,
            "role_id": role_id,
            "batch_id": batch_id,
            "role_name": role_name,
            "batch_name": batch.get("name"),
            "batch_status": batch.get("status"),
            "final_count": metrics["final_count"],
            "criteria": criteria,
            "stepper": build_stepper_context("filter", role_id, batch_id),
        },
    )


@app.get("/roles/{role_id}/batches/{batch_id}/results", response_class=HTMLResponse)
def results_page(request: Request, role_id: str, batch_id: str):
    batch = db.get_candidate_batch(batch_id)
    if not batch or batch.get("role_id") != role_id:
        return HTMLResponse("Batch not found", status_code=404)

    role_name = db.get_role_name(role_id)
    run_id = request.query_params.get("run_id")
    if not run_id:
        latest = db.get_latest_filter_run_for_batch(role_id, batch_id)
        run_id = latest.get("id") if latest else ""

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "role_id": role_id,
            "batch_id": batch_id,
            "role_name": role_name,
            "batch_name": batch.get("name"),
            "run_id": run_id,
            "stepper": build_stepper_context("results", role_id, batch_id),
        },
    )


@app.get("/api/runs/{run_id}")
def run_status_json(run_id: str):
    """JSON API endpoint for run status"""
    st = get_run_or_404(run_id)
    if not st:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    
    return JSONResponse(asdict(st))


@app.get("/api/runs")
def list_runs_json():
    """JSON API endpoint to list all runs"""
    recent = [dict_to_runstatus(r) for r in db.list_runs(20)]
    return JSONResponse([asdict(r) for r in recent])


@app.get("/download/{run_id}/{kind}")
def download(run_id: str, kind: str):
    st = get_run_or_404(run_id)
    if not st or not st.outputs:
        return HTMLResponse("Not ready", status_code=404)

    key = kind
    rel = st.outputs.get(key)
    if not rel:
        return HTMLResponse("File not found", status_code=404)

    path = REPO_ROOT / rel
    if not path.exists():
        return HTMLResponse("File missing on disk", status_code=404)

    return FileResponse(path)


def run_evaluation(run_id: str) -> None:
    """Run AI evaluation and bucketing after human approval"""
    st = get_run_or_404(run_id)
    if not st:
        return
    st.state = "evaluating"
    st.message = "Starting AI evaluation..."
    save_run_to_db(st)
    
    run_dir = RUNS_DIR / st.run_name
    output_dir = run_dir / "output"
    standardized = output_dir / "standardized_candidates.csv"
    evaluated = output_dir / "evaluated.csv"
    
    python_exe = str(REPO_ROOT / "venv" / "bin" / "python3")
    
    try:
        # 2) evaluate
        st.message = "Evaluating with AI…"
        cmd_eval = [
            python_exe,
            "evaluate_v3.py",
            str(standardized),
            str(evaluated),
        ]
        subprocess.run(cmd_eval, cwd=str(REPO_ROOT), check=True)

        # 3) bucket
        st.message = "Bucketing results…"
        cmd_bucket = [
            python_exe,
            "tools/bucket_results.py",
            str(evaluated),
            "--outdir",
            str(output_dir),
        ]
        subprocess.run(cmd_bucket, cwd=str(REPO_ROOT), check=True)

        st.state = "done"
        st.message = "Evaluation complete"
        st.outputs = {
            "standardized": str(standardized.relative_to(REPO_ROOT)),
            "evaluated": str(evaluated.relative_to(REPO_ROOT)),
            "proceed": str((output_dir / "proceed.csv").relative_to(REPO_ROOT)),
            "human_review": str((output_dir / "human_review.csv").relative_to(REPO_ROOT)),
            "dismiss": str((output_dir / "dismiss.csv").relative_to(REPO_ROOT)),
            "duplicates": str((output_dir / "duplicates_report.csv").relative_to(REPO_ROOT)) if (output_dir / "duplicates_report.csv").exists() else None,
        }
        st.standardized_data = None  # Clear to save memory
        save_run_to_db(st)

    except subprocess.CalledProcessError as e:
        st.state = "error"
        st.message = f"Evaluation failed (exit {e.returncode}). Check console logs."
        save_run_to_db(st)
    except Exception as e:
        st.state = "error"
        st.message = f"Unexpected error: {e}"
        save_run_to_db(st)


@app.post("/api/runs/{run_id}/approve")
def approve_run(run_id: str):
    """Approve standardized data and trigger AI evaluation"""
    st = get_run_or_404(run_id)
    if not st:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    
    if st.state != "standardized":
        return JSONResponse({"error": f"Cannot approve run in state: {st.state}"}, status_code=400)
    
    # Run evaluation in background thread
    t = threading.Thread(target=run_evaluation, args=(run_id,), daemon=True)
    t.start()
    
    return JSONResponse({"status": "approved", "message": "Evaluation started"})


@app.get("/api/runs/{run_id}/chat")
def get_chat_history(run_id: str):
    """Get chat history for a run"""
    st = get_run_or_404(run_id)
    if not st:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    
    return JSONResponse({"messages": st.chat_messages or []})


@app.post("/api/runs/{run_id}/chat")
async def send_chat_message(run_id: str, request: Request):
    """Send a message to the data assistant"""
    st = get_run_or_404(run_id)
    if not st:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    
    body = await request.json()
    user_message = body.get("message", "")
    
    if not user_message:
        return JSONResponse({"error": "Message cannot be empty"}, status_code=400)
    
    # Initialize chat history if needed
    if st.chat_messages is None:
        st.chat_messages = []
    
    # Add user message
    st.chat_messages.append({
        "role": "user",
        "content": user_message,
        "timestamp": time.time()
    })
    
    # Generate assistant response
    assistant_response = await handle_chat_message(run_id, user_message, st)
    
    # Add assistant message
    st.chat_messages.append({
        "role": "assistant",
        "content": assistant_response,
        "timestamp": time.time()
    })

    save_run_to_db(st)
    
    return JSONResponse({"response": assistant_response})


async def handle_chat_message(run_id: str, message: str, st: RunStatus) -> str:
    """Process user message and generate response using Claude with tool calling"""

    def normalize_field_name(text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9_ ]+", " ", (text or "").lower())
        cleaned = cleaned.replace("_", " ")
        return " ".join(cleaned.split())

    def find_field(fields: List[str], name: str) -> Optional[str]:
        if not name:
            return None
        target = normalize_field_name(name)
        for field in fields:
            if normalize_field_name(field) == target:
                return field
        return None

    def format_pending_action_response(explanation: str, code: str) -> str:
        return (
            f"{explanation}\n\n"
            "Reply **\"run\"** to apply this change, or describe a different modification."
        )

    def sanitize_user_visible_text(text: str) -> str:
        if not text:
            return text
        # Remove fenced code blocks entirely.
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()
        # Remove inline snippets that look like Python/pandas operations.
        def _strip_inline_code(match: re.Match) -> str:
            snippet = match.group(1)
            if re.search(r"\b(df|pd|lambda|iloc|loc|import)\b", snippet) or "{" in snippet or "[" in snippet:
                return ""
            return snippet
        text = re.sub(r"`([^`]+)`", _strip_inline_code, text)
        return " ".join(text.split())

    def ensure_standardized_data_loaded() -> bool:
        if st.standardized_data:
            return True
        run_dir = RUNS_DIR / st.run_name
        standardized_csv = run_dir / "output" / "standardized_candidates.csv"
        if not standardized_csv.exists():
            return False
        standardized_rows = []
        with open(standardized_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                standardized_rows.append(row)
        if not standardized_rows:
            return False
        st.standardized_data = standardized_rows
        save_run_to_db(st)
        return True

    def derive_pending_action_from_message(user_message: str) -> Optional[Dict[str, str]]:
        if not ensure_standardized_data_loaded():
            return None
        if not st.standardized_data:
            return None

        fields = list(st.standardized_data[0].keys())
        message_lower = user_message.lower()
        core_fields = {
            "linkedin_url",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "location",
            "company_name",
            "title",
        }

        col_match = re.search(r"column\s+([a-z])", message_lower)
        if not col_match:
            return None

        col_letter = col_match.group(1).upper()
        col_index = ord(col_letter) - ord("A")
        if col_index < 0 or col_index >= len(fields):
            return None

        target_field = fields[col_index]

        if any(keyword in message_lower for keyword in ["clear", "delete", "remove", "empty", "blank", "erase"]):
            code = f"df.iloc[:, {col_index}] = ''"
            explanation = f"This will clear all values in column {col_letter} ({target_field})."
            if target_field in core_fields:
                explanation += (
                    f" Heads-up: {target_field} is a core field, so clearing it can reduce match rates."
                )
            return {"code": code, "explanation": explanation}

        if any(keyword in message_lower for keyword in ["fill", "set", "populate", "update", "overwrite"]):
            source_match = re.search(r"(?:with|to)\s+(.+)", message_lower)
            source_text = source_match.group(1).strip() if source_match else ""
            source_text = re.sub(r"\s+for\s+all\s+candidates.*", "", source_text).strip()

            source_field = find_field(fields, source_text)
            if not source_field and source_text:
                source_field = find_field(fields, source_text.replace(" ", "_"))

            if source_field:
                code = f"df.iloc[:, {col_index}] = df['{source_field}']"
                explanation = (
                    f"This will set column {col_letter} ({target_field}) to the values from "
                    f"{source_field} for all candidates."
                )
                if target_field in core_fields:
                    explanation += (
                        f" Heads-up: {target_field} is a core field, so overwriting it can change "
                        "how candidates are matched and scored."
                    )
                return {"code": code, "explanation": explanation}

            quoted = re.search(r"['\"]([^'\"]+)['\"]", user_message)
            if quoted:
                literal_value = quoted.group(1)
                code = f"df.iloc[:, {col_index}] = {json.dumps(literal_value)}"
                explanation = (
                    f"This will set all values in column {col_letter} ({target_field}) to \"{literal_value}\"."
                )
                if target_field in core_fields:
                    explanation += (
                        f" Heads-up: {target_field} is a core field, so overwriting it can affect downstream "
                        "matching and outreach."
                    )
                return {"code": code, "explanation": explanation}

        return None
    
    message_lower = message.lower().strip()
    
    # Check if user is confirming a pending action
    if message_lower in ["run", "yes", "confirm", "approve", "go", "do it", "apply"]:
        if st.pending_action:
            # Execute the pending Python code
            run_dir = RUNS_DIR / st.run_name
            result = execute_data_modification(
                st.pending_action['code'],
                st.standardized_data,
                run_dir
            )
            
            if result['success']:
                # Update in-memory data
                st.standardized_data = result['modified_data']
                
                # Clear pending action
                st.pending_action = None
                
                # Stay in standardized state (no need to re-run pipeline)
                st.state = "standardized"
                save_run_to_db(st)
                st.message = f"Modification complete. {len(result['modified_data'])} candidates ready for review."
                
                return f"✅ Applied! {result['message']} The table will refresh in a moment."
            else:
                return f"❌ Error applying changes: {result['message']}\n\nPlease try rephrasing your request or describe the issue differently."
        else:
            return "There's no pending action to apply. Please describe what you'd like to change in the data, and I'll propose a fix for you to confirm."
    
    if not ensure_standardized_data_loaded():
        return (
            "I don't have standardized candidate data loaded for this run yet. "
            "Please run the standardization step first, then tell me what you'd like to change."
        )

    # Build rich context about the data and domain knowledge
    context = build_agent_context(st)
    if context.get("error"):
        return (
            "I don't have standardized candidate data loaded for this run yet. "
            "Please run the standardization step first, then tell me what you'd like to change."
        )

    total_rows = context["dataset_info"]["total_candidates"]
    fields = context["dataset_info"]["fields"]

    # Get column index mapping (A=0, B=1, etc.)
    field_column_map = "\n".join([f"  Column {chr(65+i)} ({i}): {field}" for i, field in enumerate(fields)])

    field_definitions = json.dumps(context["field_definitions"], indent=2)
    field_stats = format_field_stats(context["field_stats"])
    quality_issues = format_quality_issues(context["quality_issues"])
    common_issues = json.dumps(context["common_issues"], indent=2)
    example_transformations = json.dumps(context["example_transformations"], indent=2)
    sample_rows = json.dumps(context["sample_rows"], indent=2)

    data_summary = f"""You are a Recruiting Data Quality Assistant for standardized candidate data.

# ROLE
Help recruiters clean, validate, and improve candidate data. Be proactive, specific, safe, and concise.

# CURRENT DATASET
- Total candidates: {total_rows}
- Role: {context['dataset_info']['role']}
- Fields/Columns:
{field_column_map}

# FIELD DEFINITIONS (domain knowledge)
{field_definitions}

# FIELD STATISTICS
{field_stats}

# DETECTED QUALITY ISSUES
{quality_issues}

# COMMON RECRUITING DATA ISSUES
{common_issues}

# EXAMPLE TRANSFORMATIONS
{example_transformations}

# CAPABILITIES
- Analyze data quality and patterns
- Suggest and apply safe field transformations
- Validate formats (email/URL/phone)

# TOOL USAGE RULES
- Use execute_python only when the user wants to modify data.
- You have access to a pandas DataFrame named 'df'.
- For column letters (G, H, etc.), use df.iloc[:, index] where index = ord(letter) - ord('A').
- Always modify df in place and explain the change in recruiter-friendly terms.
- Never show Python code to the user. Keep code execution internal.
- Ask for confirmation before applying changes.
- Warn before overwriting or clearing core fields (linkedin_url, email, first_name, last_name, full_name, phone, location, company_name, title).

# RESPONSE STYLE
- Proactive: point out likely issues and propose fixes.
- Specific: name fields and impact.
- Safe: avoid deleting records; prefer reversible changes.
- Concise: use short bullet points when listing multiple items.
- Plain recruiting/business language only (e.g., "I'll standardize all LinkedIn URLs to start with https://www.linkedin.com/in/").

# COLUMN OPERATIONS
- Users can rename columns, add calculated columns, and reorder columns.
- Be helpful and flexible; only warn before deleting or overwriting core fields.

Sample data (first 3 rows):
{sample_rows}
"""
    
    # Get previous messages for context
    previous_messages = []
    if st.chat_messages:
        for msg in st.chat_messages[-6:]:  # Last 6 messages for context
            previous_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # If the request looks like a data modification, try to derive a pending action directly.
    derived_action = derive_pending_action_from_message(message)
    if derived_action:
        st.pending_action = {
            "code": derived_action["code"],
            "explanation": derived_action["explanation"],
            "timestamp": time.time()
        }
        save_run_to_db(st)
        return format_pending_action_response(derived_action["explanation"], derived_action["code"])

    # Call Claude with tool calling
    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            system=data_summary,
            tools=[EXECUTE_PYTHON_TOOL],
            messages=previous_messages + [{"role": "user", "content": message}]
        )
        
        # Check if Claude wants to use a tool
        if response.stop_reason == "tool_use":
            tool_use = next((block for block in response.content if block.type == "tool_use"), None)
            
            if tool_use and tool_use.name == "execute_python":
                code = tool_use.input['code']
                explanation = sanitize_user_visible_text(tool_use.input['explanation'])
                if not explanation:
                    explanation = "I can apply the requested change to the dataset."
                
                # Store the pending action
                st.pending_action = {
                    "code": code,
                    "explanation": explanation,
                    "timestamp": time.time()
                }
                save_run_to_db(st)
                
                # Return explanation + confirmation prompt
                return format_pending_action_response(explanation, code)
        
        # Otherwise, return Claude's text response, but avoid promising a run if nothing is pending.
        text_response = next((block.text for block in response.content if hasattr(block, 'text')), "")
        text_response = sanitize_user_visible_text(text_response)
        if text_response and "run" in text_response.lower() and not st.pending_action:
            return (
                "I can propose a change, but I don't have a saved action yet. "
                "Please describe the exact modification you want (e.g., 'clear column G')."
            )
        return text_response if text_response else "I'm not sure how to help with that. Can you describe what you'd like to change in the data?"
        
    except Exception as e:
        import traceback
        return f"Error communicating with AI: {str(e)}\n\n{traceback.format_exc()}"


def apply_data_modification(run_id: str, action: dict, st: RunStatus) -> str:
    """Apply a data modification action"""
    
    user_request = action.get('user_request', '')
    description = action.get('description', '')
    request_lower = user_request.lower()
    
    # Try to parse the request and apply changes
    # Handle column clearing/deletion/removal/regeneration
    if any(keyword in request_lower for keyword in ['clear', 'delete', 'remove', 'empty', 'regenerate', 'erase']):
        # Try to identify which column/field
        # Look for column letter or field name
        
        if st.standardized_data and len(st.standardized_data) > 0:
            fields = list(st.standardized_data[0].keys())
            
            # Try to identify which column/field to modify
            field_to_clear = None
            
            # First, look for column letter in user request (handle typos like "cloumn")
            # Pattern: (clo or col) + optional letters + space + single letter
            col_match = re.search(r'(?:clo|col)\w*\s+([a-z])', request_lower)
            if col_match:
                col_letter = col_match.group(1).upper()
                col_index = ord(col_letter) - ord('A')
                if 0 <= col_index < len(fields):
                    field_to_clear = fields[col_index]
            
            # Also check Claude's description for field name hints
            if not field_to_clear and description:
                for field in fields:
                    if field.lower() in description.lower() or field in description:
                        field_to_clear = field
                        break
            
            # If no column letter, look for field names mentioned in the request
            if not field_to_clear:
                for field in fields:
                    # Match field name with underscores or as separate words
                    field_pattern = field.lower().replace('_', '[ _]')
                    if re.search(field_pattern, request_lower):
                        field_to_clear = field
                        break
            
            if field_to_clear:
                # Update in-memory data
                for row in st.standardized_data:
                    row[field_to_clear] = ""
                
                # Update the input CSV files to reflect the change
                run_dir = RUNS_DIR / st.run_name
                input_dir = run_dir / "input"
                
                files_modified = 0
                # Modify the original input files
                for input_file in input_dir.glob("*.csv"):
                    try:
                        rows = []
                        fieldnames = None
                        with open(input_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            fieldnames = reader.fieldnames
                            for row in reader:
                                # Clear the field if it exists (case-insensitive match)
                                for key in list(row.keys()):
                                    if key.lower() == field_to_clear.lower():
                                        row[key] = ""
                                rows.append(row)
                        
                        if rows and fieldnames:
                            with open(input_file, 'w', newline='', encoding='utf-8') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(rows)
                            files_modified += 1
                    except Exception as e:
                        # Log error but continue with other files
                        print(f"Error modifying {input_file}: {e}")
                
                if files_modified == 0:
                    return f"Warning: Found field '{field_to_clear}' but couldn't modify input files. Field may not exist in source CSVs."
                
                # Trigger re-standardization in background
                st.state = "running"
                save_run_to_db(st)
                st.message = f"Re-running standardization after clearing '{field_to_clear}'..."
                st.standardized_data = None  # Clear old data
                
                # Run re-standardization in background
                t = threading.Thread(target=restandardize_run, args=(run_id,), daemon=True)
                t.start()
                
                return f"Applied: Cleared field '{field_to_clear}'. Re-running standardization now. The table will refresh automatically when complete."
            else:
                return "Could not identify which field to modify. Please be more specific about which column or field name you want to change."
    
    # For other types of modifications, return not implemented message
    return (
        "I understood your request but I'm not yet able to apply this type of modification automatically. "
        "Currently I can only clear/empty columns. For more complex changes, please export the CSV and modify it manually."
    )
