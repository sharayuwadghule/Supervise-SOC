import pandas as pd
from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EX-04: Drift against own earlier periods
# ---------------------------------------------------------

def run_ex_04():
    conn = get_connection(read_only=True)
    print("Running ML Detector EX-04: Concept Drift Analysis...")
    
    query = """
        SELECT 
            entity_id,
            created_ts
        FROM alerts_view
    """
    
    try:
        df = conn.execute(query).fetchdf()
        if df.empty: return []
        
        df['created_ts'] = pd.to_datetime(df['created_ts'])
        
        findings = []
        for entity in df['entity_id'].unique():
            entity_df = df[df['entity_id'] == entity]
            if len(entity_df) < 20: continue
            
            min_date = entity_df['created_ts'].min()
            max_date = entity_df['created_ts'].max()
            midpoint = min_date + (max_date - min_date) / 2
            
            h1_count = len(entity_df[entity_df['created_ts'] <= midpoint])
            h2_count = len(entity_df[entity_df['created_ts'] > midpoint])
            
            if h1_count > 10 and h2_count < (h1_count * 0.2):
                findings.append({
                    "detector_id": "EX-04",
                    "entity_id": entity,
                    "target_id": entity,
                    "severity": 3,
                    "rationale": f"Severe alert volume drift. H1 volume: {h1_count}, H2 volume: {h2_count}."
                })
                
        print(f"  -> Found {len(findings)} ML exploratory findings.")
        return findings
    except Exception as e:
        print(f"Error running EX-04: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ex_04()
    if findings: print(f"Sample finding: {findings[0]}")
