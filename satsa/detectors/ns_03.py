from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector NS-03: Missing investigation records (No Case)
# ---------------------------------------------------------

def run_ns_03():
    """
    Detects high severity alerts that have no associated case.
    """
    conn = get_connection(read_only=True)
    print("Running Detector NS-03: Missing investigation records...")
    
    # We unnest the alert_ids array from cases_view
    query = """
        SELECT 
            al.entity_id,
            al.alert_id,
            al.severity
        FROM alerts_view al
        LEFT JOIN (
            SELECT case_id, unnest(alert_ids) as alert_id FROM cases_view
        ) c ON al.alert_id = c.alert_id
        WHERE al.severity >= 4
          AND c.case_id IS NULL
    """
    
    try:
        results = conn.execute(query).fetchall()
        
        findings = []
        for row in results:
            findings.append({
                "detector_id": "NS-03",
                "entity_id": row[0],
                "target_id": row[1],
                "severity": row[2],
                "rationale": f"High severity alert ({row[2]}) was raised but no investigation case was opened."
            })
            
        print(f"  -> Found {len(findings)} negative space instances.")
        return findings
    except Exception as e:
        print(f"Error running NS-03: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ns_03()
    if findings:
        print(f"Sample finding: {findings[0]}")
