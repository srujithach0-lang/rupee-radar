import re
from datetime import datetime

SKIP_PATTERNS = re.compile(r"opening balance|closing balance|total", re.I)


def parse_amount(value: str) -> float | None:
    cleaned = value.strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    if not cleaned or cleaned == "-":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%d/%m/%y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None
