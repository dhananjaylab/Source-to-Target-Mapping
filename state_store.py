"""
In-memory state store for Oracle Mapping Copilot.
In production this would be backed by PostgreSQL or Oracle itself.
Provides project, run, mapping and audit persistence for the demo.
"""

from __future__ import annotations
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from models import (
    ProjectRead, ProjectCreate, ProjectStatus,
    ConnectorRead, ConnectorCreate,
    MappingRunRead, MappingRunCreate, RunStatus,
    MappingCandidate, ReviewAction, MappingStatus,
    AuditLog,
)

# ──────────────────────────────────────────────
# Load demo schemas from disk
# ──────────────────────────────────────────────

_SCHEMA_PATH = Path(__file__).parent / "sample_schemas" / "schemas.json"

def load_demo_schemas() -> dict:
    with open(_SCHEMA_PATH) as f:
        return json.load(f)

_DEMO = load_demo_schemas()
DEMO_SOURCE_SCHEMAS: Dict[str, Any] = _DEMO["source_schemas"]
DEMO_TARGET_SCHEMAS: Dict[str, Any] = _DEMO["target_schemas"]


# ──────────────────────────────────────────────
# Store
# ──────────────────────────────────────────────

class Store:
    """Thread-unsafe in-memory store. Good for single-process demo."""

    def __init__(self):
        self._projects:   Dict[str, dict] = {}
        self._connectors: Dict[str, dict] = {}   # keyed by connector id
        self._runs:       Dict[str, dict] = {}   # keyed by run id
        self._audit:      List[dict]      = []
        self._seed_demo_project()

    # ── seed ──────────────────────────────────

    def _seed_demo_project(self):
        pid = "demo-project-001"
        now = datetime.utcnow()
        self._projects[pid] = {
            "id": pid, "name": "CRM → Data Warehouse Migration",
            "description": "Map CRM and OMS source tables to DW dimensional model.",
            "owner": "engineer@company.com",
            "status": ProjectStatus.ACTIVE,
            "created_at": now, "updated_at": now,
        }
        for side, schemas in [("source", DEMO_SOURCE_SCHEMAS), ("target", DEMO_TARGET_SCHEMAS)]:
            cid = f"conn-{side}-{pid}"
            self._connectors[cid] = {
                "id": cid, "project_id": pid, "side": side,
                "host": "oracle-db.company.com", "port": 1521,
                "service_name": "ORCL", "username": f"{side}_user",
                "password": "********", "schema_name": list(schemas.keys())[0],
                "created_at": now,
            }

    # ── Projects ──────────────────────────────

    def create_project(self, body: ProjectCreate) -> dict:
        pid  = str(uuid.uuid4())
        now  = datetime.utcnow()
        proj = {**body.model_dump(), "id": pid, "status": ProjectStatus.DRAFT,
                "created_at": now, "updated_at": now}
        self._projects[pid] = proj
        self._log("project", pid, "created", body.owner, body.model_dump())
        return proj

    def list_projects(self) -> List[dict]:
        return list(self._projects.values())

    def get_project(self, pid: str) -> Optional[dict]:
        return self._projects.get(pid)

    def update_project_status(self, pid: str, status: ProjectStatus):
        if pid in self._projects:
            self._projects[pid]["status"] = status
            self._projects[pid]["updated_at"] = datetime.utcnow()

    # ── Connectors ────────────────────────────

    def save_connector(self, project_id: str, body: ConnectorCreate) -> dict:
        cid = str(uuid.uuid4())
        conn = {**body.model_dump(), "id": cid,
                "project_id": project_id, "created_at": datetime.utcnow()}
        self._connectors[cid] = conn
        self._log("connector", cid, "created", "system", conn)
        return conn

    def list_connectors(self, project_id: str) -> List[dict]:
        return [c for c in self._connectors.values() if c["project_id"] == project_id]

    # ── Mapping runs ──────────────────────────

    def create_run(self, body: MappingRunCreate) -> dict:
        rid = str(uuid.uuid4())
        run = {
            **body.model_dump(),
            "id": rid, "status": RunStatus.QUEUED,
            "candidates": [], "stats": {},
            "started_at": None, "ended_at": None, "error_message": None,
        }
        self._runs[rid] = run
        return run

    def get_run(self, run_id: str) -> Optional[dict]:
        return self._runs.get(run_id)

    def list_runs(self, project_id: str) -> List[dict]:
        return [r for r in self._runs.values() if r["project_id"] == project_id]

    def update_run(self, run_id: str, **kwargs):
        if run_id in self._runs:
            self._runs[run_id].update(kwargs)

    def set_run_candidates(self, run_id: str, candidates: List[dict]):
        if run_id not in self._runs:
            return
        self._runs[run_id]["candidates"] = candidates
        self._runs[run_id]["status"]     = RunStatus.DONE
        self._runs[run_id]["ended_at"]   = datetime.utcnow()
        # compute stats
        mapped   = sum(1 for c in candidates if c.get("target_column"))
        unmapped = len(candidates) - mapped
        high_c   = sum(1 for c in candidates if c.get("confidence", 0) >= 0.80)
        self._runs[run_id]["stats"] = {
            "total": len(candidates), "mapped": mapped,
            "unmapped": unmapped, "high_confidence": high_c,
            "avg_confidence": (
                round(sum(c.get("confidence", 0) for c in candidates) / len(candidates), 3)
                if candidates else 0
            ),
        }

    def apply_reviews(self, run_id: str, actions: List[ReviewAction]) -> int:
        run = self._runs.get(run_id)
        if not run:
            return 0
        action_map = {a.source_column: a for a in actions}
        changed = 0
        for c in run["candidates"]:
            src = c["source_column"]
            if src in action_map:
                act = action_map[src]
                c["status"] = act.action
                if act.action == MappingStatus.OVERRIDDEN and act.overridden_target:
                    c["overridden_target"] = act.overridden_target
                if act.reviewer_note:
                    c["reviewer_note"] = act.reviewer_note
                changed += 1
                self._log("mapping_candidate", src, act.action,
                          act.reviewer, {"run_id": run_id, "note": act.reviewer_note})
        return changed

    # ── Schema access (demo) ──────────────────

    def get_source_schema(self, table_name: str) -> Optional[dict]:
        return DEMO_SOURCE_SCHEMAS.get(table_name)

    def get_target_schema(self, table_name: str) -> Optional[dict]:
        return DEMO_TARGET_SCHEMAS.get(table_name)

    def list_source_tables(self) -> List[str]:
        return list(DEMO_SOURCE_SCHEMAS.keys())

    def list_target_tables(self) -> List[str]:
        return list(DEMO_TARGET_SCHEMAS.keys())

    # ── Audit ─────────────────────────────────

    def _log(self, entity_type: str, entity_id: str,
             action: str, actor: str, payload: dict):
        self._audit.append({
            "id": str(uuid.uuid4()), "entity_type": entity_type,
            "entity_id": entity_id, "action": action,
            "actor": actor, "payload": payload,
            "created_at": datetime.utcnow(),
        })

    def get_audit_logs(self, limit: int = 200) -> List[dict]:
        return list(reversed(self._audit[-limit:]))


# Singleton store instance used across all requests
store = Store()
