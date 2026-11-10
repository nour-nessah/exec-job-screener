"""The screening model: TF-IDF text features + categorical features -> logistic regression.

Inputs follow the decisions: salary amounts stripped from text (D-006), region as a
feature (D-005), work type as a feature (D-004).
"""
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from exec_screener.text import strip_salary_amounts

CATEGORICAL_COLUMNS = ["region", "work_type", "experience"]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Model inputs: title, salary-stripped description, and categorical columns."""
    return pd.DataFrame(
        {
            "title_text": df["title"].fillna("").astype(str),
            "description_clean": [strip_salary_amounts(text) for text in df["description"].fillna("")],
            **{column: df[column].fillna("missing").astype(str) for column in CATEGORICAL_COLUMNS},
        },
        index=df.index,
    )


def build_model() -> Pipeline:
    """An untrained pipeline: feature extraction and classifier in one object."""
    features = ColumnTransformer(
        [
            ("title", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), "title_text"),
            (
                "description",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=5,
                    max_features=100_000,
                    sublinear_tf=True,
                    stop_words="english",
                ),
                "description_clean",
            ),
            ("categories", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ]
    )
    return Pipeline(
        [
            ("features", features),
            ("classifier", LogisticRegression(C=1.0, max_iter=2000)),
        ]
    )