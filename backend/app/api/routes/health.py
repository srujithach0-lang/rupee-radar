from fastapi import APIRouter

from app.config import get_settings
from app.services.llm_limits import get_rate_limiter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    payload: dict = {
        "status": "ok",
        "service": "rupee-radar-api",
        "groq_configured": settings.groq_enabled,
    }
    if settings.groq_enabled:
        limiter = get_rate_limiter()
        payload["groq_limits"] = {
            # Hard quotas (from env / config)
            "rpm": settings.groq_rpm,
            "tpm": settings.groq_tpm,
            "rpd": settings.groq_rpd,
            "tpd": settings.groq_tpd,
            # Per-upload guards
            "max_txns_per_upload": settings.groq_max_txns_per_upload,
            "max_tokens_per_request": settings.groq_max_tokens_per_request,
            "upload_time_budget_sec": settings.groq_upload_time_budget_sec,
            # Live counters
            "remaining_daily_requests": limiter.remaining_daily_requests(),
            "remaining_daily_tokens": limiter.remaining_daily_tokens(),
        }
    return payload
