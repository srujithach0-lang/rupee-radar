import json
import re
from pathlib import Path

from app.models.enums import Category
from app.pipeline.cleaner import CleanedTransaction
from app.services.llm import categorize_with_llm, get_llm_service

RULE_CONFIDENCE = 0.92
DICT_CONFIDENCE = 0.85
DEFAULT_CONFIDENCE = 0.0

CATEGORY_RULES: list[tuple[re.Pattern[str], Category]] = [
    (re.compile(r"\b(SALARY|PAYROLL)\b", re.I), Category.SALARY),
    (re.compile(r"\b(FREELANCE|CONSULTING)\b", re.I), Category.SALARY),
    (re.compile(r"\b(SWIGGY|ZOMATO|DOMINOS|STARBUCKS|BIGBASKET|INSTAMART|UBER EATS)\b", re.I), Category.FOOD),
    (re.compile(r"\b(UBER|OLA|IRCTC|MAKEMYTRIP)\b", re.I), Category.TRAVEL),
    (re.compile(r"\b(AMAZON|FLIPKART|MYNTRA)\b", re.I), Category.SHOPPING),
    (re.compile(r"\b(AIRTEL|JIO|BESCOM|LIC|SMS CHARGES)\b", re.I), Category.BILLS),
    (re.compile(r"\b(NETFLIX|SPOTIFY|YOUTUBE PREMIUM|AMAZON PRIME)\b", re.I), Category.SUBSCRIPTIONS),
    (re.compile(r"\b(HOME LOAN|EMI)\b", re.I), Category.EMI),
    (re.compile(r"\b(RENT|NOBROKER)\b", re.I), Category.RENT),
    (re.compile(r"\b(ZERODHA|GROWW|SIP|REDEMPTION)\b", re.I), Category.INVESTMENTS),
    (re.compile(r"\bCASHBACK\b", re.I), Category.SHOPPING),
]


def _load_merchant_categories() -> list[tuple[str, Category]]:
    path = Path(__file__).resolve().parent.parent / "data" / "merchants.json"
    with path.open() as f:
        merchants = json.load(f)["merchants"]
    mapping: list[tuple[str, Category]] = []
    for name, info in merchants.items():
        cat = Category(info["category"])
        mapping.append((name, cat))
        for alias in info.get("aliases", []):
            mapping.append((alias, cat))
    mapping.sort(key=lambda x: len(x[0]), reverse=True)
    return mapping


def categorize_transaction(txn: CleanedTransaction) -> tuple[Category, float]:
    text = f"{txn.description_raw} {txn.description_clean}".upper()

    for pattern, category in CATEGORY_RULES:
        if pattern.search(text):
            return category, RULE_CONFIDENCE

    for keyword, category in _load_merchant_categories():
        if keyword in text:
            return category, DICT_CONFIDENCE

    if txn.type.value == "credit":
        if re.search(r"\bSALARY\b", text):
            return Category.SALARY, RULE_CONFIDENCE
        if re.search(r"\bREDEMPTION\b", text):
            return Category.INVESTMENTS, DICT_CONFIDENCE

    return Category.OTHER, DEFAULT_CONFIDENCE


def categorize_transactions(
    transactions: list[CleanedTransaction],
    txn_ids: list[str] | None = None,
) -> list[tuple[CleanedTransaction, Category, float]]:
    """Categorize transactions: rules → dictionary → LLM → Other."""
    results: list[tuple[CleanedTransaction, Category, float]] = []
    unmatched: list[tuple[str, CleanedTransaction]] = []

    for i, txn in enumerate(transactions):
        category, confidence = categorize_transaction(txn)
        results.append((txn, category, confidence))
        if category == Category.OTHER and confidence == DEFAULT_CONFIDENCE:
            txn_id = txn_ids[i] if txn_ids and i < len(txn_ids) else str(i)
            unmatched.append((txn_id, txn))

    if unmatched:
        llm_results = categorize_with_llm(unmatched, get_llm_service())
        for i, (txn, category, confidence) in enumerate(results):
            if category != Category.OTHER or confidence != DEFAULT_CONFIDENCE:
                continue
            txn_id = txn_ids[i] if txn_ids and i < len(txn_ids) else str(i)
            if txn_id in llm_results:
                llm_cat, llm_conf = llm_results[txn_id]
                results[i] = (txn, llm_cat, llm_conf)

    return results
