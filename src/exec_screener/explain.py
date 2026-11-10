"""Score ONE posting and explain the decision: probability, queue and the words that drove it.

For logistic regression the explanation is exact: the log-odds of a posting are the intercept
plus the sum, over its features, of (feature value x learned weight). Each term is that
feature's contribution.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from exec_screener.model import prepare_features
from exec_screener.routing import route


@dataclass
class Explanation:
    probability: float
    queue: str
    contributions: pd.DataFrame  # columns: source, feature, contribution (sorted, largest first)
    intercept: float


def explain(model, posting: dict, t_low: float, t_high: float) -> Explanation:
    """posting: dict with title, description, region, work_type, experience."""
    X = prepare_features(pd.DataFrame([posting]))
    probability = float(model.predict_proba(X)[0, 1])

    features = model.named_steps["features"]
    classifier = model.named_steps["classifier"]
    row = features.transform(X).tocsr()            # 1 x n_features, mostly zeros
    names = features.get_feature_names_out()
    weights = classifier.coef_[0]

    active = row.indices                           # only features present in this posting
    values = row.data * weights[active]
    sources, terms = zip(*(name.split("__", 1) for name in names[active])) if len(active) else ((), ())
    contributions = (
        pd.DataFrame({"source": sources, "feature": terms, "contribution": values})
        .sort_values("contribution", ascending=False, key=np.abs)
        .reset_index(drop=True)
    )
    queue = str(route([probability], t_low, t_high)[0])
    return Explanation(probability, queue, contributions, float(classifier.intercept_[0]))