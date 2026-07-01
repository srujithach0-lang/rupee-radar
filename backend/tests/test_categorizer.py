from app.models.enums import Category, TransactionType
from app.pipeline.categorizer import categorize_transaction
from app.pipeline.cleaner import CleanedTransaction


def _txn(raw: str, amount: float = -100.0) -> CleanedTransaction:
    clean = raw.upper()
    return CleanedTransaction(
        date="2025-01-01",
        description_raw=raw,
        description_clean=clean,
        amount=amount,
        type=TransactionType.DEBIT if amount < 0 else TransactionType.CREDIT,
        balance=None,
        payment_mode="UPI",
        merchant=None,
    )


def test_food_categorization():
    cat, conf = categorize_transaction(_txn("UPI/DR/SWIGGY"))
    assert cat == Category.FOOD
    assert conf >= 0.8


def test_salary_categorization():
    cat, _ = categorize_transaction(_txn("NEFT CR-SALARY ACME CORP", 90000))
    assert cat == Category.SALARY


def test_emi_categorization():
    cat, _ = categorize_transaction(_txn("HOME LOAN EMI HDFC", -28500))
    assert cat == Category.EMI


def test_investment_categorization():
    cat, _ = categorize_transaction(_txn("SIP ZERODHA BSE", -5000))
    assert cat == Category.INVESTMENTS


def test_unknown_goes_to_other():
    cat, conf = categorize_transaction(_txn("RANDOM VENDOR XYZ"))
    assert cat == Category.OTHER
    assert conf == 0.0
