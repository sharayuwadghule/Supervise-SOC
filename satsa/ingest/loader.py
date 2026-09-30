from pathlib import Path
from satsa.store.db import get_connection

# ---------------------------------------------------------
# SAT-SA Ingestion Engine (Phase 3)
# ---------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "synthetic"

def load_data():
    """
    Loads Parquet files into DuckDB views or tables.
    For this batch system, querying Parquet directly via DuckDB is highly efficient.
    """
    if not DATA_DIR.exists():
        print(f"Data directory {DATA_DIR} does not exist. Run the generator first.")
        return

    conn = get_connection()
    
    try:
        # Check if files exist before creating views
        if (DATA_DIR / "entities.parquet").exists():
            conn.execute(f"CREATE OR REPLACE VIEW entities_view AS SELECT * FROM read_parquet('{DATA_DIR}/entities.parquet')")
            print("Loaded entities view.")
            
        if (DATA_DIR / "assets.parquet").exists():
            conn.execute(f"CREATE OR REPLACE VIEW assets_view AS SELECT * FROM read_parquet('{DATA_DIR}/assets.parquet')")
            print("Loaded assets view.")
            
        if (DATA_DIR / "alerts.parquet").exists():
            conn.execute(f"CREATE OR REPLACE VIEW alerts_view AS SELECT * FROM read_parquet('{DATA_DIR}/alerts.parquet')")
            print("Loaded alerts view.")
            
    except Exception as e:
        print(f"Error during data load: {e}")
    finally:
        conn.close()

def run_data_quality_report():
    """
    Runs basic data quality checks on the loaded data.
    """
    conn = get_connection(read_only=True)
    print("\n--- Data Quality Report ---")
    
    try:
        # Check 1: Missing Analyst IDs (Optional field coverage)
        res = conn.execute("""
            SELECT count(*) as total, 
                   sum(case when analyst_id is null then 1 else 0 end) as missing
            FROM alerts_view
        """).fetchone()
        if res:
            total, missing = res
            print(f"[DQ] Alerts missing analyst_id: {missing} / {total} ({(missing/total*100) if total else 0:.1f}%)")

        # Check 2: Orphan Alerts (Alerts referencing non-existent assets)
        res = conn.execute("""
            SELECT count(*) 
            FROM alerts_view al
            LEFT JOIN assets_view a ON al.asset_id = a.asset_id
            WHERE a.asset_id IS NULL AND al.asset_id IS NOT NULL
        """).fetchone()
        if res and res[0] > 0:
            print(f"[DQ-WARN] Found {res[0]} orphan alerts referencing missing assets.")
        else:
            print("[DQ] No orphan alerts found.")
            
    except Exception as e:
        print(f"Error running DQ report: {e} (Have you loaded the data yet?)")
    finally:
        conn.close()

if __name__ == "__main__":
    load_data()
    run_data_quality_report()
