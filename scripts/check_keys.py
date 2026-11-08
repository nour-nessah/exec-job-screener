"""Key integrity checks between the raw LinkedIn tables (primary and foreign keys).

Run from the project root:
    python scripts/check_keys.py
"""
from pathlib import Path

import duckdb

RAW_DIR = Path("data/raw/linkedin")

con = duckdb.connect()

# Register each CSV file as a named view, so the SQL below reads like normal tables.
con.execute(f"CREATE VIEW postings  AS SELECT * FROM read_csv('{RAW_DIR / 'postings.csv'}')")
con.execute(f"CREATE VIEW salaries  AS SELECT * FROM read_csv('{RAW_DIR / 'jobs' / 'salaries.csv'}')")
con.execute(f"CREATE VIEW companies AS SELECT * FROM read_csv('{RAW_DIR / 'companies' / 'companies.csv'}')")


def scalar(sql: str) -> int:
    """Run a query that returns a single value, and return that value."""
    return con.sql(sql).fetchall()[0][0]


# --- 1. Primary keys --------------------------------------------------------
print("1. Primary keys (each ID must be unique and never missing)")
for table, key in [("postings", "job_id"), ("salaries", "job_id"), ("companies", "company_id")]:
    n_rows, n_unique, n_missing = con.sql(
        f"SELECT COUNT(*), COUNT(DISTINCT {key}), COUNT(*) - COUNT({key}) FROM {table}"
    ).fetchall()[0]
    print(f"   {table:10s} {key:11s} rows={n_rows:>7,}  unique={n_unique:>7,}  missing={n_missing:>5,}")

# --- 2. Foreign keys --------------------------------------------------------
HAS_SALARY = "(p.min_salary IS NOT NULL OR p.med_salary IS NOT NULL OR p.max_salary IS NOT NULL)"

orphan_salaries = scalar("""
    SELECT COUNT(*) FROM salaries s
    WHERE NOT EXISTS (SELECT 1 FROM postings p WHERE p.job_id = s.job_id)
""")
salary_without_row = scalar(f"""
    SELECT COUNT(*) FROM postings p
    WHERE {HAS_SALARY}
      AND NOT EXISTS (SELECT 1 FROM salaries s WHERE s.job_id = p.job_id)
""")
row_without_salary = scalar(f"""
    SELECT COUNT(*) FROM postings p
    WHERE NOT {HAS_SALARY}
      AND EXISTS (SELECT 1 FROM salaries s WHERE s.job_id = p.job_id)
""")
missing_company = scalar("SELECT COUNT(*) FROM postings WHERE company_id IS NULL")
unknown_company = scalar("""
    SELECT COUNT(*) FROM postings p
    WHERE p.company_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.company_id = p.company_id)
""")

print("\n2. Foreign keys (references between tables)")
print(f"   salary rows whose job_id is not in postings:          {orphan_salaries:>7,}")
print(f"   postings with salary fields but no salaries row:      {salary_without_row:>7,}")
print(f"   postings with a salaries row but no salary fields:    {row_without_salary:>7,}")
print(f"   postings with no company_id:                          {missing_company:>7,}")
print(f"   postings whose company_id is not in companies:        {unknown_company:>7,}")