"""First look at the raw LinkedIn data: row and column counts for every CSV file.

Run from the project root:
    python scripts/profile_raw.py
"""
from pathlib import Path

import duckdb

RAW_DIR = Path("data/raw/linkedin")

con = duckdb.connect()  # in-memory database: nothing is written to disk

csv_files = sorted(RAW_DIR.rglob("*.csv"))
print(f"Found {len(csv_files)} CSV files in {RAW_DIR}\n")

for csv_path in csv_files:
    relation = con.sql(f"SELECT * FROM read_csv('{csv_path}')")
    n_cols = len(relation.columns)
    n_rows = con.sql(f"SELECT COUNT(*) FROM read_csv('{csv_path}')").fetchall()[0][0]
    name = str(csv_path.relative_to(RAW_DIR))
    print(f"{name:40s} {n_rows:>9,} rows  {n_cols:>3} cols")