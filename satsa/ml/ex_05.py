import pandas as pd
from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EX-05: Expected vs Observed Grid (Missing Cells)
# ---------------------------------------------------------

def run_ex_05():
    conn = get_connection(read_only=True)
    print("Running ML Detector EX-05: Expected vs Observed Grid...")
    
    query = """
        SELECT entity_id, category, severity
        FROM alerts_view
    """
    
    try:
        df = conn.execute(query).fetchdf()
        if df.empty: return []
        
        # Calculate global frequencies of (category, severity)
        total_alerts = len(df)
        grid_freq = df.groupby(['category', 'severity']).size() / total_alerts
        
        # Identify common grid cells (> 5% of all alerts)
        common_cells = grid_freq[grid_freq > 0.05].index.tolist()
        
        findings = []
        for entity in df['entity_id'].unique():
            entity_df = df[df['entity_id'] == entity]
            if len(entity_df) < 50: continue # Only check entities with enough volume
            
            entity_cells = set(zip(entity_df['category'], entity_df['severity']))
            
            for expected_cell in common_cells:
                if expected_cell not in entity_cells:
                    findings.append({
                        "detector_id": "EX-05",
                        "entity_id": entity,
                        "target_id": f"{expected_cell[0]}_Sev{expected_cell[1]}",
                        "severity": 4,
                        "rationale": f"Missing expected cell: {expected_cell[0]} Sev {expected_cell[1]} is common globally, but entity has 0."
                    })
                    
        print(f"  -> Found {len(findings)} ML exploratory findings.")
        return findings
    except Exception as e:
        print(f"Error running EX-05: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ex_05()
    if findings: print(f"Sample finding: {findings[0]}")
