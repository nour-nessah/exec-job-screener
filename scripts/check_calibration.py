"""Are the model's probabilities trustworthy? Reliability table, Brier score, per-region check.

Reads the predictions written by scripts/train_model.py (no retraining).
Run from the project root:
    python scripts/check_calibration.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

PREDICTIONS_PATH = Path("data/processed/test_predictions.csv")
FIGURE_PATH = Path("reports/figures/calibration.png")
N_BINS = 10

MODEL_COLOR = "#2a78d6"
TEXT, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"

df = pd.read_csv(PREDICTIONS_PATH)
truth = df["label"].astype(bool).to_numpy()
probability = df["probability"].to_numpy()

# --- 1. Reliability table ---------------------------------------------------
edges = np.linspace(0, 1, N_BINS + 1)
bin_index = np.clip(np.digitize(probability, edges) - 1, 0, N_BINS - 1)

print("1. Reliability: predicted probability vs observed share of jobs >= $100k")
print(f"   {'bin':>9s} {'postings':>9s} {'predicted':>10s} {'observed':>9s} {'gap':>7s}")
predicted_means, observed_shares = [], []
ece = 0.0
for b in range(N_BINS):
    in_bin = bin_index == b
    n = int(in_bin.sum())
    predicted, observed = probability[in_bin].mean(), truth[in_bin].mean()
    ece += n / len(df) * abs(predicted - observed)
    predicted_means.append(predicted)
    observed_shares.append(observed)
    print(f"   {edges[b]:.1f}-{edges[b + 1]:.1f} {n:>9,} {predicted:>10.1%} {observed:>9.1%} {observed - predicted:>+7.1%}")

# --- 2. Summary scores ------------------------------------------------------
base_rate = truth.mean()
brier = brier_score_loss(truth, probability)
brier_reference = brier_score_loss(truth, np.full(len(df), base_rate))
print(f"\n2. Brier score: {brier:.3f}   (always predicting {base_rate:.1%}: {brier_reference:.3f})")
print(f"   Expected calibration error (ECE): {ece:.3f}")

# --- 3. Calibration per region (D-005) --------------------------------------
print("\n3. Mean predicted probability vs observed share, per region")
print(f"   {'region':24s} {'postings':>9s} {'predicted':>10s} {'observed':>9s}")
for region, group in df.groupby("region"):
    print(f"   {region:24s} {len(group):>9,} {group['probability'].mean():>10.1%} {group['label'].mean():>9.1%}")

# --- Figure: reliability diagram ------------------------------------------------
fig, ax = plt.subplots(figsize=(5.5, 5), dpi=200)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1, linestyle="--")
ax.text(0.97, 0.90, "perfect calibration", rotation=45, ha="right", va="bottom",
        fontsize=8, color=MUTED, rotation_mode="anchor")
ax.plot(predicted_means, observed_shares, color=MODEL_COLOR, linewidth=2,
        marker="o", markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.5)
ax.text(0.03, 0.95, f"Test set, {len(df):,} postings · expected calibration error {ece:.3f}",
        ha="left", va="top", fontsize=8, color=MUTED)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_xlabel("Predicted probability (mean per bin)", color=TEXT)
ax.set_ylabel("Observed share of jobs ≥ $100k", color=TEXT)
ax.set_title("When the model says 80%, about 80% are above $100k",
             loc="left", fontsize=11, color=TEXT)
ax.grid(color=GRID, linewidth=0.8)
ax.tick_params(colors=MUTED, labelsize=8)
for side in ["top", "right"]:
    ax.spines[side].set_visible(False)
for side in ["left", "bottom"]:
    ax.spines[side].set_color(GRID)

FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGURE_PATH, bbox_inches="tight", facecolor=SURFACE)
print(f"\nSaved figure to {FIGURE_PATH}")