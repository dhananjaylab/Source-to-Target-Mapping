"""
Gemini LLM Service for Oracle Mapping Copilot.
Uses google-genai (v1) SDK — the current supported package.
"""

from __future__ import annotations
import os, re, json, logging
from typing import Any, Dict, List, Optional, Set

from google import genai
from google.genai import types

from models import MappingCandidate, SignalBreakdown, MappingStatus, ConfidenceTier
from mapping_engine import (
    build_profiles_parallel, classify_tier,
    name_similarity, pre_signal_summary,
)

logger = logging.getLogger(__name__)

# ── Client ────────────────────────────────────────────────────────────────────
_CLIENT: Optional[genai.Client] = None

def get_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment / .env file.")
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT

MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Prompt constants ──────────────────────────────────────────────────────────
_SCORING_RUBRIC = """
CONFIDENCE SCORING RUBRIC (apply strictly — do not inflate):
  0.95 – 1.00 : Exact / near-exact name match + same type family + sample pattern matches
  0.80 – 0.94 : Clear abbreviation / semantic match + compatible type
  0.60 – 0.79 : Probable match via semantics or description + compatible sample pattern
  0.40 – 0.59 : Possible match — some signals align but mapping is ambiguous
  0.00 – 0.39 : No confident match → set target_column to null
""".strip()

_RULES = """
HARD RULES:
  1. Only use column names from the VALID TARGET COLUMNS list — never invent names.
  2. ETL infrastructure columns (etl_batch_id, load_timestamp) always map to null.
  3. Surrogate / synthetic key columns (customer_key, order_key, product_key) map to null.
  4. Never assign the same target column to two source columns (de-duplicate).
  5. Every source column must appear exactly once in the output array.
  6. Return raw JSON only — no markdown fences, no commentary, no extra keys.
""".strip()

_OUTPUT_SHAPE = """
OUTPUT FORMAT — JSON array, one object per source column:
[
  {
    "source_column": "src_col_name",
    "target_column": "tgt_col_name_or_null",
    "confidence": 0.92,
    "rationale": "2-3 sentence plain-English explanation referencing which signals matched.",
    "signals": {
      "name_similarity":    "description of name-match evidence",
      "type_compatibility": "description of type match or mismatch",
      "pattern_match":      "description of inferred pattern alignment",
      "semantic":           "description of conceptual / business meaning match"
    }
  }
]
""".strip()


# ── Prompt builder ────────────────────────────────────────────────────────────
def build_prompt(src_table, src_columns, src_profiles, tgt_table, tgt_columns) -> str:
    src_lines = []
    for col, prof in zip(src_columns, src_profiles):
        hint = pre_signal_summary(col, tgt_columns)
        src_lines.append(
            f"  • {col['name']}"
            f" | type: {col.get('type','?')}"
            f" | comment: \"{col.get('comment','')}\""
            f" | pattern: {prof.inferred_pattern}"
            f" | samples: {prof.masked_samples}"
            f" | pre-signal: {hint}"
        )
    tgt_lines = [
        f"  • {c['name']} | type: {c.get('type','?')} | comment: \"{c.get('comment','')}\""
        for c in tgt_columns
    ]
    return f"""You are a senior Oracle data-warehouse engineer performing source-to-target schema mapping.
Map each SOURCE column to the best matching TARGET column using four signals.

═══ SOURCE TABLE: {src_table} ═══
{chr(10).join(src_lines)}

═══ TARGET TABLE: {tgt_table} ═══
VALID TARGET COLUMNS (use ONLY these exact names):
{chr(10).join(tgt_lines)}

═══ FOUR MAPPING SIGNALS ═══
1. Name Similarity  — abbreviations: cust→customer, dt→date, amt/ttl→amount/total,
   prc→price, qty→quantity, addr→address, ph→phone, num→number, bal→balance,
   reg→registration, ord→order, disc→discount, pct→percent, stat→status,
   fname→first_name, lname→last_name, src→source, cd→code, fl/flg→flag/is_,
   nm→name, actv→active, stk→stock, prod→product
2. Sample Patterns  — email, ISO date, phone, decimal→currency, int→id
3. Type Compat.     — INTEGER≈INTEGER, VARCHAR≈VARCHAR2, NUMBER≈NUMBER/DECIMAL, DATE≈DATE
4. Semantic Meaning — conceptual business meaning from descriptions and comments

{_SCORING_RUBRIC}

{_RULES}

{_OUTPUT_SHAPE}
"""


# ── JSON extractor ────────────────────────────────────────────────────────────
def _extract_json(text: str) -> List[dict]:
    clean = re.sub(r"```(?:json)?\s*", "", text).strip()
    clean = re.sub(r"```\s*$", "", clean).strip()
    start = clean.find("[")
    end   = clean.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array in LLM response. Got: {text[:300]}")
    return json.loads(clean[start: end + 1])


# ── Validator ─────────────────────────────────────────────────────────────────
def _validate(raw, src_columns, tgt_columns, threshold) -> List[MappingCandidate]:
    valid_set: Set[str]   = {c["name"] for c in tgt_columns}
    used:      Set[str]   = set()
    tgt_meta: Dict[str, dict] = {c["name"]: c for c in tgt_columns}
    raw_map: Dict[str, dict]  = {r.get("source_column",""): r for r in raw if r.get("source_column")}

    results = []
    for sc in src_columns:
        sname = sc["name"]
        r     = raw_map.get(sname, {})
        tgt   = r.get("target_column") or None
        conf  = float(r.get("confidence", 0.0))

        if tgt and tgt not in valid_set:
            logger.warning("Hallucinated target '%s' for '%s' → nulled", tgt, sname)
            tgt, conf = None, 0.0
        if tgt and tgt in used:
            logger.warning("Duplicate target '%s' for '%s' → nulled", tgt, sname)
            tgt, conf = None, 0.0
        if tgt and conf < threshold:
            tgt = None
        if tgt:
            used.add(tgt)

        conf = round(min(1.0, max(0.0, conf)), 3)
        tier = classify_tier(conf) if tgt else ConfidenceTier.LOW
        sigs = r.get("signals", {})

        results.append(MappingCandidate(
            source_column      = sname,
            source_type        = sc.get("type", ""),
            source_comment     = sc.get("comment", ""),
            target_column      = tgt,
            target_type        = tgt_meta[tgt]["type"]    if tgt else "",
            target_comment     = tgt_meta[tgt]["comment"] if tgt else "",
            confidence         = conf,
            confidence_tier    = tier,
            rationale          = r.get("rationale", "No rationale provided."),
            signals            = SignalBreakdown(
                name_similarity    = sigs.get("name_similarity", ""),
                type_compatibility = sigs.get("type_compatibility", ""),
                pattern_match      = sigs.get("pattern_match", ""),
                semantic           = sigs.get("semantic", ""),
            ),
            status = MappingStatus.PENDING,
        ))

    results.sort(key=lambda c: (c.target_column is None, -c.confidence))
    return results


# ── Main entry ────────────────────────────────────────────────────────────────
async def generate_mappings(
    src_table, src_columns, tgt_table, tgt_columns,
    threshold=0.40, ai_model=MODEL_ID,
) -> List[MappingCandidate]:
    # Stage 1 — parallel profiling
    logger.info("Profiling %d source columns …", len(src_columns))
    src_profiles = build_profiles_parallel(src_columns)

    # Stage 2 — build prompt & call Gemini
    prompt = build_prompt(src_table, src_columns, src_profiles, tgt_table, tgt_columns)
    logger.info("Calling Gemini (%s) with %d-char prompt …", ai_model, len(prompt))

    client   = get_client()
    response = client.models.generate_content(
        model=ai_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            max_output_tokens=8192,
        ),
    )
    raw_text = response.text
    logger.info("Gemini response: %d chars", len(raw_text))

    # Stage 3 — extract + validate
    raw_list   = _extract_json(raw_text)
    candidates = _validate(raw_list, src_columns, tgt_columns, threshold)

    mapped = sum(1 for c in candidates if c.target_column)
    avg_c  = sum(c.confidence for c in candidates) / len(candidates) if candidates else 0
    logger.info("Done: %d/%d mapped, avg_conf=%.3f", mapped, len(candidates), avg_c)
    return candidates
