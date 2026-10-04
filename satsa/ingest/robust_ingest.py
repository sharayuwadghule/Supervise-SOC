"""
robust_ingest.py: drop-in helper for SAT-SA CSV ingestion.

Turns messy real-world CSVs into validated records for your existing pydantic
models, and returns a report instead of crashing. Adapt names to your code.
"""
from __future__ import annotations
import ast, json
import pandas as pd
from pydantic import ValidationError

# ---- 1. header aliases (extend per CSE; could be loaded from config/mappings/*.yaml) ----
ALIASES = {
    "alert_id": ["alertid", "id", "alert", "alert_number"],
    "created_ts": ["timestamp", "created_at", "created", "time", "ts", "detected_at", "alert_time", "event_time"],
    "severity": ["sev", "priority", "risk", "risk_level", "alert_severity"],
    "rule_id": ["rule", "rule_name", "signature", "signature_id", "detection_rule", "rule_code"],
    "category": ["type", "alert_type", "alert_category", "classification", "tactic"],
    "asset_ids": ["asset_id", "asset", "assets", "hostname", "host", "device", "affected_assets"],
    "status": ["state", "alert_status", "case_status"],
    "disposition": ["verdict", "resolution", "outcome", "closure_code", "closure_reason"],
    "analyst_id": ["analyst", "assignee", "assigned_to", "handled_by"],
    "case_id": ["caseid", "case_number", "ticket_id", "incident_id"],
    "alert_ids": ["alerts", "linked_alerts", "alert_id", "related_alerts"],
    "opened_ts": ["opened", "opened_at", "open_time", "start_time", "case_opened"],
    "closed_ts": ["closed", "closed_at", "close_time", "end_time", "resolved_at", "case_closed"],
    "owner": ["assigned_to", "analyst", "case_owner", "assignee"],
    "root_cause": ["cause", "rootcause"],
    "remediation": ["action_taken", "remediation_action", "resolution_notes"],
    "ts": ["timestamp", "time", "event_time", "datetime", "created_at"],
    "event_type": ["type", "action", "activity", "event"],
    "actor": ["user", "performed_by", "analyst", "by"],
    "message": ["description", "details", "comment", "note", "notes", "text"],
}
# Text severity -> integer. State this scale in your docs; invert here if your scale is reversed.
SEVERITY_SCALE = {"info": 1, "informational": 1, "low": 1, "medium": 2, "moderate": 2,
                  "high": 3, "critical": 4, "severe": 4}

def norm(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")

def read_csv_robust(src) -> pd.DataFrame:
    """Handle odd encodings and delimiters. Everything is read as text; types are coerced later."""
    last = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            if hasattr(src, "seek"):
                src.seek(0)
            return pd.read_csv(src, sep=None, engine="python", dtype=str,
                               encoding=enc, keep_default_na=True, skip_blank_lines=True)
        except Exception as e:  # noqa: BLE001
            last = e
    raise ValueError(f"Could not read file as CSV: {last}")

# ---- 2. column mapping ----
def map_columns(df: pd.DataFrame, model) -> tuple[pd.DataFrame, dict, list]:
    df = df.copy()
    df.columns = [norm(c) for c in df.columns]
    fields = list(model.model_fields)
    mapping, used = {}, set()
    for f in fields:                       # exact matches first
        if f in df.columns:
            mapping[f] = f; used.add(f)
    for f in fields:                       # then aliases, never reusing a column
        if f in mapping:
            continue
        for a in ALIASES.get(f, []):
            if a in df.columns and a not in used and a not in fields:
                mapping[f] = a; used.add(a); break
    out = pd.DataFrame({f: df[src] for f, src in mapping.items()})
    unmapped = [c for c in df.columns if c not in used]
    return out, mapping, unmapped

# ---- 3. value coercion, driven by the model's field types ----
def parse_list(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    s = str(v).strip()
    if s.startswith("[") or s.startswith("("):
        try:
            return [str(x) for x in ast.literal_eval(s)]
        except Exception:  # noqa: BLE001
            try:
                return [str(x) for x in json.loads(s)]
            except Exception:  # noqa: BLE001
                pass
    for sep in (";", "|", ","):
        if sep in s:
            return [p.strip().strip("'\"") for p in s.strip("[]").split(sep) if p.strip()]
    return [s.strip("'\"[]")]

def to_severity(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().lower()
    if s in SEVERITY_SCALE:
        return SEVERITY_SCALE[s]
    try:
        return int(float(s))
    except ValueError:
        return None

def parse_dt(s: pd.Series, dayfirst: bool) -> pd.Series:
    """ISO timestamps are parsed as ISO (never swapped); other formats use dayfirst."""
    t = pd.to_datetime(s, format="ISO8601", errors="coerce", utc=True)
    bad = t.isna() & s.notna()
    if bad.any():
        t[bad] = pd.to_datetime(s[bad], format="mixed", dayfirst=dayfirst, errors="coerce", utc=True)
    return t

def coerce(df: pd.DataFrame, model, dayfirst: bool = True) -> pd.DataFrame:
    for name, f in model.model_fields.items():
        if name not in df.columns:
            continue
        ann = str(f.annotation).lower()
        if name == "severity":
            df[name] = df[name].map(to_severity)
        elif "list" in ann:
            df[name] = df[name].map(parse_list)
        elif "datetime" in ann:
            t = parse_dt(df[name], dayfirst)
            df[name] = t.dt.tz_localize(None)          # store UTC, naive
        elif "int" in ann:
            df[name] = pd.to_numeric(df[name], errors="coerce")
        elif "float" in ann:
            df[name] = pd.to_numeric(df[name], errors="coerce")
    return df

# ---- 4. row-level validation, report, quality score ----
def prepare_records(df_raw: pd.DataFrame, model, entity_id: str, id_field: str | None = None,
                    max_reject_rate: float = 0.25, dayfirst: bool = True):
    """Returns (valid_records, report). Never raises on bad data; raises ValueError only
    when the file cannot be used at all (required columns absent or too many rejects)."""
    rows_in = len(df_raw)
    df, mapping, unmapped = map_columns(df_raw, model)
    required = [n for n, f in model.model_fields.items() if f.is_required() and n != "entity_id"]
    missing_req = [n for n in required if n not in df.columns]
    optional_missing = [n for n, f in model.model_fields.items()
                        if not f.is_required() and n not in df.columns]
    report = dict(model=model.__name__, rows_in=rows_in, column_mapping=mapping,
                  unmapped_source_columns=unmapped, missing_required=missing_req,
                  not_assessable_fields=optional_missing, rows_ok=0, rows_rejected=0,
                  duplicates_dropped=0, rejects=[], completeness={}, quality_score=0.0)
    if missing_req:
        raise ValueError(
            f"{model.__name__} file is missing required column(s): {missing_req}. "
            f"Columns found: {list(df_raw.columns)}. Rename them or add an alias in ALIASES.")
    if id_field and id_field in df.columns:
        before = len(df); df = df.drop_duplicates(subset=[id_field], keep="first").reset_index(drop=True)
        report["duplicates_dropped"] = before - len(df)
    raw = df.copy()                       # pre-coercion values, used to explain rejects
    df = coerce(df, model, dayfirst)      # dayfirst=True reads 01/04/2026 as 1 April; ISO dates unaffected
    df["entity_id"] = entity_id
    good, rejects = [], []
    for i, rec in enumerate(df.to_dict(orient="records")):
        clean = {k: v for k, v in rec.items()
                 if not (v is None or (not isinstance(v, (list, tuple)) and pd.isna(v)))}
        try:
            good.append(model(**clean).model_dump())
        except ValidationError as e:
            if len(rejects) < 1000:
                err = e.errors()[0]
                fld = ".".join(map(str, err["loc"]))
                rv = raw.at[i, fld] if fld in raw.columns else None
                problem = (f"unparseable value {rv!r}" if rv is not None and not (not isinstance(rv, (list, tuple)) and pd.isna(rv))
                           else err["msg"])
                rejects.append({"row": i + 2, "field": fld, "problem": problem, "id": clean.get(id_field, "")})
            report["rows_rejected"] += 1
    report["rows_ok"] = len(good); report["rejects"] = rejects
    report["completeness"] = {c: round(float(df[c].notna().mean()), 3) for c in df.columns if c != "entity_id"}
    ok_rate = len(good) / max(rows_in, 1)
    comp = sum(report["completeness"].values()) / max(len(report["completeness"]), 1)
    report["quality_score"] = round(100 * (0.6 * ok_rate + 0.4 * comp), 1)
    if rows_in and report["rows_rejected"] / rows_in > max_reject_rate:
        raise ValueError(f"{report['rows_rejected']} of {rows_in} {model.__name__} rows failed validation "
                         f"(first problems: {rejects[:3]}). Check column formats.")
    return good, report
