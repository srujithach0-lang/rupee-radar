import json
import re
import uuid
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from statistics import median

from app.models.enums import Category
from app.pipeline.cleaner import CleanedTransaction

MONTHLY_MIN_DAYS = 28
MONTHLY_MAX_DAYS = 32
AMOUNT_TOLERANCE = 0.05
MIN_OCCURRENCES = 2
SIMILARITY_THRESHOLD = 0.55


@dataclass
class RecurringGroupResult:
    id: str
    label: str
    category: str
    frequency: str
    typical_amount: float
    last_seen_date: str
    transaction_ids: list[str]
    confidence: float


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text.upper()) if len(t) > 1}


def _similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    if ta and tb:
        jaccard = len(ta & tb) / len(ta | tb)
        if jaccard >= SIMILARITY_THRESHOLD:
            return jaccard
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def _group_key(txn: CleanedTransaction) -> str:
    if txn.merchant:
        return txn.merchant.upper()
    return txn.description_clean.upper()


def _amounts_compatible(amounts: list[float]) -> bool:
    if len(amounts) < 2:
        return True
    med = median(amounts)
    if med == 0:
        return False
    return all(abs(a - med) / med <= AMOUNT_TOLERANCE for a in amounts)


def _detect_frequency(dates: list[date]) -> tuple[str, float]:
    if len(dates) < 2:
        return "unknown", 0.0

    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    monthly = sum(1 for d in intervals if MONTHLY_MIN_DAYS <= d <= MONTHLY_MAX_DAYS)
    ratio = monthly / len(intervals)

    if ratio >= 0.5:
        base = 0.45 + 0.12 * len(dates)
        return "monthly", min(0.95, base + 0.25 * ratio)

    weekly = sum(1 for d in intervals if 6 <= d <= 8)
    if weekly / len(intervals) >= 0.5:
        return "weekly", min(0.85, 0.4 + 0.1 * len(dates))

    return "unknown", 0.3


def _infer_category(label: str, txn_category: str) -> str:
    upper = label.upper()
    if re.search(r"\b(EMI|HOME LOAN)\b", upper):
        return Category.EMI.value
    if re.search(r"\b(SIP|ZERODHA|GROWW)\b", upper):
        return Category.INVESTMENTS.value
    if re.search(r"\b(NETFLIX|SPOTIFY|YOUTUBE|PRIME|SUBSCRIPTION)\b", upper):
        return Category.SUBSCRIPTIONS.value
    if re.search(r"\b(RENT|NOBROKER)\b", upper):
        return Category.RENT.value
    return txn_category


def _cluster_transactions(
    items: list[tuple[str, CleanedTransaction, Category, float]],
) -> list[list[tuple[str, CleanedTransaction, Category, float]]]:
    """Greedy clustering by description similarity."""
    clusters: list[list[tuple[str, CleanedTransaction, Category, float]]] = []
    used: set[int] = set()

    for i, item in enumerate(items):
        if i in used:
            continue
        cluster = [item]
        used.add(i)
        key_i = _group_key(item[1])

        for j, other in enumerate(items):
            if j in used or i == j:
                continue
            key_j = _group_key(other[1])
            if _similarity(key_i, key_j) >= SIMILARITY_THRESHOLD:
                cluster.append(other)
                used.add(j)

        clusters.append(cluster)

    return clusters


def detect_recurring(
    transactions: list[tuple[str, CleanedTransaction, Category, float]],
) -> list[RecurringGroupResult]:
    """Detect recurring payment groups from debit transactions."""
    debits = [(tid, txn, cat, conf) for tid, txn, cat, conf in transactions if txn.amount < 0]
    if len(debits) < MIN_OCCURRENCES:
        return []

    clusters = _cluster_transactions(debits)
    groups: list[RecurringGroupResult] = []

    for cluster in clusters:
        if len(cluster) < MIN_OCCURRENCES:
            continue

        amounts = [abs(txn.amount) for _, txn, _, _ in cluster]
        if not _amounts_compatible(amounts):
            continue

        dated = sorted(
            [(tid, txn, cat) for tid, txn, cat, _ in cluster],
            key=lambda x: date.fromisoformat(x[1].date),
        )
        dates = [date.fromisoformat(txn.date) for _, txn, _ in dated]
        frequency, freq_confidence = _detect_frequency(dates)
        if frequency == "unknown":
            continue

        label = dated[0][1].merchant or dated[0][1].description_clean
        if label and len(label.split()) == 1 and len(dated[0][1].description_clean) > len(label):
            label = dated[0][1].description_clean
        category = _infer_category(label, dated[0][2].value)
        typical = round(median(amounts), 2)
        last_date = dates[-1].isoformat()
        txn_ids = [tid for tid, _, _ in dated]

        confidence = round(min(0.95, freq_confidence + 0.05 * (len(cluster) - 2)), 2)

        groups.append(
            RecurringGroupResult(
                id=str(uuid.uuid4()),
                label=label,
                category=category,
                frequency=frequency,
                typical_amount=typical,
                last_seen_date=last_date,
                transaction_ids=txn_ids,
                confidence=confidence,
            )
        )

    return groups
