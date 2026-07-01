"""Groq LLM client abstraction for categorization and insights (Phase 2+)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from groq import Groq

from app.config import Settings, get_settings
from app.models.enums import Category
from app.pipeline.cleaner import CleanedTransaction
from app.services.llm_limits import (
    GroqQuotaLimits,
    estimate_tokens,
    get_rate_limiter,
)

logger = logging.getLogger(__name__)

LLM_CONFIDENCE = 0.78
VALID_CATEGORIES = {c.value for c in Category}

# Compact system prompt to conserve the 1K TPM budget
CATEGORIZATION_SYSTEM_PROMPT = (
    "Categorize Indian bank txns. JSON only: "
    '{"transactions":[{"id":"…","category":"Food","confidence":0.8}]} '
    "Categories: Food, Travel, Shopping, Bills, EMI, Subscriptions, "
    "Salary, Rent, Investments, Other."
)


class GroqLLMService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: Groq | None = None
        if self._settings.groq_enabled:
            self._client = Groq(api_key=self._settings.groq_api_key)
        self._limiter = get_rate_limiter(
            GroqQuotaLimits(
                requests_per_minute=self._settings.groq_rpm,
                tokens_per_minute=self._settings.groq_tpm,
                requests_per_day=self._settings.groq_rpd,
                tokens_per_day=self._settings.groq_tpd,
            )
        )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _truncate_description(self, text: str) -> str:
        limit = self._settings.groq_max_description_chars
        cleaned = text.strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1] + "…"

    def _compact_payload(
        self, items: list[tuple[str, CleanedTransaction]]
    ) -> list[dict[str, str | float]]:
        return [
            {
                "id": txn_id,
                "d": self._truncate_description(txn.description_clean),
                "a": txn.amount,
                "t": txn.type.value[0],  # "d" or "c"
            }
            for txn_id, txn in items
        ]

    def estimate_request_tokens(self, user_prompt: str) -> int:
        return estimate_tokens(CATEGORIZATION_SYSTEM_PROMPT, user_prompt) + 40

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        deadline: float | None = None,
        max_output_tokens: int = 120,
    ) -> dict[str, Any] | list[Any] | None:
        """Return parsed JSON from Groq chat completion, or None on failure/limit."""
        if not self._client:
            return None

        estimated = (
            self.estimate_request_tokens(user_prompt)
            if system_prompt == CATEGORIZATION_SYSTEM_PROMPT
            else estimate_tokens(system_prompt, user_prompt) + max_output_tokens
        )

        if not self._limiter.acquire(estimated, deadline=deadline):
            logger.warning("Skipping Groq request: rate limit or time budget exceeded")
            return None

        try:
            response = self._client.chat.completions.create(
                model=self._settings.groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=max_output_tokens,
            )
            usage = response.usage
            if usage and usage.total_tokens:
                self._limiter.record(usage.total_tokens)
            else:
                self._limiter.record(estimated)

            content = response.choices[0].message.content
            if not content:
                return None
            return json.loads(content)
        except Exception:
            logger.exception("Groq completion failed")
            return None

    def categorize_batch(
        self,
        items: list[tuple[str, CleanedTransaction]],
        *,
        deadline: float | None = None,
    ) -> dict[str, tuple[Category, float]]:
        """Categorize a batch of transactions. Returns {txn_id: (category, confidence)}."""
        if not items or not self._client:
            return {}

        user_prompt = json.dumps({"transactions": self._compact_payload(items)}, separators=(",", ":"))
        raw = self.complete_json(CATEGORIZATION_SYSTEM_PROMPT, user_prompt, deadline=deadline)
        return parse_categorization_response(raw)


def parse_categorization_response(
    raw: dict[str, Any] | list[Any] | None,
) -> dict[str, tuple[Category, float]]:
    """Parse and validate LLM categorization JSON."""
    if not raw or not isinstance(raw, dict):
        return {}

    entries = raw.get("transactions", raw.get("results", []))
    if not isinstance(entries, list):
        return {}

    results: dict[str, tuple[Category, float]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        txn_id = entry.get("id")
        category_str = entry.get("category", "Other")
        confidence = entry.get("confidence", LLM_CONFIDENCE)

        if not txn_id or not isinstance(txn_id, str):
            continue
        if category_str not in VALID_CATEGORIES:
            category_str = Category.OTHER.value
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = LLM_CONFIDENCE

        results[txn_id] = (Category(category_str), confidence)

    return results


def _build_token_aware_batches(
    items: list[tuple[str, CleanedTransaction]],
    settings: Settings,
    service: GroqLLMService,
) -> list[list[tuple[str, CleanedTransaction]]]:
    """Split unmatched txns into batches that fit per-request and TPM budgets."""
    if not items:
        return []

    max_per_request = settings.groq_max_tokens_per_request
    base_tokens = service.estimate_request_tokens('{"transactions":[]}')

    batches: list[list[tuple[str, CleanedTransaction]]] = []
    current: list[tuple[str, CleanedTransaction]] = []
    current_tokens = base_tokens

    for item in items:
        sample = json.dumps(
            {"transactions": service._compact_payload([item])},
            separators=(",", ":"),
        )
        item_tokens = service.estimate_request_tokens(sample) - base_tokens + 8

        if current and current_tokens + item_tokens > max_per_request:
            batches.append(current)
            current = []
            current_tokens = base_tokens

        current.append(item)
        current_tokens += item_tokens

    if current:
        batches.append(current)

    return batches


def categorize_with_llm(
    unmatched: list[tuple[str, CleanedTransaction]],
    llm: GroqLLMService | None = None,
) -> dict[str, tuple[Category, float]]:
    """Send unmatched transactions to LLM in token-aware batches within Groq quotas."""
    service = llm or get_llm_service()
    settings = service._settings
    if not service.enabled or not unmatched:
        return {}

    max_txns = settings.groq_max_txns_per_upload
    if len(unmatched) > max_txns:
        logger.info(
            "LLM categorization capped at %d/%d unmatched txns (groq_max_txns_per_upload)",
            max_txns,
            len(unmatched),
        )
        unmatched = unmatched[:max_txns]

    deadline = time.monotonic() + settings.groq_upload_time_budget_sec
    batches = _build_token_aware_batches(unmatched, settings, service)

    all_results: dict[str, tuple[Category, float]] = {}
    for batch in batches:
        if time.monotonic() >= deadline:
            logger.warning(
                "LLM categorization stopped: upload time budget (%ds) exceeded",
                settings.groq_upload_time_budget_sec,
            )
            break

        batch_results = service.categorize_batch(batch, deadline=deadline)
        all_results.update(batch_results)

    skipped = len(unmatched) - len(all_results)
    if skipped > 0:
        logger.info(
            "LLM categorized %d/%d unmatched txns; %d left as Other (limits/budget)",
            len(all_results),
            len(unmatched),
            skipped,
        )

    return all_results


def get_llm_service() -> GroqLLMService:
    return GroqLLMService()


NARRATIVE_SYSTEM_PROMPT = (
    "You are a personal finance analyst for Indian bank statements. "
    'Return JSON only: {"insights":["observation 1","observation 2"]}. '
    "Write 2-3 short, actionable observations using only the aggregate metrics provided. "
    "Reference real amounts and category names. No account numbers or personal names."
)


def _build_narrative_payload(
    metrics: "MetricsResult",
    recurring_groups: list | None,
) -> dict:
    from app.pipeline.metrics import MetricsResult

    payload: dict = {
        "total_income": round(metrics.total_income, 2),
        "total_spend": round(metrics.total_spend, 2),
        "savings": round(metrics.savings, 2),
        "savings_rate": metrics.savings_rate,
        "top_categories": [
            {"category": c.category, "amount": round(c.amount, 2)} for c in metrics.top_categories[:5]
        ],
        "recurring_monthly_total": round(metrics.recurring_total_monthly, 2),
        "recurring_count": len([g for g in (recurring_groups or []) if g.frequency == "monthly"]),
        "period_start": metrics.period_start,
        "period_end": metrics.period_end,
    }
    return payload


def parse_narrative_response(raw: dict[str, Any] | list[Any] | None) -> list[str]:
    if not raw or not isinstance(raw, dict):
        return []
    entries = raw.get("insights", [])
    if not isinstance(entries, list):
        return []
    results: list[str] = []
    for entry in entries:
        if isinstance(entry, str) and entry.strip():
            results.append(entry.strip())
        elif isinstance(entry, dict) and entry.get("text"):
            results.append(str(entry["text"]).strip())
    return results[:3]


def generate_narrative_insights(
    metrics: "MetricsResult",
    recurring_groups: list | None = None,
    llm: GroqLLMService | None = None,
) -> list["InsightItem"]:
    from app.pipeline.insight_types import InsightItem

    service = llm or get_llm_service()
    if not service.enabled:
        return []

    # Check remaining daily token budget before attempting the narrative call.
    # Narrative needs ~300 tokens (150 prompt + 150 output).  Skip if budget
    # is too low to avoid burning the last tokens on insights instead of
    # categorization on future uploads.
    NARRATIVE_TOKEN_ESTIMATE = 300
    if service._limiter.remaining_daily_tokens() < NARRATIVE_TOKEN_ESTIMATE:
        logger.info(
            "Skipping narrative insights: only %d daily tokens remaining (need %d)",
            service._limiter.remaining_daily_tokens(),
            NARRATIVE_TOKEN_ESTIMATE,
        )
        return []

    user_prompt = json.dumps(_build_narrative_payload(metrics, recurring_groups), separators=(",", ":"))

    # Give the narrative call a short deadline so it doesn't block the upload
    # response if the TPM window is exhausted.
    deadline = time.monotonic() + 15.0  # max 15 s wait for narrative

    raw = service.complete_json(
        NARRATIVE_SYSTEM_PROMPT,
        user_prompt,
        deadline=deadline,
        max_output_tokens=200,  # enough for 2-3 sentences
    )
    texts = parse_narrative_response(raw)
    return [InsightItem(text=text, source="ai") for text in texts[:3]]
