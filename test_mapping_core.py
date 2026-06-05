import pytest
from mapping_engine import infer_pattern, type_compatible, should_mask, parse_type_meta

def test_infer_pattern_heuristics():
    # ID hints vs Count/Measure hints
    samples = [1, 2, 3, 4, 5]
    
    # Measure/count hints should infer 'integer'
    assert infer_pattern(samples, "qty") == "integer"
    assert infer_pattern(samples, "stk_qty") == "integer"
    assert infer_pattern(samples, "order_amount") == "integer"
    assert infer_pattern(samples, "days") == "integer"

    # ID hints should infer 'integer_id'
    assert infer_pattern(samples, "user_id") == "integer_id"
    assert infer_pattern(samples, "customer_key") == "integer_id"
    assert infer_pattern(samples, "id") == "integer_id"
    assert infer_pattern(samples, "code_no") == "integer_id"


def test_type_meta_parsing():
    assert parse_type_meta("VARCHAR2(100)") == ("varchar2", 100, None)
    assert parse_type_meta("NUMBER(10, 2)") == ("number", 10, 2)
    assert parse_type_meta("NUMBER(5)") == ("number", 5, None)
    assert parse_type_meta("CLOB") == ("clob", None, None)
    assert parse_type_meta("NUMBER") == ("number", None, None)


def test_type_compatibility():
    # 1. Oracle NUMBER(p,0) resolved as integer
    assert type_compatible("NUMBER(10,0)", "INTEGER") == 1.0
    assert type_compatible("INTEGER", "NUMBER(10,0)") == 1.0

    # 2. Oracle NUMBER(p,s) with s > 0 resolved as decimal
    assert type_compatible("NUMBER(10,2)", "INTEGER") == 0.75  # int to dec is compatible but close (0.75)
    assert type_compatible("NUMBER(10,2)", "NUMBER(12,4)") == 1.0  # both dec

    # 3. Truncation check
    assert type_compatible("VARCHAR2(100)", "VARCHAR2(50)") == 0.85
    assert type_compatible("VARCHAR2(50)", "VARCHAR2(100)") == 1.0

    # 4. CLOB to VARCHAR truncation risk
    assert type_compatible("CLOB", "VARCHAR2(50)") == 0.70
    assert type_compatible("VARCHAR2(50)", "CLOB") == 1.0


def test_widen_pii_masking():
    # Standard PII pattern matching
    assert should_mask("email_address", "email") is True
    
    # Expanded PII name hints
    assert should_mask("first_name", "unknown") is True
    assert should_mask("fname", "unknown") is True
    assert should_mask("customer_balance", "unknown") is True
    assert should_mask("billing_address", "unknown") is True
    assert should_mask("bank_acct_no", "unknown") is True
    
    # Non-PII fields
    assert should_mask("order_qty", "unknown") is False
    assert should_mask("product_description", "unknown") is False
