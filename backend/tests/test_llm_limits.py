"""Tests for Groq rate limiting and token-aware batching."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.models.enums import Category, TransactionType
from app.pipeline.cleaner import CleanedTransaction
from app.services.llm import GroqLLMService, _build_token_aware_batches, categorize_with_llm
from app.services.llm_limits import GroqQuotaLimits, GroqRateLimiter, reset_rate_limiter_for_tests


@pytest.fixture(autouse=True)
def _reset_limiter():
    reset_rate_limiter_for_tests()
    yield
    reset_rate_limiter_for_tests()


def _txn(desc: str) -> CleanedTransaction:
    return CleanedTransaction(
        date="2025-01-01",
        description_raw=desc,
        description_clean=desc.upper(),
        amount=-100.0,
        type=TransactionType.DEBIT,
        balance=None,
        payment_mode="UPI",
        merchant=None,
    )


def test_rate_limiter_enforces_tokens_per_minute():
    limits = GroqQuotaLimits(tokens_per_minute=100)
    limiter = GroqRateLimiter(limits)

    limiter.record(60)
    assert limiter.can_acquire(50) is False
    assert limiter.can_acquire(40) is True


def test_rate_limiter_enforces_requests_per_minute():
    limits = GroqQuotaLimits(requests_per_minute=2, tokens_per_minute=10_000)
    limiter = GroqRateLimiter(limits)

    limiter.record(10)
    limiter.record(10)
    assert limiter.can_acquire(10) is False


def test_rate_limiter_enforces_daily_token_cap():
    limits = GroqQuotaLimits(tokens_per_day=200)
    limiter = GroqRateLimiter(limits)

    limiter.record(150)
    assert limiter.acquire(60) is False
    assert limiter.remaining_daily_tokens() == 50


def test_rate_limiter_window_resets_after_minute():
    limits = GroqQuotaLimits(tokens_per_minute=100)
    limiter = GroqRateLimiter(limits)

    limiter.record(90)
    assert limiter.can_acquire(20) is False

    limiter._minute_window[0] = (time.monotonic() - 61.0, 90)
    assert limiter.can_acquire(20) is True


def test_token_aware_batches_stay_under_per_request_cap():
    settings = Settings(groq_max_tokens_per_request=200, groq_max_description_chars=48)
    service = GroqLLMService(settings)

    items = [(f"id-{i}", _txn(f"VENDOR NUMBER {i} LONG DESCRIPTION TEXT")) for i in range(20)]
    batches = _build_token_aware_batches(items, settings, service)

    assert len(batches) > 1
    for batch in batches:
        prompt = __import__("json").dumps(
            {"transactions": service._compact_payload(batch)},
            separators=(",", ":"),
        )
        assert service.estimate_request_tokens(prompt) <= settings.groq_max_tokens_per_request + 20


@patch.object(GroqLLMService, "categorize_batch")
def test_categorize_with_llm_caps_unmatched_count(mock_batch):
    mock_batch.return_value = {"id-0": (Category.FOOD, 0.8)}
    settings = Settings(
        groq_api_key="test-key",
        groq_max_txns_per_upload=3,
        groq_upload_time_budget_sec=10,
    )
    service = GroqLLMService(settings)

    unmatched = [(f"id-{i}", _txn(f"UNKNOWN {i}")) for i in range(10)]
    categorize_with_llm(unmatched, service)

    total_sent = sum(len(call.args[0]) for call in mock_batch.call_args_list)
    assert total_sent <= 3


@patch.object(GroqLLMService, "categorize_batch")
def test_categorize_with_llm_stops_on_time_budget(mock_batch):
    mock_batch.side_effect = lambda batch, **_: (
        time.sleep(0.05),
        {batch[0][0]: (Category.FOOD, 0.8)},
    )[1]

    settings = Settings(
        groq_api_key="test-key",
        groq_max_txns_per_upload=50,
        groq_upload_time_budget_sec=0,
        groq_max_tokens_per_request=500,
    )
    service = GroqLLMService(settings)
    unmatched = [(f"id-{i}", _txn(f"UNKNOWN {i}")) for i in range(8)]

    results = categorize_with_llm(unmatched, service)
    assert mock_batch.call_count == 0
    assert results == {}
