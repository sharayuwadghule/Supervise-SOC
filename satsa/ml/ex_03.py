import pandas as pd
from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EX-03: Timestamp rounding / Low variance handling
# ---------------------------------------------------------

def run_ex_03():
    conn = get_connection(read_only=True)
    print("Running ML Detector EX-03: Low Variance Handling Time...")
    
    query = """
        SELECT 
            owner as analyst,
            COUNT(case_id) as case_count,
            STDDEV(epoch(closed_ts) - epoch(opened_ts)) as std_closure_time
        FROM cases_view
        WHERE owner IS NOT NULL AND closed_ts IS NOT NULL
        GROUP BY owner
        HAVING COUNT(case_id) >= 5
    """
    
    try:
        df = conn.execute(query).fetchdf()
        if df.empty:
            return []
            
        findings = []
        for _, row in df.iterrows():
            if pd.notna(row['std_closure_time']) and row['std_closure_time'] < 2.0:
                findings.append({
                    "detector_id": "EX-03",
                    "entity_id": "GLOBAL",
                    "target_id": row['analyst'],
                    "severity": 4,
                    "rationale": f"Analyst '{row['analyst']}' has unnaturally low variance in case handling time (std dev: {row['std_closure_time']:.2f}s). Indicates automation/scripting."
                })
                
        print(f"  -> Found {len(findings)} ML exploratory findings.")
        return findings
    except Exception as e:
        print(f"Error running EX-03: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ex_03()
    if findings:
        print(f"Sample finding: {findings[0]}")
