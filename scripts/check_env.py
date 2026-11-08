"""Environment smoke test: verifies that all core libraries import AND work."""
import sys

import duckdb
import matplotlib
import numpy as np
import pandas as pd
import pytest
import requests
import sklearn
from sklearn.linear_model import LogisticRegression

print("python      ", sys.version.split()[0])
for name, mod in [
    ("pandas", pd),
    ("numpy", np),
    ("duckdb", duckdb),
    ("scikit-learn", sklearn),
    ("matplotlib", matplotlib),
    ("requests", requests),
    ("pytest", pytest),
]:
    print(f"{name:12s}", mod.__version__)

# DuckDB: run SQL directly on a pandas DataFrame
df = pd.DataFrame(
    {"title": ["CFO", "Intern", "Head of Sales"], "salary": [180000, 25000, 120000]}
)
print(duckdb.sql("SELECT COUNT(*) AS n_exec FROM df WHERE salary >= 100000").fetchall())

# scikit-learn: fit a tiny model
model = LogisticRegression().fit(np.array([[0], [1], [2], [3]]), [0, 0, 1, 1])
print("sklearn prediction for x=2.5:", model.predict([[2.5]]))

print("\nAll checks passed.")