"""Review routing: turn probabilities into auto-accept / human review / auto-reject (D-011).

Thresholds are chosen so that every AUTOMATIC decision meets a target accuracy; everything
the model is unsure about goes to a person.
"""
import numpy as np

ACCEPT, REVIEW, REJECT = "auto-accept", "human review", "auto-reject"


def choose_thresholds(probability, truth, target: float = 0.95):
    """Return (t_low, t_high) such that, on the given data,
    - postings with probability >= t_high are >= target precise (truly >= $100k), and
    - postings with probability <= t_low are >= target truly below $100k,
    each pile as large as possible."""
    probability = np.asarray(probability, dtype=float)
    truth = np.asarray(truth, dtype=bool)

    # Auto-accept pile: most confident positives first; keep the largest top-k that meets the target.
    order = np.argsort(-probability, kind="stable")
    precision_top_k = np.cumsum(truth[order]) / np.arange(1, len(order) + 1)
    ok = np.flatnonzero(precision_top_k >= target)
    t_high = probability[order[ok[-1]]] if len(ok) else np.inf

    # Auto-reject pile: most confident negatives first; same idea for "truly below $100k".
    order = np.argsort(probability, kind="stable")
    negative_share_bottom_k = np.cumsum(~truth[order]) / np.arange(1, len(order) + 1)
    ok = np.flatnonzero(negative_share_bottom_k >= target)
    t_low = probability[order[ok[-1]]] if len(ok) else -np.inf

    return float(t_low), float(t_high)


def route(probability, t_low: float, t_high: float) -> np.ndarray:
    """Assign each posting to one of the three queues."""
    probability = np.asarray(probability, dtype=float)
    return np.where(probability >= t_high, ACCEPT, np.where(probability <= t_low, REJECT, REVIEW))