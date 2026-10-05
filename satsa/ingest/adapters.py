import json
import math
from pathlib import Path
 
import pandas as pd
 
from satsa.store.schema import Alert, Case, CaseEvent, Entity, Asset
from satsa.ingest.robust_ingest import read_csv_robust, prepare_records
 
 
def _write_parquet(objects: list, model_class, out_path: Path):
    """Validate dict objects against a Pydantic schema and append to Parquet (used by the JSON path)."""
    if not objects:
        return
    clean_objects = []
    for obj in objects:
        clean_objects.append({k: v for k, v in obj.items()
                              if v is not None and not (isinstance(v, float) and math.isnan(v))})
    validated = [model_class(**obj) for obj in clean_objects]
    df = pd.DataFrame([obj.model_dump() for obj in validated])
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if out_path.exists():
        df = pd.concat([pd.read_parquet(out_path), df], ignore_index=True)
    df.to_parquet(out_path, engine="pyarrow", index=False)
 
 
def _upsert_parquet(records: list, out_path: Path, entity_id: str):
    """Replace this entity's rows and keep every other entity's rows.
    Re-uploading the same file therefore never double-counts. Written atomically."""
    if not records:
        return
    df = pd.DataFrame(records)
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    if out_path.exists():
        old = pd.read_parquet(out_path)
        if "entity_id" in old.columns:
            old = old[old["entity_id"] != entity_id]
        df = pd.concat([old, df], ignore_index=True)
    tmp = out_path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, engine="pyarrow", index=False)
    tmp.replace(out_path)
 
 
def ingest_json(file_path: str, output_dir: str):
    path = Path(file_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "r") as f:
        data = json.load(f)
    if "entities" in data:
        _write_parquet(data["entities"], Entity, out_dir / "entities.parquet")
    if "assets" in data:
        _write_parquet(data["assets"], Asset, out_dir / "assets.parquet")
    if "alerts" in data:
        _write_parquet(data["alerts"], Alert, out_dir / "alerts.parquet")
    if "cases" in data:
        _write_parquet(data["cases"], Case, out_dir / "cases.parquet")
    if "events" in data:
        _write_parquet(data["events"], CaseEvent, out_dir / "events.parquet")
    print(f"Successfully ingested JSON data from {file_path}")
 
 
def _integrity(prepared: dict) -> dict:
    """Cross-file reconciliation counts, shown in the report (also useful evidence for negative space)."""
    out = {}
    if "alerts" in prepared and "cases" in prepared:
        aids = {r["alert_id"] for r in prepared["alerts"][0]}
        out["cases_referencing_unknown_alert"] = sum(
            1 for c in prepared["cases"][0] if any(a not in aids for a in c.get("alert_ids", [])))
        linked = {a for c in prepared["cases"][0] for a in c.get("alert_ids", [])}
        out["alerts_without_case"] = sum(1 for a in aids if a not in linked)
    if "cases" in prepared and "events" in prepared:
        cids = {c["case_id"] for c in prepared["cases"][0]}
        out["events_referencing_unknown_case"] = sum(
            1 for e in prepared["events"][0] if e["case_id"] not in cids)
        with_ev = {e["case_id"] for e in prepared["events"][0]}
        out["cases_without_events"] = sum(1 for c in cids if c not in with_ev)
    return out
 
 
def ingest_csv_bundle(entity_id: str, alerts_csv: str = None, cases_csv: str = None,
                      events_csv: str = None, output_dir: str = None):
    out_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent.parent / "data" / "real"
    out_dir.mkdir(parents=True, exist_ok=True)
 
    spec = [("alerts", alerts_csv, Alert, "alert_id"),
            ("cases", cases_csv, Case, "case_id"),
            ("events", events_csv, CaseEvent, None)]
 
    # Phase 1: read and validate everything. Nothing is written if any file is unusable.
    prepared, reports = {}, {}
    for name, path, model, id_field in spec:
        if path and Path(path).exists():
            try:
                prepared[name] = prepare_records(read_csv_robust(path), model,
                                                 entity_id=entity_id, id_field=id_field)
            except ValueError as e:
                raise ValueError(f"{name}.csv: {e}") from e
            reports[name] = prepared[name][1]
 
    # Phase 2: write all files (per-entity replace, atomic).
    for name, (records, _) in prepared.items():
        _upsert_parquet(records, out_dir / f"{name}.parquet", entity_id)
        print(f"Ingested {name} for {entity_id}: {len(records)} rows")
 
    reports["integrity"] = _integrity(prepared)
    return reports
