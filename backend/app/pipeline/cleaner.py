import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models.enums import TransactionType
from app.parsers.base import RawTransaction

UPI_NOISE = re.compile(
    r"^(UPI[/-]|UPI\s|IMPS[/-]|NEFT[/-]|RTGS[/-]|VPA[/-])",
    re.I,
)
UPI_DR_CR = re.compile(r"UPI/(DR|CR)/\d+/", re.I)
UPI_SLASH = re.compile(r"UPI/DR/\d+/", re.I)
NON_ALPHA = re.compile(r"[^A-Z0-9\s]")
MULTI_SPACE = re.compile(r"\s+")

PAYMENT_MODES = {
    "UPI": re.compile(r"\bUPI\b", re.I),
    "NEFT": re.compile(r"\bNEFT\b", re.I),
    "IMPS": re.compile(r"\bIMPS\b", re.I),
    "RTGS": re.compile(r"\bRTGS\b", re.I),
    "ATM": re.compile(r"\bATM\b", re.I),
    "CARD": re.compile(r"\bCARD\b|\bPOS\b", re.I),
}


@dataclass
class CleanedTransaction:
    date: str
    description_raw: str
    description_clean: str
    amount: float
    type: TransactionType
    balance: float | None
    payment_mode: str | None
    merchant: str | None
    is_duplicate: bool = False


def _load_merchants() -> dict[str, dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "merchants.json"
    with path.open() as f:
        return json.load(f)["merchants"]


def normalize_date(value: str) -> str | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def detect_payment_mode(description: str) -> str | None:
    for mode, pattern in PAYMENT_MODES.items():
        if pattern.search(description):
            return mode
    return None


def extract_merchant(description_upper: str, merchants: dict[str, dict]) -> str | None:
    for merchant, info in merchants.items():
        aliases = [merchant] + info.get("aliases", [])
        for alias in aliases:
            if alias in description_upper:
                return merchant if merchant != "SIP" else alias.split()[0] if " " in alias else merchant
    return None


def clean_description(raw: str, merchants: dict[str, dict] | None = None) -> tuple[str, str | None]:
    merchants = merchants or _load_merchants()
    text = raw.strip()
    upper = text.upper()

    # Strip common UPI patterns
    text = UPI_DR_CR.sub("", text)
    text = UPI_SLASH.sub("", text)
    text = UPI_NOISE.sub("", text)

    # Take last meaningful segment from slash-separated UPI strings
    if "/" in raw:
        parts = [p.strip() for p in raw.split("/") if p.strip() and not p.strip().isdigit()]
        if parts:
            candidate = parts[-1]
            if len(candidate) > 2 and not candidate.isdigit():
                text = candidate

    cleaned = MULTI_SPACE.sub(" ", NON_ALPHA.sub(" ", text.upper())).strip()
    if not cleaned:
        cleaned = "UNKNOWN"

    merchant = extract_merchant(cleaned, merchants) or extract_merchant(upper, merchants)
    if merchant:
        cleaned = merchant

    return cleaned, merchant


def _txn_hash(txn: RawTransaction) -> str:
    key = f"{txn.date}|{txn.amount}|{txn.description_raw}"
    return hashlib.md5(key.encode()).hexdigest()


def clean_transactions(
    raw_transactions: list[RawTransaction],
) -> tuple[list[CleanedTransaction], list[str]]:
    merchants = _load_merchants()
    seen: set[str] = set()
    cleaned: list[CleanedTransaction] = []
    warnings: list[str] = []

    for txn in raw_transactions:
        h = _txn_hash(txn)
        is_dup = h in seen
        if is_dup:
            warnings.append(f"Duplicate skipped: {txn.description_raw[:50]} on {txn.date}")
            continue
        seen.add(h)

        iso_date = normalize_date(txn.date) or txn.date
        desc_clean, merchant = clean_description(txn.description_raw, merchants)
        mode = detect_payment_mode(txn.description_raw)

        cleaned.append(
            CleanedTransaction(
                date=iso_date,
                description_raw=txn.description_raw,
                description_clean=desc_clean,
                amount=txn.amount,
                type=txn.type,
                balance=txn.balance,
                payment_mode=mode,
                merchant=merchant,
                is_duplicate=False,
            )
        )

    return cleaned, warnings
