"""Stage 2: turn a CompanyProfile into a SearchPlan.

The planner's whole job is breadth. A plan with 10 queries means a
conventional search API would have been enough and Octen's high-concurrency
fan-out has no reason to exist -- so the prompt below pushes hard for
150-400 narrow, concrete queries spread across every intent kind.
"""

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.models import CompanyProfile, SearchIntent, SearchPlan
from app.openai_client import get_openai, get_planner_model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a search-strategy planner for an investor-targeting tool. Given a \
company profile, produce a set of search intents that together cover every \
angle an investor researcher would use to find funds likely to invest in \
this specific company, right now.

For each intent, write 5-30 concrete, narrow query strings: firm names, \
company names, specific category phrases. Do NOT write broad queries like \
"seed investors medtech" -- broad queries return the same generic results \
hundreds of times and waste the retrieval budget. Prefer queries like \
"[specific fund] portfolio hearing aid" or "bone conduction startup seed \
round 2026".

Aim for 150-400 total queries spread across all six intent kinds:
adjacent_portfolio, thesis_signal, fund_activity, geo_crossing, \
portfolio_gap, recent_exit.
"""


class _PlanSchema(BaseModel):
    """What we ask the model for. profile_id is attached afterward -- the
    model has no business inventing an ID."""

    intents: list[SearchIntent]


# --- public API ---


async def build_search_plan(profile: CompanyProfile, client: AsyncOpenAI | None = None) -> SearchPlan:
    """Call OpenAI once to turn a company profile into a structured search plan."""
    logger.info("planning search for profile=%s sector=%s stage=%s", profile.id, profile.sector, profile.stage)

    openai_client = client or get_openai()
    response = await openai_client.chat.completions.parse(
        model=get_planner_model(),
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": profile.model_dump_json()},
        ],
        response_format=_PlanSchema,
    )

    parsed = response.choices[0].message.parsed
    assert parsed is not None  # response_format guarantees this or the SDK raises
    plan = SearchPlan(profile_id=profile.id, intents=parsed.intents)

    logger.info("plan built for profile=%s: %d intents, %d total queries", profile.id, len(plan.intents), plan.query_count)
    return plan
