import pytest
from fastapi.testclient import TestClient
from main import app
from state_store import store
from models import ProjectCreate, ConnectorCreate, MappingRunCreate, ConnectorSide, MappingStatus, ReviewAction, BulkReviewRequest

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_store():
    # Keep the store singleton clean or reset it
    store._projects.clear()
    store._connectors.clear()
    store._runs.clear()
    store._audit.clear()
    store._seed_demo_project()

def test_connector_password_masking_and_audit_scrub():
    # 1. Create a project
    pid = "proj-test-123"
    store._projects[pid] = {
        "id": pid, "name": "Test Project", "owner": "test@company.com"
    }

    # 2. Save a connector with a sensitive password via API
    payload = {
        "side": "source",
        "host": "localhost",
        "port": 1521,
        "service_name": "ORCL",
        "username": "admin",
        "password": "SUPER_SECRET_PASSWORD_123",
        "schema_name": "TEST_SCHEMA"
    }
    response = client.post(f"/projects/{pid}/connectors", json=payload)
    assert response.status_code == 201
    res_data = response.json()
    
    # Assert password is masked on read/response
    assert res_data["password"] == "********"
    assert res_data["id"] is not None

    # Assert get connectors also masks password
    get_response = client.get(f"/projects/{pid}/connectors")
    assert get_response.status_code == 200
    connectors = get_response.json()
    assert len(connectors) == 1
    assert connectors[0]["password"] == "********"

    # Assert audit log has scrubbed password
    audit_response = client.get("/audit")
    assert audit_response.status_code == 200
    audit_logs = audit_response.json()
    
    # Find the connector creation audit log
    conn_logs = [log for log in audit_logs if log["entity_type"] == "connector"]
    assert len(conn_logs) > 0
    # Ensure no raw password is saved in payload
    assert conn_logs[0]["payload"]["password"] == "********"


def test_project_isolation_on_run_endpoints():
    # Create project A and project B
    pid_a = "proj-a"
    pid_b = "proj-b"
    store._projects[pid_a] = {"id": pid_a, "name": "Proj A"}
    store._projects[pid_b] = {"id": pid_b, "name": "Proj B"}

    # Create a run in Project B
    run_b_id = "run-b-123"
    store._runs[run_b_id] = {
        "id": run_b_id,
        "project_id": pid_b,
        "source_table": "SRC",
        "target_table": "TGT",
        "status": "done",
        "candidates": [],
        "stats": {}
    }

    # Try to access Project B's run using Project A path parameter -> should return 404
    response = client.get(f"/projects/{pid_a}/mappings/{run_b_id}")
    assert response.status_code == 404

    # Try to validate Project B's run using Project A -> should return 404
    response = client.post(f"/projects/{pid_a}/mappings/{run_b_id}/validate")
    assert response.status_code == 404

    # Try to submit a review for Project B's run using Project A -> should return 404
    review_payload = {
        "run_id": run_b_id,
        "actions": []
    }
    response = client.post(f"/projects/{pid_a}/mappings/{run_b_id}/review", json=review_payload)
    assert response.status_code == 404

    # Try to export Project B's run using Project A -> should return 404
    export_payload = {
        "run_id": run_b_id,
        "format": "json",
        "approved_only": True
    }
    response = client.post(f"/projects/{pid_a}/exports", json=export_payload)
    assert response.status_code == 404


def test_run_creation_mismatch_prevention():
    pid_a = "proj-a"
    store._projects[pid_a] = {"id": pid_a, "name": "Proj A"}

    # Try to generate mapping run with body.project_id mismatching path project_id
    payload = {
        "project_id": "different-project",
        "source_table": "CRM_CUSTOMERS",
        "target_table": "DIM_CUSTOMER",
        "threshold": 0.40,
        "ai_model": "gemini-2.0-flash",
        "prompt_version": "v1"
    }

    response = client.post(f"/projects/{pid_a}/mappings/generate", json=payload)
    assert response.status_code == 400
    assert "does not match path parameter" in response.json()["detail"]

    response = client.post(f"/projects/{pid_a}/mappings/generate/sync", json=payload)
    assert response.status_code == 400
    assert "does not match path parameter" in response.json()["detail"]
