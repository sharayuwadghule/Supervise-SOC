from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# SAT-SA Canonical Data Model (Phase 1)
# ---------------------------------------------------------

class Entity(BaseModel):
    entity_id: str
    sector: str
    size_tier: str
    region: str
    soc_model: str  # in-house / MSSP

class Asset(BaseModel):
    asset_id: str
    entity_id: str
    type: str
    criticality: str
    environment_zone: str = Field(alias="environment/zone")
    monitored_flag: bool
    onboarded_date: Optional[datetime] = None
    decommissioned_date: Optional[datetime] = None

class Alert(BaseModel):
    alert_id: str
    entity_id: str
    asset_id: Optional[str] = None
    rule_id: str
    category: str
    severity: int  # e.g., 1 to 5
    created_ts: datetime
    ack_ts: Optional[datetime] = None
    closed_ts: Optional[datetime] = None
    status: str
    disposition: Optional[str] = None
    closure_reason: Optional[str] = None
    analyst_id: Optional[str] = None
    shift: Optional[str] = None

class Case(BaseModel):
    case_id: str
    alert_ids: List[str]
    opened_ts: datetime
    closed_ts: Optional[datetime] = None
    severity: int
    owner: Optional[str] = None
    root_cause: Optional[str] = None
    remediation: Optional[str] = None
    reopened_flag: bool = False

class CaseEvent(BaseModel):
    case_id: str
    ts: datetime
    event_type: str  # assign, enrich, pivot, note, evidence, handoff, status
    actor: str

class Escalation(BaseModel):
    case_id: Optional[str] = None
    alert_id: Optional[str] = None
    ts: datetime
    from_tier: str
    to_tier: str
    recipient: str
    outcome: str

class Note(BaseModel):
    case_id: str
    ts: datetime
    text: str

class KPIReport(BaseModel):
    entity_id: str
    period: str  # e.g., '2023-10'
    reported_mttr_mins: Optional[float] = None
    reported_mtta_mins: Optional[float] = None
    reported_sla_percent: Optional[float] = None
    closure_rate: Optional[float] = None

class SubmissionManifest(BaseModel):
    entity_id: str
    period: str
    file_hashes: dict
    row_counts: dict
    received_ts: datetime
