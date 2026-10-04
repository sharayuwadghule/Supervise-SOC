import pandas as pd
from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EX-08: Over-regularity checks
# ---------------------------------------------------------

def run_ex_08():
    conn = get_connection(read_only=True)
    print("Running ML Detector EX-08: Over-regularity checks...")
    
    query = """
        SELECT analyst_id, disposition
        FROM alerts_view
        WHERE analyst_id IS NOT NULL AND disposition IS NOT NULL
    """
    
    try:
        df = conn.execute(query).fetchdf()
        if df.empty: return []
        
        findings = []
        for analyst, group in df.groupby('analyst_id'):
            if len(group) > 20:
                unique_disps = group['disposition'].nunique()
                if unique_disps == 1:
                    disp = group['disposition'].iloc[0]
                    findings.append({
                        "detector_id": "EX-08",
                        "entity_id": "GLOBAL",
                        "target_id": analyst,
                        "severity": 4,
                        "rationale": f"Over-regularity: Analyst '{analyst}' assigned disposition '{disp}' to 100% of their {len(group)} alerts."
                    })
                    
        print(f"  -> Found {len(findings)} ML exploratory findings.")
        return findings
    except Exception as e:
        print(f"Error running EX-08: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ex_08()
    if findings: print(f"Sample finding: {findings[0]}")
