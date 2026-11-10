"""Interactive demo: screen one job posting against the $100k benchmark.

Run from the project root:
    streamlit run app/streamlit_app.py
"""
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from exec_screener.explain import explain
from exec_screener.routing import ACCEPT, REVIEW

MODEL_PATH = Path("models/model.joblib")
THRESHOLDS_PATH = Path("models/thresholds.json")
REGIONS = ["other US state", "pay-transparency state", "state unknown"]
WORK_TYPES = ["FULL_TIME", "PART_TIME", "CONTRACT", "TEMPORARY", "INTERNSHIP", "VOLUNTEER", "OTHER"]
EXPERIENCE = ["missing", "Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"]
TOP_N = 8

EXAMPLES = {
    "Vice President of Finance": {
        "title": "Vice President of Finance",
        "description": "Lead our finance team. 10 years of experience in corporate finance required. Reports to the CFO.",
        "region": "other US state", "work_type": "FULL_TIME", "experience": "Executive",
    },
    "Software Engineer": {
        "title": "Software Engineer",
        "description": "Build backend services in Python and Go. 3+ years of experience.",
        "region": "pay-transparency state", "work_type": "FULL_TIME", "experience": "Mid-Senior level",
    },
    "Customer Service Representative": {
        "title": "Customer Service Representative",
        "description": "Assist customers by phone and email. High school diploma required.",
        "region": "other US state", "work_type": "FULL_TIME", "experience": "Entry level",
    },
    "(write your own)": {
        "title": "", "description": "",
        "region": "other US state", "work_type": "FULL_TIME", "experience": "missing",
    },
}


@st.cache_resource
def load_model():
    """Load the model and thresholds once, not on every rerun."""
    return joblib.load(MODEL_PATH), pd.read_json(THRESHOLDS_PATH, typ="series")


def contribution_table(rows: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Source": rows["source"],
            "Word or feature": rows["feature"],
            "Contribution": rows["contribution"].round(2),
        }
    )


st.set_page_config(page_title="Executive Job Screener", page_icon="📊", layout="centered")
st.title("Executive Job Screener")
st.caption(
    "Estimates whether a job posting pays at least $100k (full-time equivalent), even when no "
    "salary is stated. Trained on 35,573 LinkedIn postings (2023–2024) and evaluated on "
    "companies it never saw."
)

if not MODEL_PATH.exists() or not THRESHOLDS_PATH.exists():
    st.error("Model not found. Run `python scripts/train_model.py` and `python scripts/evaluate_routing.py` first.")
    st.stop()

model, thresholds = load_model()

# --- Inputs --------------------------------------------------------------------
example = EXAMPLES[st.selectbox("Start from an example", list(EXAMPLES))]
title = st.text_input("Job title", value=example["title"])
description = st.text_area("Job description", value=example["description"], height=160)
col1, col2, col3 = st.columns(3)
region = col1.selectbox("Region", REGIONS, index=REGIONS.index(example["region"]))
work_type = col2.selectbox("Work type", WORK_TYPES, index=WORK_TYPES.index(example["work_type"]))
experience = col3.selectbox("Experience level", EXPERIENCE, index=EXPERIENCE.index(example["experience"]))

if not title.strip():
    st.info("Enter at least a job title.")
    st.stop()

# --- Result --------------------------------------------------------------------
posting = {
    "title": title,
    "description": description,
    "region": region,
    "work_type": work_type,
    "experience": experience,
}
result = explain(model, posting, thresholds["t_low"], thresholds["t_high"])

left, right = st.columns(2)
left.metric("Probability of ≥ $100k", f"{result.probability:.1%}")
show_queue = {ACCEPT: right.success, REVIEW: right.warning}.get(result.queue, right.info)
show_queue(f"**{result.queue.capitalize()}**")
st.caption(
    f"Auto-reject ≤ {thresholds['t_low']:.0%} · human review in between · "
    f"auto-accept ≥ {thresholds['t_high']:.0%}. Each automatic decision was at least 95% "
    "accurate on companies the model never saw."
)

up = result.contributions[result.contributions["contribution"] > 0].head(TOP_N)
down = result.contributions[result.contributions["contribution"] < 0].head(TOP_N)
col_up, col_down = st.columns(2)
col_up.subheader("Pushing up")
col_up.dataframe(contribution_table(up), hide_index=True)
col_down.subheader("Pushing down")
col_down.dataframe(contribution_table(down), hide_index=True)

st.caption(
    "Contributions are exact for this model: intercept + sum of all contributions = the "
    "model's log-odds. Salary amounts in the text are removed before scoring."
)