from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector NS-06: Absence relative to comparable environments
# ---------------------------------------------------------

def run_ns_06():
    conn = get_connection(read_only=True)
    print("Running Detector NS-06: Absence relative to comparable environments...")
    
    # We compare an entity's volume to the global mean (z-score approach)
    # If the Z-score is heavily negative (< -1.25), it's a global outlier.
    query = """
        WITH EntityVolumes AS (
            SELECT e.entity_id, COALESCE(COUNT(al.alert_id), 0) as alert_count
            FROM entities_view e
            LEFT JOIN alerts_view al ON e.entity_id = al.entity_id
            GROUP BY e.entity_id
        ),
        GlobalStats AS (
            SELECT 
                avg(alert_count) as mean_vol,
                stddev(alert_count) as std_vol
            FROM EntityVolumes
        )
        SELECT ev.entity_id, ev.alert_count, gs.mean_vol, gs.std_vol, 
               (ev.alert_count - gs.mean_vol) / NULLIF(gs.std_vol, 0) as z_score
        FROM EntityVolumes ev
        CROSS JOIN GlobalStats gs
        WHERE (ev.alert_count - gs.mean_vol) / NULLIF(gs.std_vol, 0) < -1.25
    """
    
    try:
        results = conn.execute(query).fetchall()
        
        findings = []
        for row in results:
            findings.append({
                "detector_id": "NS-06",
                "entity_id": row[0],
                "target_id": row[0],
                "severity": 5,
                "rationale": f"Alert volume ({row[1]}) is a global outlier (z-score: {row[4]:.2f}) compared to peers."
            })
            
        print(f"  -> Found {len(findings)} negative space instances.")
        return findings
    except Exception as e:
        print(f"Error running NS-06: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ns_06()
    if findings:
        print(f"Sample finding: {findings[0]}")
