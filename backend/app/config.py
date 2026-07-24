"""Application settings, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All tunable knobs for the pipeline. See .env.example for descriptions."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Octen (retrieval)
    octen_api_key: str = ""
    octen_base_url: str = "https://api.octen.ai"
    octen_max_concurrency: int = 64
    octen_timeout_s: float = 10.0
    octen_cache_ttl_s: int = 900

    # OpenAI concurrency cap for the high-volume extractor stage. The API
    # key and model names themselves are read directly from the environment
    # by app/openai_client.py (get_openai / get_planner_model / get_extractor_model),
    # which is the Composio-module owner's existing pattern -- kept here
    # only for the one knob that module doesn't cover.
    openai_max_concurrency: int = 16

    # Scoring / list rules
    list_cap: int = 80
    min_evidence_per_investor: int = 1
    freshness_max_age_days: int = 120


@lru_cache
def get_settings() -> Settings:
    """Settings are cheap to build but env parsing only needs to happen once per process."""
    return Settings()
