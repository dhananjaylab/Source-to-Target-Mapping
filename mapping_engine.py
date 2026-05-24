"""
Mapping Engine — pre-LLM signal computation.

Provides:
  - Pattern inference via pre-compiled regexes (email, uuid, date, phone, currency, boolean, integer_id, url)
  - Name-similarity scoring via abbreviation dictionary + token matching
  - Type-compatibility matrix
  - Column profile builder (parallel via ThreadPoolExecutor)
  - Confidence-tier classifier
"""

from __future__ import annotations
import re
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from models import ColumnProfile, ConfidenceTier


# ──────────────────────────────────────────────
# Pattern classifiers — compiled once at import
# ──────────────────────────────────────────────

_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("email",       re.compile(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$")),
    ("uuid",        re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)),
    ("date_iso",    re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$")),
    ("date_slash",  re.compile(r"^\d{2}/\d{2}/\d{4}$")),
    ("phone",       re.compile(r"^[+]?[\d\s\-().]{7,20}$")),
    ("url",         re.compile(r"^https?://")),
    ("boolean_flag",re.compile(r"^(Y|N|YES|NO|TRUE|FALSE|0|1)$", re.I)),
    ("currency",    re.compile(r"^-?\d{1,15}\.\d{2}$")),
]

_THRESHOLD = 0.70   # ≥70 % of non-null samples must match for label assignment


def infer_pattern(samples: List[Any]) -> str:
    """Return the dominant pattern label for a list of sample values."""
    str_samples = [str(s).strip() for s in samples if s is not None and str(s).strip()]
    if not str_samples:
        return "unknown"

    for label, pat in _PATTERNS:
        hits = sum(1 for s in str_samples if pat.match(s))
        if hits / len(str_samples) >= _THRESHOLD:
            return label

    # Numeric heuristics when no regex fires
    numeric = []
    for s in str_samples:
        try:
            numeric.append(float(s))
        except ValueError:
            pass

    if len(numeric) == len(str_samples):
        if all(float(s) == int(float(s)) for s in str_samples):
            return "integer_id" if all(float(s) > 0 for s in str_samples) else "integer"
        return "decimal"

    avg_len = sum(len(s) for s in str_samples) / len(str_samples)
    return "short_code" if avg_len <= 5 else "long_text"


# ──────────────────────────────────────────────
# Abbreviation dictionary
# ──────────────────────────────────────────────

ABBR: Dict[str, str] = {
    # generic
    "id": "identifier", "num": "number", "no": "number",
    "nm": "name",        "cd": "code",   "desc": "description",
    "dt": "date",        "ts": "timestamp", "tm": "time",
    "amt": "amount",     "ttl": "total", "tot": "total",
    "prc": "price",      "qty": "quantity", "cnt": "count",
    "bal": "balance",    "acct": "account",
    "addr": "address",   "str": "street",
    # entities
    "cust": "customer",  "ord": "order",  "prod": "product",
    "inv": "invoice",    "emp": "employee", "dept": "department",
    "cat": "category",   "src": "source", "tgt": "target",
    # flags / status
    "flg": "flag",       "fl": "flag",  "actv": "active", "inactv": "inactive",
    "pct": "percent",    "disc": "discount",
    # dates / audit
    "reg": "registration", "creat": "created", "upd": "updated",
    # contact
    "ph": "phone",       "tel": "telephone",
    # name parts — expand to individual tokens so they match split targets
    "fname": "first",    "lname": "last",   "mname": "middle",
    # misc
    "stat": "status",    "stk": "stock",   "sku": "sku",
    "ship": "shipping",  "bill": "billing",
    "lst": "list",       "prim": "primary", "sec": "secondary",
    "ref": "reference",  "ext": "external",
    "unit": "unit",      "svc": "service",
    "ttl": "total",      "prc": "price",
    "lst": "list",
}


def _expand_token(tok: str) -> str:
    return ABBR.get(tok.lower(), tok.lower())


def _tokenize(name: str) -> List[str]:
    """Split snake_case, camelCase, and mixed identifiers into tokens."""
    # insert underscore before uppercase runs
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [t for t in re.split(r"[_\s]+", s.lower()) if t]


def name_similarity(src: str, tgt: str) -> float:
    """
    Return 0.0-1.0 similarity between two column names
    using expanded-token overlap.
    """
    src_tokens = set(_expand_token(t) for t in _tokenize(src))
    tgt_tokens = set(_expand_token(t) for t in _tokenize(tgt))
    if not src_tokens or not tgt_tokens:
        return 0.0
    # Jaccard on expanded tokens
    inter = len(src_tokens & tgt_tokens)
    union = len(src_tokens | tgt_tokens)
    return inter / union if union else 0.0


# ──────────────────────────────────────────────
# Type compatibility
# ──────────────────────────────────────────────

_TYPE_FAMILY: Dict[str, str] = {}

def _fam(types: List[str], family: str):
    for t in types:
        _TYPE_FAMILY[t] = family

_fam(["integer","int","bigint","smallint","integer_id"],       "numeric_int")
_fam(["float","double","real","decimal","number","numeric"],   "numeric_dec")
_fam(["varchar","varchar2","nvarchar","char","nchar","string","text","clob","long"], "text")
_fam(["date"], "date")
_fam(["timestamp","timestamp with time zone","timestamp(6)"], "timestamp")
_fam(["boolean","bool"], "boolean")
_fam(["blob","raw","long raw","binary"], "binary")


def _get_family(type_str: str) -> str:
    key = re.split(r"[(\s]", type_str.lower())[0]
    return _TYPE_FAMILY.get(key, "unknown")


def type_compatible(src_type: str, tgt_type: str) -> float:
    """Return 0.0, 0.5, or 1.0 based on type compatibility."""
    sf = _get_family(src_type)
    tf = _get_family(tgt_type)
    if sf == tf:
        return 1.0
    # numeric int ↔ numeric dec are close
    if {sf, tf} == {"numeric_int", "numeric_dec"}:
        return 0.75
    # date ↔ timestamp are reasonable
    if {sf, tf} == {"date", "timestamp"}:
        return 0.60
    # text ↔ char family
    if sf in ("text",) and tf in ("text",):
        return 1.0
    if sf == "unknown" or tf == "unknown":
        return 0.50
    return 0.0


# ──────────────────────────────────────────────
# PII masking
# ──────────────────────────────────────────────

_PII_PATTERN_LABELS = {"email", "phone", "uuid"}
_PII_NAME_HINTS     = {"ssn", "social", "passport", "national_id", "credit",
                        "card", "cvv", "pin", "password", "secret", "dob", "birth"}


def should_mask(col_name: str, pattern_label: str) -> bool:
    tokens = set(_tokenize(col_name))
    return (pattern_label in _PII_PATTERN_LABELS or
            bool(tokens & _PII_NAME_HINTS))


def mask_samples(samples: List[Any], col_name: str, pattern_label: str) -> List[str]:
    if should_mask(col_name, pattern_label):
        return ["[MASKED]"] * min(len(samples), 3)
    return [str(s) for s in samples[:5]]


# ──────────────────────────────────────────────
# Column profile builder
# ──────────────────────────────────────────────

def build_profile(col: dict) -> ColumnProfile:
    """Build an enriched profile for one column dict."""
    samples  = col.get("samples") or []
    pattern  = infer_pattern(samples)
    masked   = mask_samples(samples, col["name"], pattern)
    # semantic tags
    tags = []
    for tok in _tokenize(col["name"]):
        exp = _expand_token(tok)
        if exp != tok:
            tags.append(exp)
    if pattern not in ("unknown", "long_text"):
        tags.append(pattern)

    return ColumnProfile(
        column_name      = col["name"],
        data_type        = col.get("type", "unknown"),
        comment          = col.get("comment", ""),
        inferred_pattern = pattern,
        semantic_tags    = tags,
        masked_samples   = masked,
        null_pct         = 0.0,    # would come from real Oracle stats
        distinct_count   = None,
    )


def build_profiles_parallel(columns: List[dict]) -> List[ColumnProfile]:
    """Build profiles for all columns concurrently."""
    results: Dict[int, ColumnProfile] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(columns) or 1)) as ex:
        futures = {ex.submit(build_profile, c): i for i, c in enumerate(columns)}
        for fut in as_completed(futures):
            idx = futures[fut]
            results[idx] = fut.result()
    return [results[i] for i in range(len(columns))]


# ──────────────────────────────────────────────
# Confidence tier classifier
# ──────────────────────────────────────────────

def classify_tier(score: float) -> ConfidenceTier:
    if score >= 0.95: return ConfidenceTier.EXACT
    if score >= 0.80: return ConfidenceTier.CLEAR
    if score >= 0.60: return ConfidenceTier.PROBABLE
    if score >= 0.40: return ConfidenceTier.POSSIBLE
    return ConfidenceTier.LOW


# ──────────────────────────────────────────────
# Pre-LLM name-match signal summary
# ──────────────────────────────────────────────

def pre_signal_summary(src_col: dict, tgt_candidates: List[dict]) -> str:
    """
    Compute the top name-similarity candidate for inclusion in the LLM prompt.
    Gives the model a hint without overriding its semantic reasoning.
    """
    best_score = 0.0
    best_name  = "none"
    for tc in tgt_candidates:
        s = name_similarity(src_col["name"], tc["name"])
        if s > best_score:
            best_score = s
            best_name  = tc["name"]
    if best_score > 0.5:
        return f"Top name-similarity candidate: {best_name} ({best_score:.2f})"
    return "No strong name-similarity candidate found"
