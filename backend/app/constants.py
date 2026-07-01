"""
Project-wide conventions (implementation-plan §0.6).

- Debits are stored as negative amounts; credits as positive.
- Dates use ISO 8601 (YYYY-MM-DD).
- Categories use the fixed enum in models.enums.Category.
"""

DEBIT_SIGN = -1
CREDIT_SIGN = 1
DATE_FORMAT = "%Y-%m-%d"
