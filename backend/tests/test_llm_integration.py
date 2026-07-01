from unittest.mock import MagicMock, patch

from app.models.enums import Category, TransactionType
from app.pipeline.categorizer import categorize_transactions
from app.pipeline.cleaner import CleanedTransaction


def _txn(raw: str, amount: float = -100.0) -> CleanedTransaction:
    return CleanedTransaction(
        date="2025-01-01",
        description_raw=raw,
        description_clean=raw.upper(),
        amount=amount,
        type=TransactionType.DEBIT if amount < 0 else TransactionType.CREDIT,
        balance=None,
        payment_mode="UPI",
        merchant=None,
    )


@patch("app.pipeline.categorizer.get_llm_service")
def test_llm_fallback_categorizes_unmatched(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.enabled = True
    mock_get_llm.return_value = mock_llm

    txns = [_txn("RANDOM VENDOR XYZ"), _txn("UPI/DR/SWIGGY")]
    ids = ["id-1", "id-2"]

    with patch("app.pipeline.categorizer.categorize_with_llm") as mock_llm_cat:
        mock_llm_cat.return_value = {"id-1": (Category.FOOD, 0.8)}
        results = categorize_transactions(txns, ids)

    assert results[0][1] == Category.FOOD
    assert results[0][2] == 0.8
    assert results[1][1] == Category.FOOD
    assert results[1][2] >= 0.8


@patch("app.pipeline.categorizer.get_llm_service")
def test_pipeline_completes_without_llm(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.enabled = False
    mock_get_llm.return_value = mock_llm

    txns = [_txn("OBSCURE MERCHANT ABC")]
    results = categorize_transactions(txns, ["id-1"])
    assert results[0][1] == Category.OTHER
    assert results[0][2] == 0.0
