import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

# Try to import polars, but allow the script to be saved even if not installed yet
try:
    import polars as pl
except ImportError:
    pl = None

from satsa.store.schema import Entity, Asset, Alert, Case, Escalation, CaseEvent, Note

# ---------------------------------------------------------
# SAT-SA Synthetic Data Generator with Injectors (Phase 2)
# ---------------------------------------------------------

SECTORS = ["Power", "Banking", "Telecom", "Transport", "Health"]
TIERS = ["Tier 1", "Tier 2", "Tier 3"]
SOC_MODELS = ["In-House", "MSSP", "Hybrid"]

def generate_entities(n_entities: int = 25) -> List[Entity]:
    """Generate healthy baseline entities."""
    entities = []
    for _ in range(n_entities):
        e_id = f"ENT-{uuid.uuid4().hex[:6].upper()}"
        entities.append(Entity(
            entity_id=e_id,
            sector=random.choice(SECTORS),
            size_tier=random.choice(TIERS),
            region=f"Region-{random.randint(1, 5)}",
            soc_model=random.choice(SOC_MODELS)
        ))
    return entities

def generate_assets(entities: List[Entity], avg_assets_per_ent: int = 100) -> List[Asset]:
    """Generate assets for the entities."""
    assets = []
    asset_types = ["Server", "Workstation", "Router", "Firewall", "Database", "IoT"]
    for entity in entities:
        n_assets = int(random.gauss(avg_assets_per_ent, avg_assets_per_ent * 0.2))
        n_assets = max(10, n_assets)
        for _ in range(n_assets):
            a_id = f"AST-{uuid.uuid4().hex[:8].upper()}"
            assets.append(Asset(
                asset_id=a_id,
                entity_id=entity.entity_id,
                type=random.choice(asset_types),
                criticality=random.choice(["High", "Medium", "Low", "Critical"]),
                **{"environment/zone": random.choice(["DMZ", "Internal", "Cloud", "OT"])},
                monitored_flag=random.random() > 0.05,
                onboarded_date=datetime.now() - timedelta(days=random.randint(30, 1000))
            ))
    return assets

def generate_alerts(assets: List[Asset], days: int = 30) -> List[Alert]:
    """Generate a baseline of alerts."""
    alerts = []
    rules = [f"RULE-{i:03d}" for i in range(1, 51)]
    categories = ["Malware", "Phishing", "Lateral Movement", "Exfiltration", "Auth Failure"]
    analysts = [f"A-{i:02d}" for i in range(1, 15)]
    
    start_time = datetime.now() - timedelta(days=days)
    
    for asset in assets:
        noise_factor = random.random()
        num_alerts = int(noise_factor * 10 * (days/30)) 
        
        for _ in range(num_alerts):
            severity = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
            created_ts = start_time + timedelta(seconds=random.randint(0, int(days * 86400)))
            
            ack_delay_mins = random.uniform(1, 60) * (6 - severity)
            close_delay_mins = ack_delay_mins + random.uniform(10, 240) * (6 - severity)
            
            ack_ts = created_ts + timedelta(minutes=ack_delay_mins)
            closed_ts = ack_ts + timedelta(minutes=close_delay_mins)
            
            alerts.append(Alert(
                alert_id=f"ALT-{uuid.uuid4().hex[:10].upper()}",
                entity_id=asset.entity_id,
                asset_id=asset.asset_id,
                rule_id=random.choice(rules),
                category=random.choice(categories),
                severity=severity,
                created_ts=created_ts,
                ack_ts=ack_ts,
                closed_ts=closed_ts,
                status="Closed",
                disposition=random.choice(["True Positive", "False Positive", "Benign"]),
                closure_reason="Resolved",
                analyst_id=random.choice(analysts),
                shift=random.choice(["Day", "Night"])
            ))
            
    alerts.sort(key=lambda x: x.created_ts)
    return alerts

# --- Weakness Injectors ---

def inject_fast_closure(alerts: List[Alert], ground_truth: List[Dict[str, Any]], fraction: float = 0.05):
    """
    EG-01: Inject unusually fast closure for high-severity alerts.
    """
    high_sev_alerts = [a for a in alerts if a.severity >= 4]
    n_inject = int(len(high_sev_alerts) * fraction)
    
    targets = random.sample(high_sev_alerts, n_inject)
    for alert in targets:
        # Force closure within 5 to 30 seconds of creation
        alert.ack_ts = alert.created_ts + timedelta(seconds=random.randint(1, 5))
        alert.closed_ts = alert.ack_ts + timedelta(seconds=random.randint(1, 25))
        
        ground_truth.append({
            "finding_id": "EG-01",
            "entity_id": alert.entity_id,
            "scope": "alert",
            "target_id": alert.alert_id,
            "description": "High severity alert closed abnormally fast."
        })

def inject_silent_critical_assets(assets: List[Asset], alerts: List[Alert], ground_truth: List[Dict[str, Any]], n_assets: int = 5):
    """
    NS-01: Remove all alerts for a few critical assets to simulate broken forwarding.
    """
    critical_assets = [a for a in assets if a.criticality == "Critical"]
    if not critical_assets:
        return alerts
        
    targets = random.sample(critical_assets, min(n_assets, len(critical_assets)))
    target_ids = {a.asset_id for a in targets}
    
    # Filter out alerts for these assets
    clean_alerts = [a for a in alerts if a.asset_id not in target_ids]
    
    for target in targets:
        ground_truth.append({
            "finding_id": "NS-01",
            "entity_id": target.entity_id,
            "scope": "asset",
            "target_id": target.asset_id,
            "description": "Critical asset produced zero alerts (Negative Space)."
        })
        
    return clean_alerts

def inject_remaining_negative_space(alerts: List[Alert], assets: List[Asset], entities: List[Entity], ground_truth: List[Dict[str, Any]]):
    entity_alerts = {}
    for a in alerts:
        entity_alerts.setdefault(a.entity_id, []).append(a)
    
    target_entities = random.sample(entities, 4)
    ns02_entity = target_entities[0].entity_id
    ns04_entity = target_entities[1].entity_id
    ns05_entity = target_entities[2].entity_id
    ns06_entity = target_entities[3].entity_id
    
    alerts_to_remove = set()
    
    # NS-02: Missing alert category (Phishing)
    for a in entity_alerts.get(ns02_entity, []):
        if a.category == "Phishing":
            alerts_to_remove.add(a.alert_id)
    ground_truth.append({
        "finding_id": "NS-02",
        "entity_id": ns02_entity,
        "scope": "category",
        "target_id": "Phishing",
        "description": "Entity has 0 Phishing alerts compared to peers."
    })
    
    # NS-04: Unexpectedly low activity (drop 95% of alerts)
    ns04_alerts = entity_alerts.get(ns04_entity, [])
    to_drop = random.sample(ns04_alerts, int(len(ns04_alerts) * 0.95))
    for a in to_drop:
        alerts_to_remove.add(a.alert_id)
    ground_truth.append({
        "finding_id": "NS-04",
        "entity_id": ns04_entity,
        "scope": "volume",
        "target_id": ns04_entity,
        "description": "Entity has unusually low alert volume compared to its asset count."
    })
    
    # NS-05: Missing asset class (Database)
    for a in entity_alerts.get(ns05_entity, []):
        asset = next((x for x in assets if x.asset_id == a.asset_id), None)
        if asset and asset.type == "Database":
            alerts_to_remove.add(a.alert_id)
    ground_truth.append({
        "finding_id": "NS-05",
        "entity_id": ns05_entity,
        "scope": "asset_class",
        "target_id": "Database",
        "description": "Entity has Database assets but zero alerts for them."
    })
    
    # NS-06: Global outlier (drop 99% of alerts)
    ns06_alerts = entity_alerts.get(ns06_entity, [])
    to_drop_06 = random.sample(ns06_alerts, int(len(ns06_alerts) * 0.99))
    for a in to_drop_06:
        alerts_to_remove.add(a.alert_id)
    ground_truth.append({
        "finding_id": "NS-06",
        "entity_id": ns06_entity,
        "scope": "peer_volume",
        "target_id": ns06_entity,
        "description": "Entity alert volume is a global outlier compared to peers."
    })
    
    return [a for a in alerts if a.alert_id not in alerts_to_remove]

def generate_cases_and_escalations(alerts: List[Alert], ground_truth: List[Dict[str, Any]]):
    cases = []
    escalations = []
    
    # We will pick some high severity alerts for EG-03 and NS-03
    high_sev_alerts = [a for a in alerts if a.severity >= 4]
    
    # NS-03 targets: Critical alerts with no case
    ns03_targets = random.sample(high_sev_alerts, int(len(high_sev_alerts) * 0.05))
    ns03_ids = {a.alert_id for a in ns03_targets}
    
    # EG-03 targets: Critical alerts closed without escalation
    eg03_targets = random.sample([a for a in high_sev_alerts if a.alert_id not in ns03_ids], int(len(high_sev_alerts) * 0.05))
    eg03_ids = {a.alert_id for a in eg03_targets}
    
    for alert in alerts:
        if alert.alert_id in ns03_ids:
            ground_truth.append({
                "finding_id": "NS-03",
                "entity_id": alert.entity_id,
                "scope": "alert",
                "target_id": alert.alert_id,
                "description": "High severity alert with no associated case (Negative Space)."
            })
            continue # No case for this alert
            
        # Create a Case
        c_id = f"CAS-{uuid.uuid4().hex[:8].upper()}"
        cases.append(Case(
            case_id=c_id,
            entity_id=alert.entity_id,
            alert_ids=[alert.alert_id],
            opened_ts=alert.created_ts + timedelta(minutes=random.randint(1, 10)),
            closed_ts=alert.closed_ts,
            severity=alert.severity,
            owner=alert.analyst_id,
            root_cause="Investigated",
            remediation="Resolved",
            reopened_flag=False
        ))
        
        # Create Escalation if severity >= 4 and not EG-03
        if alert.severity >= 4:
            if alert.alert_id in eg03_ids:
                ground_truth.append({
                    "finding_id": "EG-03",
                    "entity_id": alert.entity_id,
                    "scope": "alert",
                    "target_id": alert.alert_id,
                    "description": "Critical alert closed without escalation."
                })
            else:
                escalations.append(Escalation(
                    case_id=c_id,
                    alert_id=alert.alert_id,
                    entity_id=alert.entity_id,
                    ts=alert.created_ts + timedelta(minutes=random.randint(5, 30)),
                    from_tier="Tier 1",
                    to_tier="Tier 2",
                    recipient="L2-Analyst",
                    outcome="Escalated for further review"
                ))
                
    return cases, escalations

def generate_events_and_notes(cases: List[Case], alerts: List[Alert], ground_truth: List[Dict[str, Any]]):
    events = []
    notes = []
    
    alert_map = {a.alert_id: a for a in alerts}
    
    analysts = list(set([c.owner for c in cases if c.owner]))
    eg04_analyst = random.choice(analysts) if analysts else None
    
    rules = list(set([alert_map[c.alert_ids[0]].rule_id for c in cases if c.alert_ids and c.alert_ids[0] in alert_map]))
    eg05_rule = random.choice(rules) if rules else None
    
    eg06_analyst = random.choice([a for a in analysts if a != eg04_analyst]) if len(analysts) > 1 else None
    eg06_cases = [c for c in cases if c.owner == eg06_analyst]
    bulk_close_time = datetime.now() - timedelta(days=2)
    
    eg06_injected = False
    if eg06_analyst and eg06_cases:
        for c in eg06_cases:
            if c.alert_ids and c.alert_ids[0] in alert_map:
                c.closed_ts = bulk_close_time + timedelta(seconds=random.randint(1, 60))
                if not eg06_injected:
                    ground_truth.append({
                        "finding_id": "EG-06",
                        "entity_id": alert_map[c.alert_ids[0]].entity_id,
                        "scope": "analyst",
                        "target_id": eg06_analyst,
                        "description": "Bulk closures by one analyst in a short window."
                    })
                    eg06_injected = True
            
    eg04_injected = False
    eg05_injected = False
    
    for case in cases:
        case_rule = alert_map[case.alert_ids[0]].rule_id if case.alert_ids and case.alert_ids[0] in alert_map else None
        
        # EG-05: Skip events if it's the target rule
        if case_rule == eg05_rule:
            if not eg05_injected:
                ground_truth.append({
                    "finding_id": "EG-05",
                    "entity_id": alert_map[case.alert_ids[0]].entity_id,
                    "scope": "rule",
                    "target_id": eg05_rule,
                    "description": "Rule fires regularly but has no analyst action events."
                })
                eg05_injected = True
        else:
            num_events = random.randint(1, 5)
            for i in range(num_events):
                events.append(CaseEvent(
                    case_id=case.case_id,
                    entity_id=case.entity_id,
                    ts=case.opened_ts + timedelta(minutes=random.randint(1, 60)),
                    event_type=random.choice(["enrich", "pivot", "evidence", "status"]),
                    actor=case.owner or "System"
                ))
                
        # EG-04: Template notes
        if case.owner == eg04_analyst:
            notes.append(Note(
                case_id=case.case_id,
                entity_id=case.entity_id,
                ts=case.opened_ts + timedelta(minutes=random.randint(5, 30)),
                text="Reviewed logs. No malicious activity found. Closing as false positive."
            ))
            if not eg04_injected and case.alert_ids:
                ground_truth.append({
                    "finding_id": "EG-04",
                    "entity_id": alert_map[case.alert_ids[0]].entity_id,
                    "scope": "analyst",
                    "target_id": eg04_analyst,
                    "description": "Repetitive template-driven closure notes."
                })
                eg04_injected = True
        else:
            notes.append(Note(
                case_id=case.case_id,
                entity_id=case.entity_id,
                ts=case.opened_ts + timedelta(minutes=random.randint(5, 30)),
                text=f"Analyst {case.owner} investigated {case_rule}. Findings: {random.choice(['Normal behavior', 'Authorized scan', 'Known issue'])}."
            ))
            
    # EG-02: Cases closed unusually fast
    normal_cases = [c for c in cases if c.owner not in (eg04_analyst, eg06_analyst) and c.alert_ids and alert_map[c.alert_ids[0]].rule_id != eg05_rule and c.severity >= 3]
    eg02_targets = random.sample(normal_cases, min(int(len(normal_cases) * 0.05), len(normal_cases)))
    for c in eg02_targets:
        c.closed_ts = c.opened_ts + timedelta(seconds=random.randint(1, 25))
        ground_truth.append({
            "finding_id": "EG-02",
            "entity_id": alert_map[c.alert_ids[0]].entity_id,
            "scope": "case",
            "target_id": c.case_id,
            "description": "Case closed unusually quickly conditioned on severity."
        })
            
    return events, notes

def inject_ex_07_change_point(alerts: List[Alert], ground_truth: List[Dict[str, Any]]):
    entities = list(set(a.entity_id for a in alerts))
    if not entities: return alerts
    
    ex07_entity = random.choice(entities)
    cutoff = datetime.now() - timedelta(days=7)
    
    alerts_to_drop = {a.alert_id for a in alerts if a.entity_id == ex07_entity and a.created_ts > cutoff}
    
    ground_truth.append({
        "finding_id": "EX-07",
        "entity_id": ex07_entity,
        "scope": "volume_series",
        "target_id": ex07_entity,
        "description": "Alert volume flatlines in the last 7 days (Change Point)."
    })
    
    return [a for a in alerts if a.alert_id not in alerts_to_drop]

def inject_ex_04_05_08(alerts: List[Alert], ground_truth: List[Dict[str, Any]]):
    entities = list(set(a.entity_id for a in alerts))
    if not entities: return alerts
    
    ex04_entity = random.choice(entities)
    ex05_entity = random.choice(entities)
    analysts = list(set(a.analyst_id for a in alerts))
    ex08_analyst = random.choice(analysts)
    
    # EX-08
    for a in alerts:
        if a.analyst_id == ex08_analyst:
            a.disposition = "Benign"
    ground_truth.append({
        "finding_id": "EX-08",
        "entity_id": "GLOBAL",
        "scope": "analyst",
        "target_id": ex08_analyst,
        "description": "Over-regularity: Analyst assigns 'Benign' to everything."
    })
    
    alerts_to_drop = set()
    # EX-05
    for a in alerts:
        if a.entity_id == ex05_entity and a.category == "Access" and a.severity == 3:
            alerts_to_drop.add(a.alert_id)
    ground_truth.append({
        "finding_id": "EX-05",
        "entity_id": ex05_entity,
        "scope": "grid",
        "target_id": "Access_Sev3",
        "description": "Missing common grid cell Access_Sev3."
    })
    
    # EX-04
    entity_alerts = [a for a in alerts if a.entity_id == ex04_entity]
    if entity_alerts:
        min_date = min(a.created_ts for a in entity_alerts)
        max_date = max(a.created_ts for a in entity_alerts)
        midpoint = min_date + (max_date - min_date) / 2
        h2_alerts = [a for a in entity_alerts if a.created_ts > midpoint]
        to_drop = random.sample(h2_alerts, int(len(h2_alerts) * 0.90))
        for a in to_drop:
            alerts_to_drop.add(a.alert_id)
        ground_truth.append({
            "finding_id": "EX-04",
            "entity_id": ex04_entity,
            "scope": "volume_series",
            "target_id": ex04_entity,
            "description": "Alert volume drifted heavily in the second half of the month."
        })
        
    return [a for a in alerts if a.alert_id not in alerts_to_drop]

def inject_ex_01_analyst(cases: List[Case], ground_truth: List[Dict[str, Any]]):
    analysts = list(set([c.owner for c in cases if c.owner]))
    if not analysts: return
    
    ex01_analyst = random.choice(analysts)
    ex01_cases = [c for c in cases if c.owner == ex01_analyst]
    
    for c in ex01_cases:
        c.closed_ts = c.opened_ts + timedelta(seconds=random.randint(1, 2))
        
    ground_truth.append({
        "finding_id": "EX-01",
        "entity_id": "GLOBAL",
        "scope": "analyst",
        "target_id": ex01_analyst,
        "description": "Analyst exhibits highly anomalous closure patterns (Isolation Forest)."
    })

def inject_ex_02_03(cases: List[Case], events: List[CaseEvent], ground_truth: List[Dict[str, Any]]):
    analysts = list(set([c.owner for c in cases if c.owner]))
    if len(analysts) < 3: return
    
    ex02_analyst = random.choice(analysts)
    ex03_analyst = random.choice([a for a in analysts if a != ex02_analyst])
    
    ex02_cases = [c for c in cases if c.owner == ex02_analyst]
    ex03_cases = [c for c in cases if c.owner == ex03_analyst]
    
    for c in ex03_cases:
        c.closed_ts = c.opened_ts + timedelta(seconds=60)
        
    ground_truth.append({
        "finding_id": "EX-03",
        "entity_id": "GLOBAL",
        "scope": "analyst",
        "target_id": ex03_analyst,
        "description": "Analyst has zero variance in closure time."
    })
    
    ex02_case_ids = {c.case_id for c in ex02_cases}
    events[:] = [e for e in events if e.case_id not in ex02_case_ids]
    
    for c in ex02_cases:
        events.append(CaseEvent(
            case_id=c.case_id,
            entity_id=c.entity_id,
            ts=c.opened_ts + timedelta(seconds=10),
            event_type="enrich",
            actor=ex02_analyst
        ))
        events.append(CaseEvent(
            case_id=c.case_id,
            entity_id=c.entity_id,
            ts=c.opened_ts + timedelta(seconds=20),
            event_type="status",
            actor=ex02_analyst
        ))
        
    ground_truth.append({
        "finding_id": "EX-02",
        "entity_id": "GLOBAL",
        "scope": "analyst",
        "target_id": ex02_analyst,
        "description": "Analyst uses exactly the same event path for all cases."
    })

def inject_ex_06(cases: List[Case], alerts: List[Alert], ground_truth: List[Dict[str, Any]]):
    entities = list(set(a.entity_id for a in alerts))
    if not entities: return
    ex06_entity = random.choice(entities)
    
    alert_map = {a.alert_id: a for a in alerts}
    ex06_cases = [c for c in cases if c.alert_ids and alert_map[c.alert_ids[0]].entity_id == ex06_entity]
    
    unique_rc = "Custom Entity Exception"
    for c in ex06_cases:
        c.root_cause = unique_rc
        
    if ex06_cases:
        ground_truth.append({
            "finding_id": "EX-06",
            "entity_id": ex06_entity,
            "scope": "root_cause",
            "target_id": unique_rc,
            "description": "Entity uses a frequent root cause that is completely absent in peers."
        })

def export_data(entities: List[Entity], assets: List[Asset], alerts: List[Alert], cases: List[Case], escalations: List[Escalation], events: List[CaseEvent], notes: List[Note], ground_truth: List[Dict[str, Any]]):
    """Export the generated data to Parquet and JSON for ground truth."""
    out_dir = Path(__file__).parent.parent.parent / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Export ground truth
    gt_file = out_dir / "ground_truth.json"
    with open(gt_file, "w") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Exported ground truth to {gt_file}")
    
    if pl is None:
        print("Polars is not installed yet. Skipping Parquet export.")
        return

    # Export Entities
    df_entities = pl.DataFrame([e.model_dump() for e in entities])
    df_entities.write_parquet(out_dir / "entities.parquet")
    
    # Export Assets
    df_assets = pl.DataFrame([a.model_dump(by_alias=True) for a in assets])
    df_assets.write_parquet(out_dir / "assets.parquet")
    
    # Export Alerts
    df_alerts = pl.DataFrame([a.model_dump() for a in alerts])
    df_alerts.write_parquet(out_dir / "alerts.parquet")
    
    # Export Cases
    df_cases = pl.DataFrame([c.model_dump() for c in cases])
    df_cases.write_parquet(out_dir / "cases.parquet")
    
    # Export Escalations
    df_escalations = pl.DataFrame([e.model_dump() for e in escalations])
    df_escalations.write_parquet(out_dir / "escalations.parquet")
    
    # Export Events
    df_events = pl.DataFrame([e.model_dump() for e in events])
    df_events.write_parquet(out_dir / "events.parquet")
    
    # Export Notes
    df_notes = pl.DataFrame([n.model_dump() for n in notes])
    df_notes.write_parquet(out_dir / "notes.parquet")
    
    print(f"Exported {len(entities)} entities to Parquet.")
    print(f"Exported {len(assets)} assets to Parquet.")
    print(f"Exported {len(alerts)} alerts to Parquet.")
    print(f"Exported {len(cases)} cases to Parquet.")
    print(f"Exported {len(escalations)} escalations to Parquet.")
    print(f"Exported {len(events)} events to Parquet.")
    print(f"Exported {len(notes)} notes to Parquet.")

def generate_sample_data():
    print("Generating healthy baseline data...")
    ents = generate_entities(10) # Reduced to 10 for quick testing
    asts = generate_assets(ents, avg_assets_per_ent=50)
    alts = generate_alerts(asts, days=30)
    
    print("Injecting weaknesses (Ground Truth)...")
    gt = []
    alts = inject_ex_07_change_point(alts, gt)
    alts = inject_ex_04_05_08(alts, gt)
    inject_fast_closure(alts, gt, fraction=0.02)
    alts = inject_silent_critical_assets(asts, alts, gt, n_assets=3)
    alts = inject_remaining_negative_space(alts, asts, ents, gt)
    
    cases, escalations = generate_cases_and_escalations(alts, gt)
    inject_ex_01_analyst(cases, gt)
    events, notes = generate_events_and_notes(cases, alts, gt)
    inject_ex_02_03(cases, events, gt)
    inject_ex_06(cases, alts, gt)
    
    print(f"Injected {len(gt)} known weaknesses.")
    export_data(ents, asts, alts, cases, escalations, events, notes, gt)
    print("Synthetic generation complete.")

if __name__ == "__main__":
    generate_sample_data()
