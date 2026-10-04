import pandas as pd
from satsa.store.db import get_connection

# ---------------------------------------------------------
# Detector EX-07: Change Point Detection (Volume Flatlines)
# ---------------------------------------------------------

def run_ex_07():
    conn = get_connection(read_only=True)
    print("Running ML Detector EX-07: Change Point Detection on Volume Series...")
    
    query = """
        SELECT 
            entity_id,
            CAST(created_ts AS DATE) as date_val,
            COUNT(alert_id) as alert_count
        FROM alerts_view
        GROUP BY entity_id, CAST(created_ts AS DATE)
        ORDER BY entity_id, date_val
    """
    
    try:
        df = conn.execute(query).fetchdf()
        if df.empty:
            return []
            
        df['date_val'] = pd.to_datetime(df['date_val'])
        
        min_date = df['date_val'].min()
        max_date = df['date_val'].max()
        idx = pd.date_range(min_date, max_date)
        
        findings = []
        entities = df['entity_id'].unique()
        
        for entity in entities:
            entity_data = df[df['entity_id'] == entity].set_index('date_val')[['alert_count']]
            entity_data = entity_data.groupby('date_val').sum()
            entity_data = entity_data.reindex(idx, fill_value=0)
            
            if len(entity_data) < 7:
                continue
                
            recent_avg = entity_data.iloc[-7:]['alert_count'].mean()
            prior_avg = entity_data.iloc[:-7]['alert_count'].mean()
            
            if recent_avg < 0.5 and prior_avg > 2.0:
                findings.append({
                    "detector_id": "EX-07",
                    "entity_id": entity,
                    "target_id": entity,
                    "severity": 4,
                    "rationale": f"Alert volume flatlined in recent days (Change point detected). Prior avg: {prior_avg:.1f}, Recent avg: {recent_avg:.1f}."
                })
            
        print(f"  -> Found {len(findings)} ML exploratory findings.")
        return findings
    except Exception as e:
        print(f"Error running EX-07: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    findings = run_ex_07()
    if findings:
        print(f"Sample finding: {findings[0]}")
