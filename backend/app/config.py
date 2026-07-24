import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration (BACKEND_SPEC §4).

    Every external integration is optional. With no keys set, the pipeline runs against
    the local index and the deterministic LLM fallbacks, which is what the demo uses.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    octen_api_key: str | None = None
    octen_base_url: str = "https://api.octen.ai"
    octen_max_concurrency: int = 64
    octen_timeout_s: float = 10.0
    octen_cache_ttl_s: int = 900

    openai_api_key: str | None = None
    openai_model_planner: str | None = None
    openai_model_extractor: str | None = None
    openai_max_concurrency: int = 16

    composio_api_key: str | None = None
    composio_user_id: str = "founder@noviaudio.com"

    list_cap: int = 80
    min_evidence_per_investor: int = 1
    freshness_max_age_days: int = 120
    underfilled_threshold: int = 30

    sending_domain: str = "noviaudio.com"
    sending_domain_verified: bool = True

    auth_optional: bool = True
    warm_run_on_startup: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    simulate_latency: bool = True

    @property
    def octen_enabled(self) -> bool:
        return bool(self.octen_api_key)

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_model_planner and self.openai_model_extractor)

    @property
    def composio_enabled(self) -> bool:
        return bool(self.composio_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if os.environ.get("VERCEL"):
        # Serverless CPU is metered; the artificial per-query delay that makes the
        # concurrency visible locally only adds cold-start latency here.
        return settings.model_copy(update={"simulate_latency": False, "warm_run_on_startup": False})
    return settings
