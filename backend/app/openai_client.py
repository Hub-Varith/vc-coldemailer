import os
from functools import lru_cache

from openai import AsyncOpenAI


@lru_cache
def get_openai() -> AsyncOpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return AsyncOpenAI(api_key=api_key)


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5.5")
