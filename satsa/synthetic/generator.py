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

from satsa.store.schema import Entity, Asset, Alert

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

def export_data(entities: List[Entity], assets: List[Asset], alerts: List[Alert], ground_truth: List[Dict[str, Any]]):
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
    
    print(f"Exported {len(entities)} entities to Parquet.")
    print(f"Exported {len(assets)} assets to Parquet.")
    print(f"Exported {len(alerts)} alerts to Parquet.")

def generate_sample_data():
    print("Generating healthy baseline data...")
    ents = generate_entities(10) # Reduced to 10 for quick testing
    asts = generate_assets(ents, avg_assets_per_ent=50)
    alts = generate_alerts(asts, days=30)
    
    print("Injecting weaknesses (Ground Truth)...")
    gt = []
    inject_fast_closure(alts, gt, fraction=0.02)
    alts = inject_silent_critical_assets(asts, alts, gt, n_assets=3)
    
    print(f"Injected {len(gt)} known weaknesses.")
    export_data(ents, asts, alts, gt)
    print("Synthetic generation complete.")

if __name__ == "__main__":
    generate_sample_data()
