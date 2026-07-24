"""OpenAI structured-output helper with token accounting.

Wraps the shared client factory in `openai_client.py`. Every call site passes an explicit
JSON schema — never free-text parsing (BACKEND_SPEC §6). When no key/model is configured
the caller falls back to its deterministic path, so the pipeline always terminates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .config import get_settings

log = logging.getLogger("proofline.llm")


@dataclass
class TokenLedger:
    by_stage: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, stage: str, prompt: int, completion: int) -> None:
        bucket = self.by_stage.setdefault(stage, {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        bucket["prompt_tokens"] += prompt
        bucket["completion_tokens"] += completion
        bucket["calls"] += 1

    @property
    def prompt_tokens(self) -> int:
        return sum(b["prompt_tokens"] for b in self.by_stage.values())

    @property
    def completion_tokens(self) -> int:
        return sum(b["completion_tokens"] for b in self.by_stage.values())


LEDGER = TokenLedger()


class StructuredLLM:
    def __init__(self, stage: str, model: str | None = None, temperature: float = 0.1) -> None:
        self._settings = get_settings()
        self._stage = stage
        self._model = model
        self._temperature = temperature
        self._semaphore = asyncio.Semaphore(self._settings.openai_max_concurrency)

    @property
    def available(self) -> bool:
        return bool(self._settings.openai_api_key and self._model)

    async def complete(
        self, system: str, user: str, schema: dict[str, Any], schema_name: str = "response"
    ) -> dict[str, Any] | None:
        """Returns the parsed object, or None so the caller can use its fallback."""
        if not self.available:
            return None
        from .openai_client import get_openai

        async with self._semaphore:
            for attempt in (1, 2):
                try:
                    response = await get_openai().chat.completions.create(
                        model=self._model or "",
                        temperature=self._temperature,
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                        response_format={
                            "type": "json_schema",
                            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
                        },
                    )
                    usage = getattr(response, "usage", None)
                    LEDGER.record(
                        self._stage,
                        getattr(usage, "prompt_tokens", 0) or 0,
                        getattr(usage, "completion_tokens", 0) or 0,
                    )
                    content = response.choices[0].message.content or "{}"
                    return json.loads(content)
                except (json.JSONDecodeError, KeyError, IndexError) as exc:
                    log.warning("%s: schema violation on attempt %s (%s)", self._stage, attempt, exc)
                except Exception as exc:  # network, auth, rate limit — degrade, never poison the run
                    log.warning("%s: llm call failed (%s)", self._stage, exc)
                    return None
        return None


def planner_llm() -> StructuredLLM:
    settings = get_settings()
    return StructuredLLM("planner", settings.openai_model_planner, temperature=0.2)


def extractor_llm() -> StructuredLLM:
    settings = get_settings()
    return StructuredLLM("extractor", settings.openai_model_extractor, temperature=0.0)


def drafter_llm() -> StructuredLLM:
    settings = get_settings()
    return StructuredLLM("drafter", settings.openai_model_planner, temperature=0.6)
