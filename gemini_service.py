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
    type_compatible,
)
from pydantic import BaseModel

# Structured output Pydantic schemas for Gemini
class GeminiSignalBreakdown(BaseModel):
    name_similarity:    str
    type_compatibility: str
    pattern_match:      str
    semantic:           str

class GeminiMappingCandidate(BaseModel):
    source_column:      str
    target_column:      Optional[str]
    confidence:         float
    rationale:          str
    signals:            GeminiSignalBreakdown

class GeminiMappingResponse(BaseModel):
    candidates:         List[GeminiMappingCandidate]

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
        comment = col.get("comment", "")
        wrapped_comment = f"<comment>{comment}</comment>" if comment else '""'
        wrapped_samples = f"<samples>{prof.masked_samples}</samples>"
        src_lines.append(
            f"  • {col['name']}"
            f" | type: {col.get('type','?')}"
            f" | comment: {wrapped_comment}"
            f" | pattern: {prof.inferred_pattern}"
            f" | samples: {wrapped_samples}"
            f" | pre-signal: {hint}"
        )
    tgt_lines = []
    for c in tgt_columns:
        c_comment = c.get("comment", "")
        wrapped_c_comment = f"<comment>{c_comment}</comment>" if c_comment else '""'
        tgt_lines.append(
            f"  • {c['name']} | type: {c.get('type','?')} | comment: {wrapped_c_comment}"
        )
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

    resolved_candidates: List[MappingCandidate] = []
    unresolved_src_cols = []
    unresolved_src_profiles = []

    tgt_meta = {c["name"]: c for c in tgt_columns}

    # Deterministic bypass for exact matches
    for col, prof in zip(src_columns, src_profiles):
        src_name = col["name"]
        src_type = col.get("type", "")
        
        exact_match_tgt = None
        for tc in tgt_columns:
            if name_similarity(src_name, tc["name"]) == 1.0 and type_compatible(src_type, tc.get("type", "")) == 1.0:
                exact_match_tgt = tc["name"]
                break
                
        if exact_match_tgt:
            logger.info("Deterministic bypass: exact match found for '%s' -> '%s'", src_name, exact_match_tgt)
            resolved_candidates.append(MappingCandidate(
                source_column      = src_name,
                source_type        = src_type,
                source_comment     = col.get("comment", ""),
                target_column      = exact_match_tgt,
                target_type        = tgt_meta[exact_match_tgt]["type"],
                target_comment     = tgt_meta[exact_match_tgt].get("comment", ""),
                confidence         = 1.0,
                confidence_tier    = ConfidenceTier.EXACT,
                rationale          = "Deterministic bypass: exact match on name and type family.",
                signals            = SignalBreakdown(
                    name_similarity    = "Exact name match (1.00)",
                    type_compatibility = "Compatible type (1.00)",
                    pattern_match      = "Matches",
                    semantic           = "Identical concept",
                ),
                status = MappingStatus.PENDING,
            ))
        else:
            unresolved_src_cols.append(col)
            unresolved_src_profiles.append(prof)

    if not unresolved_src_cols:
        logger.info("All columns resolved deterministically. Bypassing LLM.")
        resolved_candidates.sort(key=lambda c: (c.target_column is None, -c.confidence))
        return resolved_candidates

    # Stage 2 — build prompt & call Gemini
    prompt = build_prompt(src_table, unresolved_src_cols, unresolved_src_profiles, tgt_table, tgt_columns)
    logger.info("Calling Gemini (%s) with %d-char prompt for %d unresolved columns …", ai_model, len(prompt), len(unresolved_src_cols))

    client = get_client()
    raw_list = []
    
    try:
        response = client.models.generate_content(
            model=ai_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.95,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=GeminiMappingResponse,
            ),
        )
        raw_text = response.text
        logger.info("Gemini response: %d chars", len(raw_text))
        data = json.loads(raw_text)
        raw_list = data.get("candidates", [])
    except Exception as exc:
        logger.warning("Failed structured Gemini call: %s. Retrying...", exc)
        try:
            response = client.models.generate_content(
                model=ai_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                    response_schema=GeminiMappingResponse,
                ),
            )
            raw_text = response.text
            data = json.loads(raw_text)
            raw_list = data.get("candidates", [])
        except Exception as retry_exc:
            logger.error("Structured output retry failed: %s. Falling back to parsing regex.", retry_exc)
            try:
                response = client.models.generate_content(
                    model=ai_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                    ),
                )
                raw_list = _extract_json(response.text)
            except Exception as final_exc:
                logger.exception("All attempts to parse mapping output failed: %s", final_exc)
                raise RuntimeError(f"All LLM mapping attempts failed: {final_exc}")

    # Stage 3 — extract + validate
    llm_candidates = _validate(raw_list, unresolved_src_cols, tgt_columns, threshold)
    all_candidates = resolved_candidates + llm_candidates
    all_candidates.sort(key=lambda c: (c.target_column is None, -c.confidence))

    mapped = sum(1 for c in all_candidates if c.target_column)
    avg_c  = sum(c.confidence for c in all_candidates) / len(all_candidates) if all_candidates else 0
    logger.info("Done: %d/%d mapped, avg_conf=%.3f", mapped, len(all_candidates), avg_c)
    return all_candidates
