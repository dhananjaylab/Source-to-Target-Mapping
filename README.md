# 🗄️ Oracle Source to Target Schema Mapping 

> **AI-assisted Oracle source-to-target column mapping** — powered by **Gemini 2.0 Flash**, 
> **FastAPI**, and **Streamlit**.

Automatically maps source Oracle schema columns to target Oracle schema columns using four 
complementary signals: name similarity, sample data patterns, type compatibility, and Gemini 
semantic reasoning. Returns confidence-scored mappings with explainable rationale and a full 
human-review workflow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                       │
│  Setup → Generate → Review → Export                         │
└───────────────────┬─────────────────────────────────────────┘
                    │  HTTP (REST)
┌───────────────────▼─────────────────────────────────────────┐
│                   FastAPI Backend                           │
│  /projects  /schemas  /profiles  /mappings  /exports        │
└──────┬──────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────┐    ┌──────────────────────────────┐
│   Mapping Engine        │    │   Gemini Service            │
│  • Pattern inference    │───▶│  • Prompt builder           │
│  • Name similarity      │    │  • Gemini 2.0 Flash API call │
│  • Type compatibility   │    │  • JSON extraction           │
│  • Parallel profiler    │    │  • Validation                │
└─────────────────────────┘    └──────────────────────────────┘
       │
┌──────▼──────────────────┐
│   In-memory State Store  │
│  (SQLite / Oracle in prod)│
└──────────────────────────┘
```

## Four Mapping Signals

| Signal | Description |
|--------|-------------|
| 🔤 **Name Similarity** | Abbreviation expansion (cust→customer, dt→date, amt→amount, qty→quantity, prc→price, addr→address, ph→phone) + token overlap scoring |
| 🔬 **Sample Patterns** | Pre-compiled regex classifiers: email, UUID, ISO date, phone, currency, boolean flag, integer ID (70% sample threshold) |
| 📐 **Type Compatibility** | Broadened type families: INTEGER≈BIGINT≈NUMBER, VARCHAR≈VARCHAR2≈NVARCHAR, DATE vs TIMESTAMP |
| 🧠 **Semantic Reasoning** | Gemini reasons over column descriptions, patterns, and context to handle everything rule-based signals miss |

## Confidence Score Rubric

| Range | Tier | Meaning | Example |
|-------|------|---------|---------|
| 0.95 – 1.00 | **EXACT** | Exact name + matching type + sample pattern | `order_id → order_id` |
| 0.80 – 0.94 | **CLEAR** | Clear abbreviation + compatible type | `cust_id → customer_id` |
| 0.60 – 0.79 | **PROBABLE** | Probable via semantics + compatible pattern | `ph_num → phone_number` |
| 0.40 – 0.59 | **POSSIBLE** | Some signals align but ambiguous | `ref_code → external_ref` |
| 0.00 – 0.39 | **LOW** | No confident match → unmapped | `legacy_flag → (unmapped)` |

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd oracle_mapping_copilot
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get a free Gemini API key at: https://aistudio.google.com/apikey

### 3. Start the FastAPI Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

### 4. Start the Streamlit Frontend

```bash
cd frontend
streamlit run app.py
```

App available at: http://localhost:8501

---

## Project Structure

```
oracle_mapping_copilot/
├── backend/
│   ├── main.py              # FastAPI application — all endpoints
│   ├── models.py            # Pydantic request/response models
│   ├── state_store.py       # In-memory store (replace with DB in prod)
│   ├── gemini_service.py    # Gemini LLM integration + prompt builder
│   └── mapping_engine.py   # Pattern inference, name similarity, profiler
├── frontend/
│   └── app.py               # Streamlit UI — full 4-step workflow
├── sample_schemas/
│   └── schemas.json         # Demo Oracle source + target schemas
├── exports/                 # Generated mapping artifacts
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/projects` | List all projects |
| POST | `/projects` | Create a project |
| GET | `/schemas/source` | List source tables |
| GET | `/schemas/target` | List target tables |
| GET | `/schemas/source/{table}` | Get source table schema |
| GET | `/schemas/target/{table}` | Get target table schema |
| POST | `/projects/{id}/profiles` | Build enriched column profiles |
| POST | `/projects/{id}/mappings/generate/sync` | Generate mappings (sync, for Streamlit) |
| POST | `/projects/{id}/mappings/generate` | Generate mappings (async background) |
| GET | `/projects/{id}/mappings/{run_id}` | Get run status and results |
| POST | `/projects/{id}/mappings/{run_id}/review` | Submit review actions (approve/reject) |
| POST | `/projects/{id}/exports` | Export as JSON or CSV |
| GET | `/audit` | Audit log |

---

## Demo Schemas Included

**Source tables:**
- `CRM_CUSTOMERS` — 10 columns with typical CRM abbreviations
- `ORD_TRANSACTIONS` — 9 columns, order management system
- `INV_PRODUCTS` — 8 columns, product inventory

**Target tables:**
- `DIM_CUSTOMER` — DW customer dimension
- `FACT_ORDERS` — DW orders fact table  
- `DIM_PRODUCT` — DW product dimension

---

## Production Extensions

To connect to a real Oracle database, uncomment `cx_Oracle` or `oracledb` in `requirements.txt` 
and replace the `state_store.py` schema methods with actual Oracle queries using:

```sql
SELECT column_name, data_type, nullable, comments
FROM   all_tab_columns atc
JOIN   all_col_comments acc USING (owner, table_name, column_name)
WHERE  atc.owner = :schema AND atc.table_name = :table
ORDER  BY column_id
```

---

## Test Results (Demo Run)

- `CRM_CUSTOMERS → DIM_CUSTOMER`: 8/10 columns correctly mapped including all abbreviation pairs
- `ORD_TRANSACTIONS → FACT_ORDERS`: 8/9 columns mapped, including `ttl_amt → total_amount`, `ord_dt → sale_date`
- ETL columns (`etl_batch_id`, `load_timestamp`) correctly unmapped in every run
- Surrogate keys (`customer_key`, `order_key`) correctly excluded
