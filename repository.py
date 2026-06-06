from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from models import (
    ProjectCreate, ProjectStatus,
    ConnectorCreate,
    MappingRunCreate,
    ReviewAction,
)
from state_store import store

class BaseRepository(ABC):
    """
    Abstract Base Repository interface defining standard persistence methods
    for projects, connectors, runs, schema discovery, and audits.
    """

    # ── Projects ──────────────────────────────
    @abstractmethod
    def create_project(self, body: ProjectCreate) -> dict:
        pass

    @abstractmethod
    def list_projects(self) -> List[dict]:
        pass

    @abstractmethod
    def get_project(self, pid: str) -> Optional[dict]:
        pass

    @abstractmethod
    def update_project_status(self, pid: str, status: ProjectStatus) -> None:
        pass

    # ── Connectors ────────────────────────────
    @abstractmethod
    def save_connector(self, project_id: str, body: ConnectorCreate) -> dict:
        pass

    @abstractmethod
    def list_connectors(self, project_id: str) -> List[dict]:
        pass

    # ── Mapping runs ──────────────────────────
    @abstractmethod
    def create_run(self, body: MappingRunCreate) -> dict:
        pass

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_runs(self, project_id: str) -> List[dict]:
        pass

    @abstractmethod
    def update_run(self, run_id: str, **kwargs) -> None:
        pass

    @abstractmethod
    def set_run_candidates(self, run_id: str, candidates: List[dict]) -> None:
        pass

    @abstractmethod
    def apply_reviews(self, run_id: str, actions: List[ReviewAction]) -> int:
        pass

    # ── Schema access ──────────────────────────
    @abstractmethod
    def get_source_schema(self, table_name: str) -> Optional[dict]:
        pass

    @abstractmethod
    def get_target_schema(self, table_name: str) -> Optional[dict]:
        pass

    @abstractmethod
    def list_source_tables(self) -> List[str]:
        pass

    @abstractmethod
    def list_target_tables(self) -> List[str]:
        pass

    # ── Audit ─────────────────────────────────
    @abstractmethod
    def get_audit_logs(self, limit: int = 200) -> List[dict]:
        pass


class InMemoryRepository(BaseRepository):
    """
    Repository implementation using the thread-unsafe in-memory store.
    """

    def create_project(self, body: ProjectCreate) -> dict:
        return store.create_project(body)

    def list_projects(self) -> List[dict]:
        return store.list_projects()

    def get_project(self, pid: str) -> Optional[dict]:
        return store.get_project(pid)

    def update_project_status(self, pid: str, status: ProjectStatus) -> None:
        store.update_project_status(pid, status)

    def save_connector(self, project_id: str, body: ConnectorCreate) -> dict:
        return store.save_connector(project_id, body)

    def list_connectors(self, project_id: str) -> List[dict]:
        return store.list_connectors(project_id)

    def create_run(self, body: MappingRunCreate) -> dict:
        return store.create_run(body)

    def get_run(self, run_id: str) -> Optional[dict]:
        return store.get_run(run_id)

    def list_runs(self, project_id: str) -> List[dict]:
        return store.list_runs(project_id)

    def update_run(self, run_id: str, **kwargs) -> None:
        store.update_run(run_id, **kwargs)

    def set_run_candidates(self, run_id: str, candidates: List[dict]) -> None:
        store.set_run_candidates(run_id, candidates)

    def apply_reviews(self, run_id: str, actions: List[ReviewAction]) -> int:
        return store.apply_reviews(run_id, actions)

    def get_source_schema(self, table_name: str) -> Optional[dict]:
        return store.get_source_schema(table_name)

    def get_target_schema(self, table_name: str) -> Optional[dict]:
        return store.get_target_schema(table_name)

    def list_source_tables(self) -> List[str]:
        return store.list_source_tables()

    def list_target_tables(self) -> List[str]:
        return store.list_target_tables()

    def get_audit_logs(self, limit: int = 200) -> List[dict]:
        return store.get_audit_logs(limit)

# Global repository instance
repo: BaseRepository = InMemoryRepository()
