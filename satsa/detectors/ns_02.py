from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector NS-02: Absence of expected alert categories
# ---------------------------------------------------------

def run_ns_02():
    conn = get_connection(read_only=True)
    print("Running Detector NS-02: Missing expected alert categories...")
    
    query = """
        WITH CategoryFrequency AS (
            SELECT category, COUNT(DISTINCT entity_id) as entity_count
            FROM alerts_view
            GROUP BY category
        ),
        GlobalEntities AS (
            SELECT COUNT(DISTINCT entity_id) as total_entities FROM entities_view
        ),
        CommonCategories AS (
            SELECT cf.category 
            FROM CategoryFrequency cf, GlobalEntities ge
            WHERE cf.entity_count * 1.0 / ge.total_entities >= 0.8
        ),
        EntityCategories AS (
            SELECT entity_id, category 
            FROM alerts_view
            GROUP BY entity_id, category
        )
        SELECT e.entity_id, c.category
        FROM entities_view e
        CROSS JOIN CommonCategories c
        LEFT JOIN EntityCategories ec ON e.entity_id = ec.entity_id AND c.category = ec.category
        WHERE ec.category IS NULL
    """
    
    try:
        results = conn.execute(query).fetchall()
        
        findings = []
        for row in results:
            findings.append({
                "detector_id": "NS-02",
                "entity_id": row[0],
                "target_id": row[1],
                "severity": 3,
                "rationale": f"Category '{row[1]}' is present in >80% of peers but missing for this entity."
            })
            
        print(f"  -> Found {len(findings)} negative space instances.")
        return findings
    except Exception as e:
        print(f"Error running NS-02: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ns_02()
    if findings:
        print(f"Sample finding: {findings[0]}")
