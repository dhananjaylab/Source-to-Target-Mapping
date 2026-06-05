import pytest
from pydantic import ValidationError
from models import MappingRunCreate, ReviewAction, ExportRequest, MappingStatus, ExportFormat
from state_store import store
from gemini_service import generate_mappings

def test_mapping_run_create_validation():
    # Valid model
    run = MappingRunCreate(
        project_id="demo-project-001",
        source_table="CRM_CUSTOMERS",
        target_table="DIM_CUSTOMER",
        threshold=0.5,
        ai_model="gemini-2.0-flash",
        prompt_version="v1"
    )
    assert run.threshold == 0.5

    # Out of bounds threshold
    with pytest.raises(ValidationError):
        MappingRunCreate(
            project_id="demo-project-001",
            source_table="CRM_CUSTOMERS",
            target_table="DIM_CUSTOMER",
            threshold=1.5  # > 1.0
        )

    with pytest.raises(ValidationError):
        MappingRunCreate(
            project_id="demo-project-001",
            source_table="CRM_CUSTOMERS",
            target_table="DIM_CUSTOMER",
            threshold=-0.1  # < 0.0
        )

    # Extra fields rejected
    with pytest.raises(ValidationError):
        MappingRunCreate(
            project_id="demo-project-001",
            source_table="CRM_CUSTOMERS",
            target_table="DIM_CUSTOMER",
            model_name="gemini-2.0-flash"  # extra field, should be ai_model
        )


def test_review_action_validation():
    # Valid actions
    act_ok = ReviewAction(
        source_column="cust_id",
        action=MappingStatus.APPROVED
    )
    assert act_ok.action == MappingStatus.APPROVED

    # Pending action rejected
    with pytest.raises(ValidationError) as exc:
        ReviewAction(
            source_column="cust_id",
            action=MappingStatus.PENDING
        )
    assert "Review actions must not be PENDING." in str(exc.value)


def test_export_request_validation():
    # Valid export format
    req = ExportRequest(run_id="run-1", format=ExportFormat.CSV)
    assert req.format == "csv"

    # Invalid export format rejected
    with pytest.raises(ValidationError):
        ExportRequest(run_id="run-1", format="invalid_format")


@pytest.mark.asyncio
async def test_deterministic_bypass():
    # If all columns match exactly on name and type, generate_mappings should resolve it instantly without calling Gemini
    src_columns = [{"name": "CUST_ID", "type": "INTEGER", "comment": "Customer ID", "samples": [1, 2, 3]}]
    tgt_columns = [{"name": "CUST_ID", "type": "INTEGER", "comment": "Customer Identifier"}]

    results = await generate_mappings(
        src_table="SRC",
        src_columns=src_columns,
        tgt_table="TGT",
        tgt_columns=tgt_columns,
        threshold=0.40
    )

    assert len(results) == 1
    assert results[0].target_column == "CUST_ID"
    assert results[0].confidence == 1.0
    assert "Deterministic bypass" in results[0].rationale
