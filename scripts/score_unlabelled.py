"""Apply the trained model to postings WITHOUT a disclosed salary: the real use case.

No ground truth exists here, so this reports estimates, not accuracy. They rely on the test-set
evaluation (D-009, D-010) and on disclosure being random within each region (D-005).
Run from the project root (after train_model.py and evaluate_routing.py):
    python scripts/score_unlabelled.py
"""
from pathlib import Path

import duckdb
import joblib
import pandas as pd

from exec_screener.dataset import load_unlabelled
from exec_screener.model import prepare_features
from exec_screener.routing import ACCEPT, REJECT, REVIEW, route

DB_PATH = Path("data/processed/linkedin.duckdb")
MODEL_PATH = Path("models/model.joblib")
THRESHOLDS_PATH = Path("models/thresholds.json")
SCORES_PATH = Path("data/processed/unlabelled_scores.csv")

con = duckdb.connect(str(DB_PATH), read_only=True)
df = load_unlabelled(con)
model = joblib.load(MODEL_PATH)
thresholds = pd.read_json(THRESHOLDS_PATH, typ="series")

df["probability"] = model.predict_proba(prepare_features(df))[:, 1]
df["queue"] = route(df["probability"], thresholds["t_low"], thresholds["t_high"])

print(f"Postings without a salary: {len(df):,}")
print(f"Expected share >= $100k (mean calibrated probability): {df['probability'].mean():.1%} "
      f"(about {df['probability'].sum():,.0f} postings)\n")

print(f"Routing (D-011 thresholds: reject <= {thresholds['t_low']:.3f}, accept >= {thresholds['t_high']:.3f})")
for queue in [ACCEPT, REVIEW, REJECT]:
    in_queue = df["queue"] == queue
    print(f"   {queue:14s} {in_queue.sum():>8,} {in_queue.mean():>7.1%}")


def by(column: str) -> None:
    table = df.groupby(column)["probability"].agg(["size", "mean"]).sort_values("size", ascending=False)
    print(f"\nMean probability by {column}")
    for value, row in table.iterrows():
        print(f"   {value:24s} {int(row['size']):>8,} {row['mean']:>7.1%}")


by("region")
by("experience")

print("\nMost confident postings")
for _, row in df.nlargest(5, "probability").iterrows():
    print(f"   {row['probability']:.3f}  {str(row['title'])[:70]}")

df[["job_id", "title", "region", "experience", "probability", "queue"]].to_csv(SCORES_PATH, index=False)
print(f"\nSaved scores to {SCORES_PATH}")