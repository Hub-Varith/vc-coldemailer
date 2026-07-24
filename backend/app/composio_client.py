import os
from functools import lru_cache

from composio import Composio


@lru_cache
def get_composio() -> Composio:
    api_key = os.environ.get("COMPOSIO_API_KEY")
    if not api_key:
        raise RuntimeError("COMPOSIO_API_KEY is not set")
    return Composio(api_key=api_key)


