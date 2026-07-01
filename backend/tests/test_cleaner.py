from app.models.enums import TransactionType
from app.parsers.base import RawTransaction
from app.pipeline.cleaner import clean_description, clean_transactions


def test_clean_upi_swiggy():
    clean, merchant = clean_description("UPI/DR/123456/SWIGGY")
    assert "SWIGGY" in clean
    assert merchant == "SWIGGY"


def test_clean_transactions_deduplicates():
    raw = [
        RawTransaction("2025-01-01", "SWIGGY", -100.0, TransactionType.DEBIT),
        RawTransaction("2025-01-01", "SWIGGY", -100.0, TransactionType.DEBIT),
        RawTransaction("2025-01-02", "ZOMATO", -200.0, TransactionType.DEBIT),
    ]
    cleaned, warnings = clean_transactions(raw)
    assert len(cleaned) == 2
    assert any("Duplicate" in w for w in warnings)


def test_messy_descriptions():
    samples = [
        "UPI/DR/482910/SWIGGY/BANGALORE",
        "UPI-SWIGGY-INSTAMART",
        "NEFT CR-SALARY ACME CORP",
        "HOME LOAN EMI HDFC",
        "NETFLIX COM",
    ]
    for sample in samples:
        clean, _ = clean_description(sample)
        assert clean
        assert clean != ""
