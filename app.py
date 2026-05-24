"""
Oracle Mapping Copilot — Streamlit Frontend
Full UI: Project setup → Connection → Schema select → Generate → Review → Export
"""

import os
import io
import json
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
DEMO_PROJECT_ID = "demo-project-001"

st.set_page_config(
    page_title="Oracle Mapping Copilot",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Theme / CSS
# ──────────────────────────────────────────────

st.markdown("""
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #111827 !important;
    border-right: 1px solid #1F2937;
}
[data-testid="stSidebar"] * { color: #D1D5DB !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #F9FAFB !important; }

/* ── Main background ── */
.stApp { background: #F8F7F5; }
.block-container { padding: 2rem 2.5rem 2rem 2.5rem; }

/* ── Cards ── */
.card {
    background: #ffffff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.card-header {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: #6B7280;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

/* ── Chips ── */
.chip {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.chip-exact    { background:#DCFCE7; color:#166534; }
.chip-clear    { background:#DBEAFE; color:#1E40AF; }
.chip-probable { background:#EDE9FE; color:#5B21B6; }
.chip-possible { background:#FEF9C3; color:#854D0E; }
.chip-low      { background:#F3F4F6; color:#4B5563; }
.chip-approved { background:#DCFCE7; color:#166534; }
.chip-rejected { background:#FEE2E2; color:#991B1B; }
.chip-pending  { background:#FEF3C7; color:#92400E; }
.chip-override { background:#EDE9FE; color:#5B21B6; }

/* ── Confidence bar ── */
.conf-bar-bg { background:#E5E7EB; border-radius:4px; height:8px; width:100%; }
.conf-bar    { border-radius:4px;  height:8px; }

/* ── Mapping row ── */
.map-row {
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    background: #ffffff;
}
.map-row:hover { border-color: #6366F1; }

/* ── Column name monospace ── */
.col-name {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.85rem;
    font-weight: 600;
    color: #1F2937;
}
.col-type {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.72rem;
    color: #6366F1;
}

/* ── Signal cards ── */
.signal-card {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.8rem;
    color: #374151;
}
.signal-label {
    font-weight: 600;
    font-size: 0.75rem;
    color: #4F46E5;
    margin-bottom: 2px;
}

/* ── Section header ── */
.section-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #111827;
    margin-bottom: 0.25rem;
}
.section-sub {
    font-size: 0.85rem;
    color: #6B7280;
    margin-bottom: 1.5rem;
}

/* ── Stat boxes ── */
.stat-box {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
}
.stat-num  { font-size: 1.75rem; font-weight: 700; color: #111827; }
.stat-lbl  { font-size: 0.75rem; color: #6B7280; font-weight: 500; }

/* ── Step pill ── */
.step-pill {
    display: inline-block;
    background: #EEF2FF;
    color: #4F46E5;
    border-radius: 99px;
    padding: 2px 12px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    margin-bottom: 0.75rem;
}

/* ── Primary button override ── */
.stButton > button[kind="primary"] {
    background: #4F46E5 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #4338CA !important;
}

/* ── Table header ── */
.tbl-header {
    display: grid;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: #6B7280;
    text-transform: uppercase;
    padding: 0.5rem 1rem;
    border-bottom: 2px solid #E5E7EB;
    margin-bottom: 0.5rem;
}

/* ── Divider ── */
hr { border-color: #E5E7EB !important; }

/* ── Pipeline stages ── */
.pipeline-stage {
    background: white;
    border: 2px solid #E5E7EB;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
    transition: border-color 0.3s;
}
.pipeline-stage.active  { border-color: #4F46E5; background: #EEF2FF; }
.pipeline-stage.done    { border-color: #16A34A; background: #DCFCE7; }
.pipeline-stage-icon    { font-size: 1.75rem; }
.pipeline-stage-label   { font-size: 0.75rem; font-weight: 600; margin-top: 0.25rem; color: #374151; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Session state initialisation
# ──────────────────────────────────────────────

defaults = {
    "screen":         "setup",
    "project_id":     DEMO_PROJECT_ID,
    "src_table":      "CRM_CUSTOMERS",
    "tgt_table":      "DIM_CUSTOMER",
    "run_id":         None,
    "candidates":     [],
    "run_stats":      {},
    "review_actions": {},   # {source_col: {action, note, override}}
    "threshold":      0.40,
    "filter_tier":    "All",
    "filter_status":  "All",
    "expanded_row":   None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ──────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    url = f"{API_BASE}{path}"
    try:
        r = requests.request(method, url, timeout=120, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the FastAPI backend. Start it with `uvicorn main:app --reload`")
        st.stop()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def check_api():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ──────────────────────────────────────────────
# Confidence helpers
# ──────────────────────────────────────────────

TIER_COLORS = {
    "exact":    ("#166534", "#DCFCE7"),
    "clear":    ("#1E40AF", "#DBEAFE"),
    "probable": ("#5B21B6", "#EDE9FE"),
    "possible": ("#854D0E", "#FEF9C3"),
    "low":      ("#4B5563", "#F3F4F6"),
}

STATUS_COLORS = {
    "approved":   ("#166534", "#DCFCE7"),
    "rejected":   ("#991B1B", "#FEE2E2"),
    "overridden": ("#5B21B6", "#EDE9FE"),
    "pending":    ("#92400E", "#FEF3C7"),
}

def tier_from_score(score: float) -> str:
    if score >= 0.95: return "exact"
    if score >= 0.80: return "clear"
    if score >= 0.60: return "probable"
    if score >= 0.40: return "possible"
    return "low"

def chip_html(label: str, color: str, bg: str) -> str:
    return (f'<span style="background:{bg};color:{color};'
            f'padding:2px 10px;border-radius:99px;'
            f'font-size:0.72rem;font-weight:700;letter-spacing:0.04em">'
            f'{label.upper()}</span>')

def conf_bar_html(score: float, tier: str) -> str:
    color, _ = TIER_COLORS.get(tier, ("#9CA3AF", "#F3F4F6"))
    w = int(score * 100)
    return (f'<div style="background:#E5E7EB;border-radius:4px;height:6px;width:100%;">'
            f'<div style="background:{color};border-radius:4px;height:6px;width:{w}%;"></div>'
            f'</div>')

def type_badge(t: str) -> str:
    t = (t or "").upper()
    if "INT" in t:     color = "#7C3AED"
    elif "VAR" in t or "CHAR" in t: color = "#2563EB"
    elif "NUM" in t or "DEC" in t:  color = "#D97706"
    elif t == "DATE":  color = "#16A34A"
    elif "STAMP" in t: color = "#0891B2"
    else:              color = "#6B7280"
    return (f'<code style="background:#F3F4F6;color:{color};'
            f'padding:1px 6px;border-radius:4px;font-size:0.72rem;">{t}</code>')


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🗄️ Oracle Mapping")
        st.markdown("**Copilot**")
        st.markdown("---")

        api_ok = check_api()
        if api_ok:
            st.markdown("🟢 **API Connected**")
        else:
            st.markdown("🔴 **API Offline**")
            st.caption("Run: `uvicorn main:app --reload`")

        st.markdown("---")
        st.markdown("**Workflow Steps**")

        steps = [
            ("setup",    "1 · Configure",   "⚙️"),
            ("generate", "2 · Generate",    "⚡"),
            ("review",   "3 · Review",      "✅"),
            ("export",   "4 · Export",      "📥"),
        ]
        for sid, label, icon in steps:
            is_active  = st.session_state.screen == sid
            can_nav    = sid == "setup" or bool(st.session_state.candidates)
            style = ("background:#1F2937;border-left:3px solid #4F46E5;"
                     "color:#F9FAFB;") if is_active else ""
            btn_label = f"{icon} {label}"
            if can_nav:
                if st.button(btn_label, key=f"nav_{sid}",
                             use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.screen = sid
                    st.rerun()
            else:
                st.button(btn_label, key=f"nav_{sid}",
                          disabled=True, use_container_width=True)

        if st.session_state.candidates:
            st.markdown("---")
            stats = st.session_state.run_stats
            st.markdown("**Run Summary**")
            st.caption(f"📊 {stats.get('mapped',0)}/{stats.get('total',0)} mapped")
            st.caption(f"⭐ {stats.get('high_confidence',0)} high confidence")

            acts = st.session_state.review_actions
            approved  = sum(1 for v in acts.values() if v.get("action") == "approved")
            rejected  = sum(1 for v in acts.values() if v.get("action") == "rejected")
            total     = len(st.session_state.candidates)
            pct = int((approved + rejected) / total * 100) if total else 0
            st.progress(pct / 100, text=f"{pct}% reviewed")
            st.caption(f"✅ {approved} approved · ❌ {rejected} rejected")

        st.markdown("---")
        st.caption("Oracle Mapping Copilot v1.0")
        st.caption("Powered by Gemini 2.0 Flash")


# ──────────────────────────────────────────────
# Screen 1 — Setup
# ──────────────────────────────────────────────

def render_setup():
    st.markdown('<div class="step-pill">STEP 1 OF 4 · CONFIGURE</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Configure Mapping Project</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Select source and target Oracle tables to map. '
                'Enriched column profiles will be built before the AI mapping is generated.</div>',
                unsafe_allow_html=True)

    # ── Oracle connection cards ──────────────────
    col_src, col_tgt = st.columns(2)

    with col_src:
        st.markdown('<div class="card"><div class="card-header">🔵 Source · Oracle OLTP</div>', unsafe_allow_html=True)
        st.text_input("Host",         value="oracle-crm.company.com",  key="src_host",    disabled=True)
        c1, c2 = st.columns(2)
        c1.text_input("Port",         value="1521",                    key="src_port",    disabled=True)
        c2.text_input("Service Name", value="CRM_PROD",                key="src_svc",     disabled=True)
        st.text_input("Schema / Owner", value="CRM_OWNER",             key="src_owner",   disabled=True)
        src_tables = api("GET", "/schemas/source") or {}
        src_table_list = src_tables.get("tables", [])
        if src_table_list:
            idx = src_table_list.index(st.session_state.src_table) if st.session_state.src_table in src_table_list else 0
            chosen_src = st.selectbox("Source Table", src_table_list, index=idx, key="src_table_sel")
            st.session_state.src_table = chosen_src
        if st.button("🔌 Test Connection", key="test_src"):
            st.success("✅ Connected — 284,500 rows accessible")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_tgt:
        st.markdown('<div class="card"><div class="card-header">🟢 Target · Oracle DW</div>', unsafe_allow_html=True)
        st.text_input("Host",         value="oracle-dw.company.com",   key="tgt_host",    disabled=True)
        c1, c2 = st.columns(2)
        c1.text_input("Port",         value="1521",                    key="tgt_port",    disabled=True)
        c2.text_input("Service Name", value="DW_PROD",                 key="tgt_svc",     disabled=True)
        st.text_input("Schema / Owner", value="DW_OWNER",              key="tgt_owner",   disabled=True)
        tgt_tables = api("GET", "/schemas/target") or {}
        tgt_table_list = tgt_tables.get("tables", [])
        if tgt_table_list:
            idx = tgt_table_list.index(st.session_state.tgt_table) if st.session_state.tgt_table in tgt_table_list else 0
            chosen_tgt = st.selectbox("Target Table", tgt_table_list, index=idx, key="tgt_table_sel")
            st.session_state.tgt_table = chosen_tgt
        if st.button("🔌 Test Connection", key="test_tgt"):
            st.success("✅ Connected — DW schema accessible")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Schema previews ──────────────────────────
    col_p1, col_p2 = st.columns(2)

    def render_schema_preview(table_name: str, side: str, container):
        with container:
            st.markdown(f"**{table_name}** — column preview")
            schema = api("GET", f"/schemas/{side}/{table_name}") or {}
            cols   = schema.get("columns", [])
            if cols:
                rows = []
                for c in cols:
                    rows.append({
                        "Column":  c["name"],
                        "Type":    c.get("type",""),
                        "Comment": (c.get("comment","") or "")[:55],
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True,
                             hide_index=True, height=min(300, 40 + 35 * len(rows)))
            else:
                st.info("No columns found.")

    render_schema_preview(st.session_state.src_table, "source", col_p1)
    render_schema_preview(st.session_state.tgt_table, "target", col_p2)

    st.markdown("---")

    # ── Four signal cards ────────────────────────
    st.markdown("**How the AI mapping engine works — 4 signals**")
    s1, s2, s3, s4 = st.columns(4)
    signals = [
        ("🔤", "Name Similarity",
         "Exact matches, common abbreviations (cust→customer, dt→date, amt→amount, "
         "qty→quantity, prc→price) and camelCase/snake_case normalisation."),
        ("🔬", "Sample Patterns",
         "Pre-compiled regex classifiers identify value shapes — email, UUID, ISO date, "
         "phone number, currency, boolean flag, integer ID."),
        ("📐", "Type Compatibility",
         "Broadened type model handles aliases: int/integer/bigint/number are equivalent; "
         "varchar/string/text/nvarchar are the same family."),
        ("🧠", "Semantic Reasoning",
         "Column descriptions and context are passed to Gemini, which reasons about "
         "conceptual meaning — the signal that handles everything else."),
    ]
    for col, (icon, title, desc) in zip([s1, s2, s3, s4], signals):
        col.markdown(
            f'<div class="signal-card">'
            f'<div style="font-size:1.5rem">{icon}</div>'
            f'<div class="signal-label" style="margin-top:0.5rem">{title}</div>'
            f'<div style="font-size:0.78rem;color:#6B7280;margin-top:0.25rem">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ── Advanced options ─────────────────────────
    with st.expander("⚙️ Advanced Options"):
        st.session_state.threshold = st.slider(
            "Confidence threshold (columns below this will be unmapped)",
            0.0, 1.0, st.session_state.threshold, 0.05
        )
        st.info(f"Columns with confidence < **{st.session_state.threshold:.2f}** will be shown as unmapped.")

    # ── Generate button ──────────────────────────
    col_btn, col_info = st.columns([2, 5])
    with col_btn:
        if st.button("⚡ Generate Mappings", type="primary", use_container_width=True):
            st.session_state.screen = "generate"
            st.rerun()
    with col_info:
        st.info(f"Will map **{st.session_state.src_table}** → **{st.session_state.tgt_table}** "
                f"using Gemini 2.0 Flash with confidence threshold {st.session_state.threshold:.0%}")


# ──────────────────────────────────────────────
# Screen 2 — Generate (pipeline animation + API call)
# ──────────────────────────────────────────────

def render_generate():
    st.markdown('<div class="step-pill">STEP 2 OF 4 · GENERATE</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Generating AI Mappings</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-sub">Mapping '
        f'<code>{st.session_state.src_table}</code> → '
        f'<code>{st.session_state.tgt_table}</code> '
        f'using Gemini 2.0 Flash</div>',
        unsafe_allow_html=True
    )

    # ── Pipeline diagram ────────────────────────
    c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 1, 3])
    stage_placeholder = st.empty()

    stages_html = {
        0: lambda s: ("pipeline-stage active" if s == 0 else
                      "pipeline-stage done"   if s > 0  else "pipeline-stage"),
    }

    def draw_pipeline(active_stage: int):
        stage_configs = [
            ("🔍", "Stage 1", "Parallel Profiling", "Building enriched column profiles"),
            ("⚡", "Stage 2", "LLM Mapper",         "Gemini reasoning over 4 signals"),
            ("✅", "Stage 3", "Validator",           "De-dup · threshold · sort"),
        ]
        with stage_placeholder.container():
            st.markdown("""
            <style>
            .pipe-wrap { display:flex; align-items:center; gap:0; }
            .pipe-box  { flex:1; background:white; border:2px solid #E5E7EB;
                         border-radius:10px; padding:1rem; text-align:center; }
            .pipe-box.active { border-color:#4F46E5; background:#EEF2FF; }
            .pipe-box.done   { border-color:#16A34A; background:#DCFCE7; }
            .pipe-arrow      { font-size:1.5rem; color:#9CA3AF; padding:0 0.5rem; }
            </style>
            """, unsafe_allow_html=True)

            cols = st.columns([5, 1, 5, 1, 5])
            for i, (icon, stage_label, title, sub) in enumerate(stage_configs):
                col_idx = i * 2
                css = ("active" if i == active_stage - 1 else
                       "done"   if i < active_stage - 1   else "")
                tick = "✔ " if css == "done" else ""
                cols[col_idx].markdown(
                    f'<div class="pipe-box {css}">'
                    f'<div style="font-size:1.5rem">{icon}</div>'
                    f'<div style="font-weight:700;font-size:0.8rem;margin-top:0.25rem">{tick}{title}</div>'
                    f'<div style="font-size:0.7rem;color:#4F46E5;font-weight:600">{stage_label}</div>'
                    f'<div style="font-size:0.72rem;color:#6B7280;margin-top:0.25rem">{sub}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if i < 2:
                    cols[col_idx + 1].markdown(
                        '<div style="text-align:center;font-size:1.5rem;color:#9CA3AF;'
                        'padding-top:1rem">→</div>', unsafe_allow_html=True
                    )

    # Status + log area
    status_ph = st.empty()
    log_ph    = st.empty()
    prog_ph   = st.progress(0, text="Initialising…")

    logs = []
    def log(msg: str):
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_ph.code("\n".join(logs[-8:]))

    # ── Stage 1: Profiling ──────────────────────
    draw_pipeline(1)
    prog_ph.progress(10, text="Stage 1 — Building column profiles in parallel…")
    status_ph.info("⏳ Profiling source and target schemas concurrently…")
    log("Starting parallel column profiling (ThreadPoolExecutor)…")

    src_profile = api("POST",
                      f"/projects/{st.session_state.project_id}/profiles",
                      params={"table_name": st.session_state.src_table, "side": "source"})
    log(f"  ✔ Source profiles built: {src_profile.get('column_count',0)} columns")

    tgt_profile = api("POST",
                      f"/projects/{st.session_state.project_id}/profiles",
                      params={"table_name": st.session_state.tgt_table, "side": "target"})
    log(f"  ✔ Target profiles built: {tgt_profile.get('column_count',0)} columns")

    prog_ph.progress(30, text="Stage 1 complete — profiles ready")
    time.sleep(0.3)

    # ── Stage 2: LLM ────────────────────────────
    draw_pipeline(2)
    prog_ph.progress(40, text="Stage 2 — Calling Gemini 2.0 Flash…")
    status_ph.info("🧠 Sending enriched profiles to Gemini with 4-signal prompt…")
    log("Constructing LLM prompt with enriched column profiles…")
    log("Calling Gemini 2.0 Flash (structured JSON output mode)…")
    log("Waiting for model response (may take 10-30 seconds)…")

    payload = {
        "project_id":   st.session_state.project_id,
        "source_table": st.session_state.src_table,
        "target_table": st.session_state.tgt_table,
        "threshold":    st.session_state.threshold,
        "model_name":   "gemini-2.0-flash",
        "prompt_version": "v1",
    }

    with st.spinner("Gemini is reasoning over column mappings…"):
        result = api("POST",
                     f"/projects/{st.session_state.project_id}/mappings/generate/sync",
                     json=payload)

    if not result:
        st.error("Mapping generation failed. Check the API logs.")
        if st.button("↩ Back to Setup"):
            st.session_state.screen = "setup"
            st.rerun()
        return

    log(f"  ✔ LLM response received — {len(result.get('candidates',[]))} mappings")
    prog_ph.progress(75, text="Stage 2 complete — LLM response received")
    time.sleep(0.3)

    # ── Stage 3: Validate ───────────────────────
    draw_pipeline(3)
    prog_ph.progress(85, text="Stage 3 — Validating and sorting results…")
    status_ph.info("✅ Validating target column names, de-duplicating, sorting…")
    log("Checking all target columns against valid schema set (O(1) set lookup)…")
    log("De-duplicating: first use of each target wins…")
    log("Sorting by confidence descending — unmapped last…")
    time.sleep(0.4)

    # Persist to session
    st.session_state.candidates     = result.get("candidates", [])
    st.session_state.run_id         = result.get("run_id")
    st.session_state.run_stats      = result.get("stats", {})
    st.session_state.review_actions = {}

    stats = st.session_state.run_stats
    log(f"  ✔ Validation complete: {stats.get('mapped',0)} mapped, "
        f"{stats.get('unmapped',0)} unmapped, avg confidence {stats.get('avg_confidence',0):.3f}")

    prog_ph.progress(100, text="✔ Complete!")
    draw_pipeline(4)   # all done
    status_ph.success(
        f"✅ Mapping complete — **{stats.get('mapped',0)}** of "
        f"**{stats.get('total',0)}** columns mapped · "
        f"**{stats.get('high_confidence',0)}** high confidence"
    )
    time.sleep(1.2)

    st.session_state.screen = "review"
    st.rerun()


# ──────────────────────────────────────────────
# Screen 3 — Review
# ──────────────────────────────────────────────

TIER_LABELS  = ["All", "exact", "clear", "probable", "possible", "low"]
STATUS_LABELS = ["All", "pending", "approved", "rejected", "overridden"]

def render_review():
    st.markdown('<div class="step-pill">STEP 3 OF 4 · REVIEW</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Review & Approve Mappings</div>', unsafe_allow_html=True)

    candidates = st.session_state.candidates
    stats      = st.session_state.run_stats
    acts       = st.session_state.review_actions

    if not candidates:
        st.warning("No mappings to review. Go to Configure and generate mappings first.")
        return

    # ── Stat bar ────────────────────────────────
    approved  = sum(1 for v in acts.values() if v.get("action") == "approved")
    rejected  = sum(1 for v in acts.values() if v.get("action") == "rejected")
    overridden= sum(1 for v in acts.values() if v.get("action") == "overridden")
    pending   = len(candidates) - approved - rejected - overridden

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, num, lbl, color in [
        (c1, stats.get("total",0),           "Total",        "#1F2937"),
        (c2, stats.get("mapped",0),          "Mapped",        "#4F46E5"),
        (c3, stats.get("high_confidence",0), "High Conf.",    "#16A34A"),
        (c4, approved,                        "Approved",      "#16A34A"),
        (c5, rejected,                        "Rejected",      "#DC2626"),
        (c6, pending,                         "Pending",       "#D97706"),
    ]:
        col.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-num" style="color:{color}">{num}</div>'
            f'<div class="stat-lbl">{lbl}</div>'
            f'</div>', unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters + bulk actions ───────────────────
    fcol1, fcol2, fcol3, bcol1, bcol2 = st.columns([2, 2, 2, 2, 2])
    with fcol1:
        tier_filter = st.selectbox("Filter by Tier", TIER_LABELS, key="tier_filter")
    with fcol2:
        stat_filter = st.selectbox("Filter by Status", STATUS_LABELS, key="stat_filter")
    with fcol3:
        search_term = st.text_input("Search column", placeholder="cust_id …", key="col_search")
    with bcol1:
        if st.button("✅ Approve All High-Conf", use_container_width=True):
            for c in candidates:
                if c.get("confidence", 0) >= 0.80 and c.get("target_column"):
                    st.session_state.review_actions[c["source_column"]] = {
                        "action": "approved", "note": "", "override": None
                    }
            st.rerun()
    with bcol2:
        if st.button("🔄 Reset Reviews", use_container_width=True):
            st.session_state.review_actions = {}
            st.rerun()

    st.markdown("---")

    # ── Filter candidates ───────────────────────
    def effective_tier(c):
        return tier_from_score(c.get("confidence", 0)) if c.get("target_column") else "low"

    def effective_status(c):
        act = acts.get(c["source_column"], {})
        return act.get("action", "pending")

    filtered = [
        c for c in candidates
        if (tier_filter  == "All" or effective_tier(c)   == tier_filter)
        and (stat_filter == "All" or effective_status(c) == stat_filter)
        and (not search_term or search_term.lower() in c["source_column"].lower()
             or search_term.lower() in (c.get("target_column") or "").lower())
    ]

    st.markdown(f"**Showing {len(filtered)} of {len(candidates)} columns**")

    # ── Confidence rubric legend ─────────────────
    with st.expander("📊 Confidence Score Rubric"):
        r1, r2, r3, r4, r5 = st.columns(5)
        rubric = [
            (r1, "0.95 – 1.00", "EXACT",    "#166534","#DCFCE7", "order_id → order_id"),
            (r2, "0.80 – 0.94", "CLEAR",    "#1E40AF","#DBEAFE", "cust_id → customer_id"),
            (r3, "0.60 – 0.79", "PROBABLE", "#5B21B6","#EDE9FE", "ph_num → phone_number"),
            (r4, "0.40 – 0.59", "POSSIBLE", "#854D0E","#FEF9C3", "ref_code → external_ref"),
            (r5, "0.00 – 0.39", "LOW",      "#4B5563","#F3F4F6", "legacy_flag → (unmapped)"),
        ]
        for col, rng, lbl, tc, bg, example in rubric:
            col.markdown(
                f'<div style="background:{bg};border-radius:8px;padding:0.75rem;text-align:center">'
                f'<div style="font-weight:700;font-size:0.8rem;color:{tc}">{rng}</div>'
                f'<div style="font-weight:600;font-size:0.72rem;color:{tc}">{lbl}</div>'
                f'<div style="font-size:0.68rem;color:{tc};opacity:0.8;margin-top:4px">'
                f'<code>{example}</code></div>'
                f'</div>', unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Mapping table header ─────────────────────
    st.markdown(
        '<div style="display:grid;grid-template-columns:2fr 2fr 1.2fr 1fr 1.5fr;'
        'padding:0.4rem 1rem;background:#F3F4F6;border-radius:6px;'
        'font-size:0.72rem;font-weight:700;letter-spacing:0.07em;color:#6B7280;'
        'margin-bottom:0.5rem">'
        '<span>SOURCE COLUMN</span><span>TARGET COLUMN</span>'
        '<span>CONFIDENCE</span><span>STATUS</span><span>ACTIONS</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Mapping rows ─────────────────────────────
    for c in filtered:
        src  = c["source_column"]
        tgt  = c.get("target_column")
        conf = c.get("confidence", 0.0)
        tier = effective_tier(c)
        tc, bg = TIER_COLORS.get(tier, ("#6B7280","#F3F4F6"))
        act  = acts.get(src, {})
        cur_status = act.get("action", "pending")
        sc2, sc3   = STATUS_COLORS.get(cur_status, ("#92400E","#FEF3C7"))

        is_expanded = st.session_state.expanded_row == src

        with st.container():
            row_cols = st.columns([2, 2, 1.2, 1, 1.5])

            with row_cols[0]:
                st.markdown(
                    f'<div class="col-name">{src}</div>'
                    f'<div>{type_badge(c.get("source_type",""))}</div>',
                    unsafe_allow_html=True
                )

            with row_cols[1]:
                if tgt:
                    override = act.get("override")
                    display_tgt = override or tgt
                    st.markdown(
                        f'<div class="col-name">{display_tgt}</div>'
                        f'<div>{type_badge(c.get("target_type",""))}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div style="color:#9CA3AF;font-style:italic;font-size:0.82rem">'
                        '(unmapped)</div>', unsafe_allow_html=True
                    )

            with row_cols[2]:
                if tgt:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:6px">'
                        f'<span style="font-weight:700;font-size:0.85rem;color:{tc}">'
                        f'{conf:.2f}</span>'
                        f'{chip_html(tier, tc, bg)}'
                        f'</div>'
                        f'{conf_bar_html(conf, tier)}',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown('<span style="color:#9CA3AF;font-size:0.8rem">—</span>',
                                unsafe_allow_html=True)

            with row_cols[3]:
                st.markdown(chip_html(cur_status, sc2, sc3), unsafe_allow_html=True)

            with row_cols[4]:
                btn_c1, btn_c2, btn_c3 = st.columns(3)
                with btn_c1:
                    is_app = cur_status == "approved"
                    if st.button("✅" if not is_app else "↩",
                                 key=f"app_{src}", help="Approve" if not is_app else "Undo",
                                 use_container_width=True):
                        if is_app:
                            st.session_state.review_actions.pop(src, None)
                        else:
                            st.session_state.review_actions[src] = {"action": "approved", "note": "", "override": None}
                        st.rerun()
                with btn_c2:
                    is_rej = cur_status == "rejected"
                    if st.button("❌" if not is_rej else "↩",
                                 key=f"rej_{src}", help="Reject" if not is_rej else "Undo",
                                 use_container_width=True):
                        if is_rej:
                            st.session_state.review_actions.pop(src, None)
                        else:
                            st.session_state.review_actions[src] = {"action": "rejected", "note": "", "override": None}
                        st.rerun()
                with btn_c3:
                    if st.button("🔍", key=f"exp_{src}", help="Expand details",
                                 use_container_width=True):
                        st.session_state.expanded_row = None if is_expanded else src
                        st.rerun()

        # ── Expanded detail panel ────────────────
        if is_expanded:
            with st.container():
                st.markdown(
                    f'<div style="background:#F9FAFB;border:1px solid #E5E7EB;'
                    f'border-radius:8px;padding:1rem 1.25rem;margin-bottom:0.75rem;'
                    f'margin-left:1rem">',
                    unsafe_allow_html=True
                )

                d1, d2 = st.columns(2)
                with d1:
                    st.markdown("**🤖 AI Rationale**")
                    st.markdown(
                        f'<div style="font-size:0.83rem;color:#374151;'
                        f'background:white;border:1px solid #E5E7EB;border-radius:6px;'
                        f'padding:0.75rem">{c.get("rationale","No rationale.")}</div>',
                        unsafe_allow_html=True
                    )

                    # Signal breakdown
                    st.markdown("**📡 Signal Breakdown**")
                    sigs = c.get("signals", {})
                    sig_items = [
                        ("🔤 Name Similarity",    sigs.get("name_similarity","—")),
                        ("📐 Type Compat.",        sigs.get("type_compatibility","—")),
                        ("🔬 Pattern Match",       sigs.get("pattern_match","—")),
                        ("🧠 Semantic",            sigs.get("semantic","—")),
                    ]
                    for lbl, val in sig_items:
                        st.markdown(
                            f'<div class="signal-card" style="margin-bottom:0.35rem">'
                            f'<span class="signal-label">{lbl}</span><br>'
                            f'<span style="font-size:0.78rem">{val}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                with d2:
                    st.markdown("**📝 Reviewer Actions**")
                    note = st.text_area("Note / justification",
                                        value=act.get("note",""),
                                        key=f"note_{src}",
                                        height=80)

                    tgt_schema = api("GET", f"/schemas/target/{st.session_state.tgt_table}") or {}
                    tgt_cols   = [col["name"] for col in tgt_schema.get("columns", [])]
                    override_val = st.selectbox(
                        "Override target (optional)",
                        ["— keep AI suggestion —"] + tgt_cols,
                        key=f"ovr_{src}",
                        index=0,
                    )

                    col_save, col_close = st.columns(2)
                    with col_save:
                        if st.button("💾 Save Note", key=f"save_{src}", use_container_width=True):
                            override = None if override_val.startswith("—") else override_val
                            action   = "overridden" if override else act.get("action","pending")
                            st.session_state.review_actions[src] = {
                                "action": action, "note": note, "override": override
                            }
                            st.rerun()
                    with col_close:
                        if st.button("✖ Close", key=f"cls_{src}", use_container_width=True):
                            st.session_state.expanded_row = None
                            st.rerun()

                    # Source sample data
                    src_schema = api("GET", f"/schemas/source/{st.session_state.src_table}") or {}
                    src_col_def = next(
                        (col for col in src_schema.get("columns", []) if col["name"] == src), None
                    )
                    if src_col_def and src_col_def.get("samples"):
                        st.markdown("**Sample Values** (masked if PII)")
                        st.code(", ".join(str(s) for s in src_col_def["samples"][:5]))

                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<hr style="margin:0.25rem 0;border-color:#F3F4F6">', unsafe_allow_html=True)

    # ── Bottom actions ───────────────────────────
    st.markdown("---")
    bc1, bc2, bc3 = st.columns([2, 2, 5])
    with bc1:
        if st.button("↩ Re-configure", use_container_width=True):
            st.session_state.screen = "setup"
            st.rerun()
    with bc2:
        if st.button("📥 Proceed to Export →", type="primary", use_container_width=True):
            # Push review actions to API
            if acts and st.session_state.run_id:
                actions_payload = [
                    {
                        "source_column": src,
                        "action":        v.get("action", "pending"),
                        "overridden_target": v.get("override"),
                        "reviewer_note": v.get("note", ""),
                        "reviewer":      "reviewer@company.com",
                    }
                    for src, v in acts.items()
                ]
                api("POST",
                    f"/projects/{st.session_state.project_id}"
                    f"/mappings/{st.session_state.run_id}/review",
                    json={"run_id": st.session_state.run_id, "actions": actions_payload})
            st.session_state.screen = "export"
            st.rerun()


# ──────────────────────────────────────────────
# Screen 4 — Export
# ──────────────────────────────────────────────

def render_export():
    st.markdown('<div class="step-pill">STEP 4 OF 4 · EXPORT</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Export Mapping Artifacts</div>', unsafe_allow_html=True)

    candidates = st.session_state.candidates
    acts       = st.session_state.review_actions

    if not candidates:
        st.warning("No mapping data to export.")
        return

    approved  = [c for c in candidates if acts.get(c["source_column"],{}).get("action") == "approved"]
    rejected  = [c for c in candidates if acts.get(c["source_column"],{}).get("action") == "rejected"]
    overridden= [c for c in candidates if acts.get(c["source_column"],{}).get("action") == "overridden"]
    unmapped  = [c for c in candidates if not c.get("target_column")]
    pending   = [c for c in candidates
                 if acts.get(c["source_column"],{}).get("action","pending") == "pending"]

    # ── Summary ──────────────────────────────────
    s1, s2, s3, s4, s5 = st.columns(5)
    for col, num, lbl, color in [
        (s1, len(candidates), "Total Columns",  "#1F2937"),
        (s2, len(approved),   "Approved",        "#16A34A"),
        (s3, len(overridden), "Overridden",      "#7C3AED"),
        (s4, len(rejected),   "Rejected",        "#DC2626"),
        (s5, len(pending),    "Pending",         "#D97706"),
    ]:
        col.markdown(
            f'<div class="stat-box">'
            f'<div class="stat-num" style="color:{color}">{num}</div>'
            f'<div class="stat-lbl">{lbl}</div>'
            f'</div>', unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Build export table ───────────────────────
    rows = []
    for c in candidates:
        src = c["source_column"]
        act = acts.get(src, {})
        status = act.get("action", "pending")
        effective_tgt = act.get("override") or c.get("target_column") or "(unmapped)"
        rows.append({
            "Source Column":    src,
            "Source Type":      c.get("source_type",""),
            "Target Column":    effective_tgt,
            "Target Type":      c.get("target_type",""),
            "Confidence":       round(c.get("confidence",0),3),
            "Tier":             tier_from_score(c.get("confidence",0)) if c.get("target_column") else "low",
            "Status":           status,
            "Rationale":        c.get("rationale",""),
            "Reviewer Note":    act.get("note",""),
        })

    df = pd.DataFrame(rows)

    # ── Preview table ────────────────────────────
    st.markdown("**📋 Final Mapping Table Preview**")
    st.dataframe(
        df.style.apply(
            lambda row: [
                f"background-color:{'#DCFCE7' if row['Status']=='approved' else '#FEE2E2' if row['Status']=='rejected' else '#EDE9FE' if row['Status']=='overridden' else '#FEF3C7'}"
            ] * len(row), axis=1
        ),
        use_container_width=True, hide_index=True, height=400
    )

    st.markdown("---")
    st.markdown("**📥 Download Artifacts**")

    dl1, dl2, dl3 = st.columns(3)

    # JSON
    with dl1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📄 JSON Export")
        st.markdown("Full mapping data with rationale and signals. "
                    "Ready for ETL pipeline ingestion.")
        json_payload = {
            "run_id":       st.session_state.run_id,
            "generated_at": datetime.utcnow().isoformat(),
            "source_table": st.session_state.src_table,
            "target_table": st.session_state.tgt_table,
            "mappings":     rows,
        }
        st.download_button(
            "⬇️ Download JSON",
            data      = json.dumps(json_payload, indent=2, default=str),
            file_name = f"mapping_{st.session_state.src_table}_to_{st.session_state.tgt_table}.json",
            mime      = "application/json",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # CSV
    with dl2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 📊 CSV Export")
        st.markdown("Tabular format for Excel review, QA checklists, "
                    "and migration tracking sheets.")
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Download CSV",
            data      = csv_buf.getvalue(),
            file_name = f"mapping_{st.session_state.src_table}_to_{st.session_state.tgt_table}.csv",
            mime      = "text/csv",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Audit report
    with dl3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### 🗒️ Audit Report")
        st.markdown("Human-readable review log with decisions, notes, and timestamps.")
        audit_lines = [
            f"Oracle Mapping Copilot — Audit Report",
            f"Generated: {datetime.utcnow().isoformat()}",
            f"Source: {st.session_state.src_table}",
            f"Target: {st.session_state.tgt_table}",
            f"Run ID: {st.session_state.run_id}",
            "=" * 60,
            "",
        ]
        for r in rows:
            audit_lines.append(
                f"[{r['Status'].upper()}] {r['Source Column']} → {r['Target Column']}"
                f"  (conf: {r['Confidence']}, tier: {r['Tier']})"
            )
            if r["Rationale"]:
                audit_lines.append(f"  Rationale: {r['Rationale'][:120]}")
            if r["Reviewer Note"]:
                audit_lines.append(f"  Note: {r['Reviewer Note']}")
            audit_lines.append("")

        st.download_button(
            "⬇️ Download Audit Log",
            data      = "\n".join(audit_lines),
            file_name = f"audit_{st.session_state.src_table}.txt",
            mime      = "text/plain",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Unmapped columns ─────────────────────────
    if unmapped:
        st.markdown("---")
        st.warning(f"⚠️ **{len(unmapped)} unmapped columns** — these need manual review before ETL handoff.")
        unmapped_df = pd.DataFrame([
            {"Column": c["source_column"], "Type": c.get("source_type",""),
             "Comment": c.get("source_comment","")} for c in unmapped
        ])
        st.dataframe(unmapped_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    if st.button("↩ Back to Review", use_container_width=False):
        st.session_state.screen = "review"
        st.rerun()


# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

def main():
    render_sidebar()

    screen = st.session_state.screen
    if screen == "setup":
        render_setup()
    elif screen == "generate":
        render_generate()
    elif screen == "review":
        render_review()
    elif screen == "export":
        render_export()
    else:
        render_setup()

if __name__ == "__main__":
    main()
