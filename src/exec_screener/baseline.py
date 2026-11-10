"""Rule-based baselines: predict the salary benchmark from the job title alone.

Any machine-learning model must beat these simple rules to justify its complexity.
The patterns are valid in both Python's `re` and DuckDB's regex engine (RE2).
"""

# Titles that name an executive role.
EXEC_TITLE_PATTERN = (
    r"(?i)\b(chief|c[etfoi]o|president|vp|svp|evp|vice president|director|head of|partner)\b"
)

# Executive titles plus common senior-professional markers.
SENIOR_TITLE_PATTERN = (
    r"(?i)\b(chief|c[etfoi]o|president|vp|svp|evp|vice president|director|head of|partner"
    r"|principal|senior|sr|lead|staff|architect|manager)\b"
)