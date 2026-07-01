from datetime import date, timedelta

from app.models.enums import Category, TransactionType
from app.pipeline.cleaner import CleanedTransaction
from app.pipeline.recurring import detect_recurring


def _debit(
    txn_id: str,
    desc: str,
    amount: float,
    txn_date: str,
    category: Category = Category.SUBSCRIPTIONS,
) -> tuple[str, CleanedTransaction, Category, float]:
    return (
        txn_id,
        CleanedTransaction(
            date=txn_date,
            description_raw=desc,
            description_clean=desc.upper(),
            amount=-amount,
            type=TransactionType.DEBIT,
            balance=None,
            payment_mode="UPI",
            merchant=desc.split()[0] if desc else None,
        ),
        category,
        0.9,
    )


def test_detects_monthly_subscription_series():
    base = date(2024, 11, 9)
    txns = []
    for i in range(4):
        d = base + timedelta(days=30 * i)
        txns.append(_debit(f"t{i}", "NETFLIX INDIA", 199.0, d.isoformat()))

    groups = detect_recurring(txns)
    assert len(groups) >= 1
    netflix = next((g for g in groups if "NETFLIX" in g.label.upper()), None)
    assert netflix is not None
    assert netflix.frequency == "monthly"
    assert netflix.typical_amount == 199.0
    assert len(netflix.transaction_ids) == 4


def test_detects_monthly_emi():
    base = date(2024, 12, 8)
    txns = []
    for i in range(3):
        d = base + timedelta(days=30 * i)
        txns.append(_debit(f"e{i}", "HOME LOAN EMI HDFC", 28500.0, d.isoformat(), Category.EMI))

    groups = detect_recurring(txns)
    emi = next((g for g in groups if g.category == Category.EMI.value), None)
    assert emi is not None
    assert emi.category == Category.EMI.value
    assert emi.typical_amount == 28500.0


def test_does_not_group_one_off_similar_merchants():
    txns = [
        _debit("a", "AMAZON PAY INDIA", 4500.0, "2024-11-22"),
        _debit("b", "AMAZON PAY INDIA", 1200.0, "2024-12-15"),
    ]
    groups = detect_recurring(txns)
    amazon_groups = [g for g in groups if "AMAZON" in g.label.upper()]
    assert len(amazon_groups) == 0
