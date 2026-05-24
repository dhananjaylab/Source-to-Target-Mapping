"""
Oracle Mapping Copilot — FastAPI Backend
Endpoints: projects, connectors, schemas, profiles, mappings, reviews, exports, audit
"""

from __future__ import annotations
import os
import csv
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("main")

# Local imports
from models import (
    ProjectCreate, ProjectRead, ProjectStatus,
    ConnectorCreate, ConnectorRead,
    MappingRunCreate, MappingRunRead, RunStatus,
    MappingCandidate, BulkReviewRequest, ReviewAction, MappingStatus,
    ExportRequest, ExportResult,
    HealthResponse, MessageResponse,
    AuditLog,
)
from state_store import store
from gemini_service import generate_mappings
from mapping_engine import build_profiles_parallel

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────

app = FastAPI(
    title        = "Oracle Mapping Copilot API",
    description  = "AI-assisted Oracle source-to-target column mapping with Gemini LLM.",
    version      = "1.0.0",
    docs_url     = "/docs",
    redoc_url    = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse()

@app.get("/", tags=["System"])
def root():
    return {"message": "Oracle Mapping Copilot API", "docs": "/docs"}


# ──────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────

@app.get("/projects", response_model=List[dict], tags=["Projects"])
def list_projects():
    return store.list_projects()

@app.post("/projects", response_model=dict, status_code=201, tags=["Projects"])
def create_project(body: ProjectCreate):
    return store.create_project(body)

@app.get("/projects/{project_id}", response_model=dict, tags=["Projects"])
def get_project(project_id: str):
    proj = store.get_project(project_id)
    if not proj:
        raise HTTPException(404, f"Project '{project_id}' not found.")
    return proj


# ──────────────────────────────────────────────
# Connectors
# ──────────────────────────────────────────────

@app.get("/projects/{project_id}/connectors", response_model=List[dict], tags=["Connectors"])
def list_connectors(project_id: str):
    return store.list_connectors(project_id)

@app.post("/projects/{project_id}/connectors", response_model=dict, status_code=201, tags=["Connectors"])
def save_connector(project_id: str, body: ConnectorCreate):
    proj = store.get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found.")
    return store.save_connector(project_id, body)

@app.post("/projects/{project_id}/connectors/test", tags=["Connectors"])
def test_connection(project_id: str, body: ConnectorCreate):
    """
    Simulates Oracle connectivity test.
    In production: attempt cx_Oracle / oracledb connect with a SELECT 1 FROM DUAL.
    """
    return {
        "status": "success",
        "message": f"Connected to {body.host}:{body.port}/{body.service_name} as {body.username}",
        "latency_ms": 42,
    }


# ──────────────────────────────────────────────
# Schema discovery
# ──────────────────────────────────────────────

@app.get("/schemas/source", tags=["Schemas"])
def list_source_tables():
    return {"tables": store.list_source_tables()}

@app.get("/schemas/target", tags=["Schemas"])
def list_target_tables():
    return {"tables": store.list_target_tables()}

@app.get("/schemas/source/{table_name}", tags=["Schemas"])
def get_source_schema(table_name: str):
    schema = store.get_source_schema(table_name)
    if not schema:
        raise HTTPException(404, f"Source table '{table_name}' not found.")
    return {"table_name": table_name, **schema}

@app.get("/schemas/target/{table_name}", tags=["Schemas"])
def get_target_schema(table_name: str):
    schema = store.get_target_schema(table_name)
    if not schema:
        raise HTTPException(404, f"Target table '{table_name}' not found.")
    return {"table_name": table_name, **schema}


# ──────────────────────────────────────────────
# Profiling
# ──────────────────────────────────────────────

@app.post("/projects/{project_id}/profiles", tags=["Profiling"])
def build_profiles(project_id: str, table_name: str = Query(...), side: str = Query("source")):
    """
    Build enriched column profiles for a source or target table.
    In production this queries Oracle ALL_TAB_COLUMNS + samples.
    """
    if side == "source":
        schema = store.get_source_schema(table_name)
    else:
        schema = store.get_target_schema(table_name)

    if not schema:
        raise HTTPException(404, f"Table '{table_name}' not found in {side} schemas.")

    columns  = schema["columns"]
    profiles = build_profiles_parallel(columns)

    return {
        "table_name": table_name,
        "side":       side,
        "column_count": len(profiles),
        "profiles": [p.model_dump() for p in profiles],
    }


# ──────────────────────────────────────────────
# Mapping generation (background)
# ──────────────────────────────────────────────

async def _run_mapping(run_id: str, src_table: str, tgt_table: str, threshold: float):
    """Background task: call Gemini and persist results."""
    store.update_run(run_id, status=RunStatus.RUNNING, started_at=datetime.utcnow())
    try:
        src_schema = store.get_source_schema(src_table)
        tgt_schema = store.get_target_schema(tgt_table)

        if not src_schema or not tgt_schema:
            raise ValueError(f"Schema not found: src={src_table}, tgt={tgt_table}")

        candidates = await generate_mappings(
            src_table   = src_table,
            src_columns = src_schema["columns"],
            tgt_table   = tgt_table,
            tgt_columns = tgt_schema["columns"],
            threshold   = threshold,
        )

        store.set_run_candidates(run_id, [c.model_dump() for c in candidates])
        logger.info("Run %s complete — %d candidates.", run_id, len(candidates))

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        store.update_run(
            run_id,
            status       = RunStatus.FAILED,
            ended_at     = datetime.utcnow(),
            error_message= str(exc),
        )


@app.post("/projects/{project_id}/mappings/generate",
          response_model=dict, status_code=202, tags=["Mappings"])
async def generate_mapping_run(
    project_id:      str,
    background_tasks: BackgroundTasks,
    body:            MappingRunCreate,
):
    """
    Kick off an async mapping run. Returns the run_id immediately.
    Poll GET /projects/{id}/mappings/{run_id} for status.
    """
    proj = store.get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found.")

    run = store.create_run(body)
    background_tasks.add_task(
        _run_mapping,
        run["id"],
        body.source_table,
        body.target_table,
        body.threshold,
    )
    return {"run_id": run["id"], "status": RunStatus.QUEUED,
            "message": "Mapping run queued. Poll status endpoint."}


@app.post("/projects/{project_id}/mappings/generate/sync",
          response_model=dict, tags=["Mappings"])
async def generate_mapping_run_sync(project_id: str, body: MappingRunCreate):
    """
    Synchronous version — waits for Gemini and returns candidates directly.
    Useful for Streamlit (which drives the UX state machine itself).
    """
    proj = store.get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found.")

    run = store.create_run(body)
    run_id = run["id"]

    store.update_run(run_id, status=RunStatus.RUNNING, started_at=datetime.utcnow())

    try:
        src_schema = store.get_source_schema(body.source_table)
        tgt_schema = store.get_target_schema(body.target_table)

        if not src_schema or not tgt_schema:
            raise HTTPException(404, "Source or target schema not found.")

        candidates = await generate_mappings(
            src_table   = body.source_table,
            src_columns = src_schema["columns"],
            tgt_table   = body.target_table,
            tgt_columns = tgt_schema["columns"],
            threshold   = body.threshold,
        )

        store.set_run_candidates(run_id, [c.model_dump() for c in candidates])

        run = store.get_run(run_id)
        return {
            "run_id":     run_id,
            "status":     RunStatus.DONE,
            "stats":      run["stats"],
            "candidates": [c.model_dump() for c in candidates],
        }

    except HTTPException:
        raise
    except Exception as exc:
        store.update_run(run_id, status=RunStatus.FAILED,
                         ended_at=datetime.utcnow(), error_message=str(exc))
        raise HTTPException(500, f"Mapping failed: {exc}")


@app.get("/projects/{project_id}/mappings", response_model=List[dict], tags=["Mappings"])
def list_runs(project_id: str):
    return store.list_runs(project_id)

@app.get("/projects/{project_id}/mappings/{run_id}", tags=["Mappings"])
def get_run(project_id: str, run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found.")
    return run


# ──────────────────────────────────────────────
# Validation endpoint
# ──────────────────────────────────────────────

@app.post("/projects/{project_id}/mappings/{run_id}/validate", tags=["Mappings"])
def validate_run(project_id: str, run_id: str):
    """Re-runs validation logic on existing candidates without re-calling LLM."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found.")

    tgt_schema = store.get_target_schema(run["target_table"])
    if not tgt_schema:
        raise HTTPException(404, "Target schema not found.")

    valid_names = {c["name"] for c in tgt_schema["columns"]}
    issues      = []

    for c in run["candidates"]:
        tgt = c.get("target_column")
        if tgt and tgt not in valid_names:
            issues.append({"source": c["source_column"], "invalid_target": tgt})

    return {
        "run_id":      run_id,
        "valid":       len(issues) == 0,
        "issue_count": len(issues),
        "issues":      issues,
    }


# ──────────────────────────────────────────────
# Review actions
# ──────────────────────────────────────────────

@app.post("/projects/{project_id}/mappings/{run_id}/review",
          response_model=MessageResponse, tags=["Review"])
def apply_review(project_id: str, run_id: str, body: BulkReviewRequest):
    changed = store.apply_reviews(run_id, body.actions)
    return MessageResponse(message=f"{changed} mapping(s) updated.", data={"changed": changed})

@app.get("/projects/{project_id}/mappings/{run_id}/review/summary", tags=["Review"])
def review_summary(project_id: str, run_id: str):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found.")
    cands    = run["candidates"]
    approved = sum(1 for c in cands if c.get("status") == MappingStatus.APPROVED)
    rejected = sum(1 for c in cands if c.get("status") == MappingStatus.REJECTED)
    overridden= sum(1 for c in cands if c.get("status") == MappingStatus.OVERRIDDEN)
    pending  = len(cands) - approved - rejected - overridden
    return {
        "total": len(cands), "approved": approved,
        "rejected": rejected, "overridden": overridden, "pending": pending,
        "pct_reviewed": round((approved + rejected + overridden) / len(cands) * 100, 1) if cands else 0,
    }


# ──────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────

def _get_export_rows(run_id: str, approved_only: bool) -> List[dict]:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Run not found.")
    cands = run["candidates"]
    if approved_only:
        cands = [c for c in cands
                 if c.get("status") in (MappingStatus.APPROVED, MappingStatus.OVERRIDDEN)]
    return cands


@app.post("/projects/{project_id}/exports", tags=["Export"])
def export_mappings(project_id: str, body: ExportRequest):
    rows = _get_export_rows(body.run_id, body.approved_only)

    if body.format == "json":
        return JSONResponse({"run_id": body.run_id, "count": len(rows), "mappings": rows})

    if body.format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            "source_column", "source_type", "target_column", "target_type",
            "confidence", "confidence_tier", "status", "rationale", "reviewer_note",
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "source_column":   r.get("source_column", ""),
                "source_type":     r.get("source_type", ""),
                "target_column":   r.get("overridden_target") or r.get("target_column") or "(unmapped)",
                "target_type":     r.get("target_type", ""),
                "confidence":      r.get("confidence", 0),
                "confidence_tier": r.get("confidence_tier", ""),
                "status":          r.get("status", ""),
                "rationale":       r.get("rationale", ""),
                "reviewer_note":   r.get("reviewer_note", ""),
            })
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mapping_{body.run_id[:8]}.csv"},
        )

    raise HTTPException(400, f"Unsupported format: {body.format}. Use 'json' or 'csv'.")


# ──────────────────────────────────────────────
# Audit
# ──────────────────────────────────────────────

@app.get("/audit", response_model=List[dict], tags=["Audit"])
def get_audit(limit: int = Query(100, ge=1, le=500)):
    return store.get_audit_logs(limit)
