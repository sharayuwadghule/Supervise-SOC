from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EG-01: Unusually fast closure
# ---------------------------------------------------------

def run_eg_01():
    """
    Detects high-severity alerts that are closed abnormally fast.
    In a real implementation, this would compare against historical baselines
    and peer distributions using robust z-scores. 
    Here, we use a simple threshold query for demonstration.
    """
    conn = get_connection(read_only=True)
    print("Running Detector EG-01: Fast Closure on High Severity Alerts...")
    
    # We look for severity >= 4 and closure within 60 seconds (our injector uses <30s)
    query = """
        SELECT 
            entity_id,
            alert_id,
            severity,
            epoch(closed_ts) - epoch(created_ts) as time_to_close_seconds
        FROM alerts_view
        WHERE severity >= 4 
          AND closed_ts IS NOT NULL
          AND epoch(closed_ts) - epoch(created_ts) < 60
    """
    
    try:
        results = conn.execute(query).fetchall()
        
        findings = []
        for row in results:
            findings.append({
                "detector_id": "EG-01",
                "entity_id": row[0],
                "target_id": row[1],
                "severity": row[2],
                "time_to_close_seconds": row[3],
                "rationale": f"High severity alert closed in {row[3]} seconds, significantly faster than baseline."
            })
            
        print(f"  -> Found {len(findings)} execution gaps.")
        return findings
    except Exception as e:
        print(f"Error running EG-01: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_eg_01()
    if findings:
        print(f"Sample finding: {findings[0]}")
