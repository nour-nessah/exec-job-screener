"""Load all raw LinkedIn CSV files into one DuckDB database file.

The raw CSVs are never modified; this script rebuilds the database from scratch.
Run from the project root:
    python scripts/build_db.py
"""
import time
from pathlib import Path

import duckdb

RAW_DIR = Path("data/raw/linkedin")
DB_PATH = Path("data/processed/linkedin.duckdb")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
start = time.perf_counter()

con = duckdb.connect(str(DB_PATH))
for csv_path in sorted(RAW_DIR.rglob("*.csv")):
    table = csv_path.stem  # e.g. "postings", "salaries", "companies"
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv('{csv_path}')")
    n_rows = con.sql(f"SELECT COUNT(*) FROM {table}").fetchall()[0][0]
    print(f"{table:22s} {n_rows:>9,} rows")
con.close()

elapsed = time.perf_counter() - start
size_mb = DB_PATH.stat().st_size / 1e6
print(f"\nBuilt {DB_PATH} ({size_mb:.0f} MB) in {elapsed:.1f} s")