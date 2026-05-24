"""
Pydantic models for Oracle Mapping Copilot
Covers all request/response shapes used across FastAPI endpoints.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class ProjectStatus(str, Enum):
    ACTIVE   = "active"
    ARCHIVED = "archived"
    DRAFT    = "draft"

class MappingStatus(str, Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    REJECTED  = "rejected"
    OVERRIDDEN = "overridden"

class RunStatus(str, Enum):
    QUEUED   = "queued"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"

class ConnectorSide(str, Enum):
    SOURCE = "source"
    TARGET = "target"

class ConfidenceTier(str, Enum):
    EXACT    = "exact"       # 0.95-1.00
    CLEAR    = "clear"       # 0.80-0.94
    PROBABLE = "probable"    # 0.60-0.79
    POSSIBLE = "possible"    # 0.40-0.59
    LOW      = "low"         # 0.00-0.39


# ──────────────────────────────────────────────
# Column & Schema primitives
# ──────────────────────────────────────────────

class ColumnDef(BaseModel):
    name:     str
    type:     str
    nullable: Optional[str]  = "Y"
    comment:  Optional[str]  = ""
    samples:  Optional[List[Any]] = Field(default_factory=list)

class TableDef(BaseModel):
    name:               str
    owner:              Optional[str]  = ""
    row_count_estimate: Optional[int]  = 0
    columns:            List[ColumnDef] = Field(default_factory=list)

class ColumnProfile(BaseModel):
    column_name:     str
    data_type:       str
    comment:         Optional[str]  = ""
    inferred_pattern: Optional[str] = "unknown"
    semantic_tags:   List[str]      = Field(default_factory=list)
    masked_samples:  List[str]      = Field(default_factory=list)
    null_pct:        float          = 0.0
    distinct_count:  Optional[int]  = None


# ──────────────────────────────────────────────
# Connector
# ──────────────────────────────────────────────

class ConnectorCreate(BaseModel):
    side:         ConnectorSide
    host:         str = "localhost"
    port:         int = 1521
    service_name: str = "ORCL"
    username:     str = "system"
    password:     str = ""            # stored encrypted in real builds
    schema_name:  str = ""

class ConnectorRead(ConnectorCreate):
    id:         str
    project_id: str
    password:   str = "********"      # masked on read
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Project
# ──────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name:        str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = ""
    owner:       Optional[str] = "engineer@company.com"

class ProjectRead(ProjectCreate):
    id:         str
    status:     ProjectStatus = ProjectStatus.DRAFT
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Mapping candidate (AI output per column)
# ──────────────────────────────────────────────

class SignalBreakdown(BaseModel):
    name_similarity:    str = ""
    type_compatibility: str = ""
    pattern_match:      str = ""
    semantic:           str = ""

class MappingCandidate(BaseModel):
    source_column:      str
    source_type:        Optional[str] = ""
    source_comment:     Optional[str] = ""
    target_column:      Optional[str] = None
    target_type:        Optional[str] = ""
    target_comment:     Optional[str] = ""
    confidence:         float         = 0.0
    confidence_tier:    ConfidenceTier = ConfidenceTier.LOW
    rationale:          str           = ""
    signals:            SignalBreakdown = Field(default_factory=SignalBreakdown)
    status:             MappingStatus  = MappingStatus.PENDING
    reviewer_note:      Optional[str]  = ""
    overridden_target:  Optional[str]  = None


# ──────────────────────────────────────────────
# Mapping run
# ──────────────────────────────────────────────

class MappingRunCreate(BaseModel):
    project_id:      str
    source_table:    str
    target_table:    str
    threshold:       float = 0.40
    ai_model:      str   = "gemini-2.0-flash"
    prompt_version:  str   = "v1"

class MappingRunRead(MappingRunCreate):
    id:             str
    status:         RunStatus = RunStatus.QUEUED
    candidates:     List[MappingCandidate] = Field(default_factory=list)
    started_at:     Optional[datetime] = None
    ended_at:       Optional[datetime] = None
    error_message:  Optional[str]      = None
    stats:          Dict[str, Any]     = Field(default_factory=dict)

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Review actions
# ──────────────────────────────────────────────

class ReviewAction(BaseModel):
    source_column:     str
    action:            MappingStatus   # approved | rejected | overridden
    overridden_target: Optional[str]  = None
    reviewer_note:     Optional[str]  = ""
    reviewer:          str             = "reviewer@company.com"

class BulkReviewRequest(BaseModel):
    run_id:  str
    actions: List[ReviewAction]


# ──────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────

class ExportRequest(BaseModel):
    run_id:       str
    format:       str = "json"   # json | csv | xlsx
    approved_only: bool = True

class ExportResult(BaseModel):
    run_id:       str
    format:       str
    row_count:    int
    file_path:    Optional[str] = None
    payload:      Optional[Any] = None   # inline JSON payload


# ──────────────────────────────────────────────
# Audit
# ──────────────────────────────────────────────

class AuditLog(BaseModel):
    id:          str
    entity_type: str
    entity_id:   str
    action:      str
    actor:       str
    payload:     Dict[str, Any] = Field(default_factory=dict)
    created_at:  datetime


# ──────────────────────────────────────────────
# Health / generic response
# ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:    str = "ok"
    version:   str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageResponse(BaseModel):
    message: str
    data:    Optional[Any] = None
