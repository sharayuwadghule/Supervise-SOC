import duckdb
from pathlib import Path

# ---------------------------------------------------------
# SAT-SA DuckDB Connection and Setup
# ---------------------------------------------------------

DB_FILE = Path(__file__).parent.parent.parent / "data" / "satsa.duckdb"

def get_connection(read_only: bool = False):
    """
    Returns a DuckDB connection.
    Ensures the data directory exists.
    """
    if not DB_FILE.parent.exists():
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # In a real air-gapped run, we might use an in-memory DB or a specific path.
    conn = duckdb.connect(str(DB_FILE), read_only=read_only)
    return conn

def init_db():
    """
    Initializes the database schema if it doesn't exist.
    """
    conn = get_connection()
    
    # We will mostly query Parquet files directly, but we can create 
    # views or materialized tables here if needed.
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        entity_id VARCHAR PRIMARY KEY,
        sector VARCHAR,
        size_tier VARCHAR,
        region VARCHAR,
        soc_model VARCHAR
    );
    """)
    
    # Example for alerts (we would likely read these from parquet partition views)
    # conn.execute(...)
    
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_FILE}")
