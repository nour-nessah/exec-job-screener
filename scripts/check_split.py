"""Compare a random split with the company-grouped split (D-008): sizes, balance, duplicates.

Run from the project root:
    python scripts/check_split.py
"""
from pathlib import Path

import duckdb

from exec_screener.dataset import is_test, load_labelled

DB_PATH = Path("data/processed/linkedin.duckdb")
con = duckdb.connect(str(DB_PATH), read_only=True)

df = load_labelled(con)
df["is_test_random"] = [is_test(f"job:{job_id}") for job_id in df["job_id"]]

# A "twin" = a test posting whose exact title + description also appears in training.
twin_key = df["title"].fillna("").str.lower().str.strip() + "||" + df["description"].fillna("").str.strip()

print(f"Labelled postings: {len(df):,} in {df['group'].nunique():,} company groups\n")
print(f"{'split':8s} {'train':>8s} {'test':>7s} {'test %':>7s} {'pos train':>10s} {'pos test':>9s} {'test twins':>11s} {'shared groups':>14s}")
for name, column in [("random", "is_test_random"), ("grouped", "is_test")]:
    test = df[column]
    train_keys = set(twin_key[~test])
    n_twins = int(twin_key[test].isin(train_keys).sum())
    n_shared = len(set(df["group"][test]) & set(df["group"][~test]))
    print(
        f"{name:8s} {(~test).sum():>8,} {test.sum():>7,} {test.mean():>7.1%} "
        f"{df['label'][~test].mean():>10.1%} {df['label'][test].mean():>9.1%} "
        f"{n_twins:>5,} ({n_twins / test.sum():.1%}) {n_shared:>14,}"
    )