import pandas as pd
from sklearn.ensemble import IsolationForest
from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EX-01: Analyst Fatigue / Behavior Anomaly
# ---------------------------------------------------------

def run_ex_01():
    conn = get_connection(read_only=True)
    print("Running ML Detector EX-01: Analyst Behavior Anomaly (Isolation Forest)...")
    
    query = """
        SELECT 
            c.owner as analyst,
            COUNT(c.case_id) as total_cases,
            AVG(epoch(c.closed_ts) - epoch(c.opened_ts)) as avg_closure_time,
            SUM(CASE WHEN epoch(c.closed_ts) - epoch(c.opened_ts) < 60 THEN 1 ELSE 0 END) * 1.0 / COUNT(c.case_id) as fast_closure_rate
        FROM cases_view c
        WHERE c.owner IS NOT NULL AND c.closed_ts IS NOT NULL
        GROUP BY c.owner
    """
    
    try:
        df = conn.execute(query).fetchdf()
        if df.empty:
            return []
            
        # Features for ML
        features = df[['total_cases', 'avg_closure_time', 'fast_closure_rate']].fillna(0)
        
        # Train Isolation Forest
        iso = IsolationForest(contamination=0.1, random_state=42)
        df['anomaly'] = iso.fit_predict(features)
        
        # -1 indicates anomaly
        anomalies = df[df['anomaly'] == -1]
        
        findings = []
        for _, row in anomalies.iterrows():
            findings.append({
                "detector_id": "EX-01",
                "entity_id": "GLOBAL",
                "target_id": row['analyst'],
                "severity": 4,
                "rationale": f"Analyst '{row['analyst']}' exhibits anomalous behavior (Isolation Forest outlier). " 
                             f"Volume: {row['total_cases']}, Fast Closure Rate: {row['fast_closure_rate']:.2%}"
            })
            
        print(f"  -> Found {len(findings)} ML exploratory findings.")
        return findings
    except Exception as e:
        print(f"Error running EX-01: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ex_01()
    if findings:
        print(f"Sample finding: {findings[0]}")
