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

import json
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "runs"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

RUNS_DIR.mkdir(parents=True, exist_ok=True)

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


@dataclass
class RunStatus:
    run_id: str
    created_at: float
    run_name: str
    role_label: str
    state: str  # queued|running|done|error
    message: str = ""
    outputs: Optional[dict] = None


RUNS: Dict[str, RunStatus] = {}


def safe_name(s: str) -> str:
    s = (s or "").strip()
    keep = []
    for ch in s:
        if ch.isalnum() or ch in "-_ ":
            keep.append(ch)
    out = "".join(keep).strip().replace(" ", "_")
    return out[:80] if out else "run"


def run_pipeline(run_id: str, input_paths: List[Path]) -> None:
    st = RUNS[run_id]
    st.state = "running"
    st.message = "Starting…"

    run_dir = RUNS_DIR / st.run_name
    input_dir = run_dir / "input"
    output_dir = run_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy inputs into run folder
    st.message = "Saving uploads…"
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
        # Use python -m ingestion.main with glob
        cmd_ingest = [
            "python",
            "-m",
            "ingestion.main",
        ] + [str(input_dir / p.name) for p in input_paths] + [
            "--output-dir",
            str(output_dir),
        ]
        subprocess.run(cmd_ingest, cwd=str(REPO_ROOT), check=True)

        # 2) evaluate
        st.message = "Evaluating with AI…"
        standardized = output_dir / "standardized_candidates.csv"
        evaluated = output_dir / "evaluated.csv"
        cmd_eval = [
            "python",
            "evaluate_v3.py",
            str(standardized),
            str(evaluated),
        ]
        subprocess.run(cmd_eval, cwd=str(REPO_ROOT), check=True)

        # 3) bucket
        st.message = "Bucketing results…"
        cmd_bucket = [
            "python",
            "tools/bucket_results.py",
            str(evaluated),
            "--outdir",
            str(output_dir),
        ]
        subprocess.run(cmd_bucket, cwd=str(REPO_ROOT), check=True)

        st.state = "done"
        st.message = "Done"
        st.outputs = {
            "standardized": str(standardized.relative_to(REPO_ROOT)),
            "evaluated": str(evaluated.relative_to(REPO_ROOT)),
            "proceed": str((output_dir / "proceed.csv").relative_to(REPO_ROOT)),
            "human_review": str((output_dir / "human_review.csv").relative_to(REPO_ROOT)),
            "dismiss": str((output_dir / "dismiss.csv").relative_to(REPO_ROOT)),
            "duplicates": str((output_dir / "duplicates_report.csv").relative_to(REPO_ROOT)) if (output_dir / "duplicates_report.csv").exists() else None,
        }

    except subprocess.CalledProcessError as e:
        st.state = "error"
        st.message = f"Pipeline failed (exit {e.returncode}). Check console logs on the machine running the UI."
    except Exception as e:
        st.state = "error"
        st.message = f"Unexpected error: {e}"


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Show recent runs (latest first)
    recent = sorted(RUNS.values(), key=lambda r: r.created_at, reverse=True)[:20]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "recent": recent,
        },
    )


@app.post("/run")
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
    RUNS[rid] = st

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


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str):
    st = RUNS.get(run_id)
    if not st:
        return HTMLResponse("Run not found", status_code=404)

    return templates.TemplateResponse(
        "run.html",
        {
            "request": request,
            "run": st,
            "run_json": json.dumps(asdict(st), indent=2),
        },
    )


@app.get("/api/runs/{run_id}")
def run_status_json(run_id: str):
    """JSON API endpoint for run status"""
    st = RUNS.get(run_id)
    if not st:
        return JSONResponse({"error": "Run not found"}, status_code=404)
    
    return JSONResponse(asdict(st))


@app.get("/api/runs")
def list_runs_json():
    """JSON API endpoint to list all runs"""
    recent = sorted(RUNS.values(), key=lambda r: r.created_at, reverse=True)[:20]
    return JSONResponse([asdict(r) for r in recent])


@app.get("/download/{run_id}/{kind}")
def download(run_id: str, kind: str):
    st = RUNS.get(run_id)
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
