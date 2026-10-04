from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector NS-04: Unexpectedly low activity levels
# ---------------------------------------------------------

def run_ns_04():
    conn = get_connection(read_only=True)
    print("Running Detector NS-04: Unexpectedly low activity levels...")
    
    # Expected vs observed volume model (simplified to average alerts per asset ratio)
    query = """
        WITH EntityAssets AS (
            SELECT entity_id, COUNT(*) as asset_count
            FROM assets_view
            GROUP BY entity_id
        ),
        EntityAlerts AS (
            SELECT entity_id, COUNT(*) as alert_count
            FROM alerts_view
            GROUP BY entity_id
        ),
        GlobalAverages AS (
            SELECT SUM(alert_count) * 1.0 / SUM(asset_count) as avg_alerts_per_asset
            FROM EntityAssets JOIN EntityAlerts USING (entity_id)
        )
        SELECT 
            ea.entity_id, 
            ea.asset_count, 
            COALESCE(eal.alert_count, 0) as alert_count,
            ea.asset_count * ga.avg_alerts_per_asset as expected_alerts
        FROM EntityAssets ea
        LEFT JOIN EntityAlerts eal ON ea.entity_id = eal.entity_id
        CROSS JOIN GlobalAverages ga
        WHERE COALESCE(eal.alert_count, 0) < (ea.asset_count * ga.avg_alerts_per_asset * 0.2)
    """
    
    try:
        results = conn.execute(query).fetchall()
        
        findings = []
        for row in results:
            findings.append({
                "detector_id": "NS-04",
                "entity_id": row[0],
                "target_id": row[0],
                "severity": 4,
                "rationale": f"Observed {row[2]} alerts, but expected ~{int(row[3])} based on global asset ratio."
            })
            
        print(f"  -> Found {len(findings)} negative space instances.")
        return findings
    except Exception as e:
        print(f"Error running NS-04: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ns_04()
    if findings:
        print(f"Sample finding: {findings[0]}")
