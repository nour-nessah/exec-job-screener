"""Text cleaning shared by all models.

D-006: remove money amounts from job descriptions before modelling, so a model cannot
"read the answer" (target leakage). We deliberately over-strip: removing a harmless number
costs little, leaving a salary in the text inflates every evaluation metric.
"""
import re

SALARY_AMOUNT_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?[kKmM]\b)?"  # $150,000  $25.50  $150k  $1.2M
    r"|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?"          # 170,000.00 (range end without $)
    r"|\b\d+(?:\.\d+)?\s?[kK]\b"                # 150k  95.5K  (without $)
)

# Patterns used to MEASURE leakage (Step 2.2a). They are valid in both Python's `re`
# and DuckDB's regex engine (RE2), so the same strings work in Python and in SQL.
LEAKAGE_PATTERNS = {
    "dollar amount ($ + digit)": r"\$\s?\d",
    "yearly-style amount": r"\$\s?\d{2,3},\d{3}|\$\s?\d{2,3}(\.\d+)?\s?[kK]\b",
    "hourly-style amount": r"(?i)\$\s?\d{1,3}(\.\d{2})?\s*(/|per)\s*(hour|hr)\b",
}


def strip_salary_amounts(text: str | None) -> str:
    """Replace every money-like amount in the text with a single space."""
    if text is None:
        return ""
    return SALARY_AMOUNT_RE.sub(" ", text)