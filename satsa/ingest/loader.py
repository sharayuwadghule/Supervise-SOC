from pathlib import Path
from satsa.store.db import get_connection

def load_data(*args, **kwargs):
    """
    Creates DuckDB views that combine Parquet files from both 'synthetic' and 'real' data directories.
    """
    conn = get_connection(read_only=False)
    base_dir = Path(__file__).parent.parent.parent / "data"
    
    tables = ["entities", "assets", "alerts", "cases", "events"]
    
    for table in tables:
        paths = []
        syn_path = base_dir / "synthetic" / f"{table}.parquet"
        real_path = base_dir / "real" / f"{table}.parquet"
        
        if syn_path.exists():
            paths.append(f"'{syn_path.as_posix()}'")
        if real_path.exists():
            paths.append(f"'{real_path.as_posix()}'")
            
        if not paths:
            # Create an empty view if no files exist so queries don't crash
            try:
                # We need a dummy schema, but since we don't know it, we just drop the view
                conn.execute(f"DROP VIEW IF EXISTS {table}_view")
            except Exception:
                pass
            continue
            
        # If multiple files exist, we can use read_parquet with a list
        files_str = ", ".join(paths)
        query = f"CREATE OR REPLACE VIEW {table}_view AS SELECT * FROM read_parquet([{files_str}], union_by_name=True)"
        try:
            conn.execute(query)
            print(f"Created view {table}_view over {len(paths)} sources.")
        except Exception as e:
            print(f"Failed to create view {table}_view: {e}")
            
    conn.close()
    return True
