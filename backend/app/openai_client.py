import os
from functools import lru_cache

from openai import AsyncOpenAI


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


@lru_cache
def get_openai() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=_require("OPENAI_API_KEY"))


def get_planner_model() -> str:
    """Larger model for the planner stage. Pinned via env, never hardcoded."""
    return _require("OPENAI_MODEL_PLANNER")


def get_extractor_model() -> str:
    """Smaller/cheaper model for the high-volume extractor stage."""
    return _require("OPENAI_MODEL_EXTRACTOR")
