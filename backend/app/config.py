from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/rupee_radar.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_size_mb: int = 10
    session_ttl_hours: int = 72

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Groq llama-3.3-70b-versatile free-tier limits (override if your tier differs)
    groq_rpm: int = 30
    groq_tpm: int = 1000
    groq_rpd: int = 12000
    groq_tpd: int = 100000

    # Phase 2 LLM categorization guards (tuned for 1K TPM)
    groq_max_tokens_per_request: int = 350
    groq_max_txns_per_upload: int = 15
    groq_upload_time_budget_sec: int = 45
    groq_max_description_chars: int = 48

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        # Railway and other hosts often provide postgres://; SQLAlchemy 2 expects postgresql://
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def groq_enabled(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
