from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector NS-01: Silent critical assets
# ---------------------------------------------------------

def run_ns_01():
    """
    Detects critical assets that have zero or very low alert rates.
    This identifies broken forwarding, unmonitored zones, or Negative Space.
    """
    conn = get_connection(read_only=True)
    print("Running Detector NS-01: Silent Critical Assets...")
    
    # Left join critical assets with alerts to find those with 0 count
    query = """
        SELECT 
            a.entity_id,
            a.asset_id,
            a.type,
            COUNT(al.alert_id) as alert_count
        FROM assets_view a
        LEFT JOIN alerts_view al ON a.asset_id = al.asset_id
        WHERE a.criticality = 'Critical'
        GROUP BY 1, 2, 3
        HAVING COUNT(al.alert_id) = 0
    """
    
    try:
        results = conn.execute(query).fetchall()
        
        findings = []
        for row in results:
            findings.append({
                "detector_id": "NS-01",
                "entity_id": row[0],
                "target_id": row[1],
                "asset_type": row[2],
                "rationale": f"Critical asset of type '{row[2]}' produced 0 alerts in the given period."
            })
            
        print(f"  -> Found {len(findings)} negative space instances.")
        return findings
    except Exception as e:
        print(f"Error running NS-01: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ns_01()
    if findings:
        print(f"Sample finding: {findings[0]}")
