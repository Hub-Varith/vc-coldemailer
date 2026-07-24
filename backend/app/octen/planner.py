"""Profile → SearchPlan (BACKEND_SPEC §5.3).

The planner's job is breadth: 150–400 narrow queries across six intent kinds. Narrow
matters — broad queries return the same generic results three hundred times.
"""

from __future__ import annotations

import logging
from itertools import product

from ..llm import planner_llm
from ..models import CompanyProfile, IntentKind, SearchIntent, SearchPlan

log = logging.getLogger("proofline.octen.planner")

SYSTEM = (
    "You plan investor research. Given a company profile, emit narrow, specific search queries "
    "(firm names, portfolio company names, category phrases, event language). Never emit broad "
    "queries like 'seed investors'. Aim for 150-400 queries total across the six intent kinds."
)

PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["intents"],
    "properties": {
        "intents": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "rationale", "queries", "domain_hints", "recency_days"],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "adjacent_portfolio",
                            "thesis_signal",
                            "fund_activity",
                            "geo_crossing",
                            "portfolio_gap",
                            "recent_exit",
                        ],
                    },
                    "rationale": {"type": "string"},
                    "queries": {"type": "array", "items": {"type": "string"}},
                    "domain_hints": {"type": "array", "items": {"type": "string"}},
                    "recency_days": {"type": ["integer", "null"]},
                },
            },
        }
    },
}

_ADJACENT_MODIFIERS = (
    "seed round",
    "pre-seed round",
    "led the round",
    "portfolio company",
    "investor backing",
    "raises funding",
)
_THESIS_MODIFIERS = (
    "partner thesis",
    "essay",
    "podcast interview",
    "conference keynote",
    "market memo",
    "why we invested",
)
_FUND_MODIFIERS = ("new fund close", "fund II", "actively deploying", "Form D filing", "raises new fund")
_GEO_MODIFIERS = ("cross-border investment", "invests in Europe", "US fund European seed", "global mandate")
_GAP_MODIFIERS = ("portfolio index", "portfolio review", "no position in", "portfolio gap")
_EXIT_MODIFIERS = ("acquisition", "exit", "acquired by", "M&A outcome")

_INTENT_SPECS: tuple[tuple[IntentKind, str, tuple[str, ...], int | None], ...] = (
    (
        "adjacent_portfolio",
        "Funds already backing companies adjacent to ours — the strongest predictor of a second check in the category.",
        _ADJACENT_MODIFIERS,
        540,
    ),
    (
        "thesis_signal",
        "Partners publishing on our space. A dated public argument is the best opening line an email can have.",
        _THESIS_MODIFIERS,
        540,
    ),
    (
        "fund_activity",
        "Fresh capital and visible deployment. A fund without dry powder is a wasted send.",
        _FUND_MODIFIERS,
        365,
    ),
    (
        "geo_crossing",
        "Funds that cross into our geography rather than requiring us to move to theirs.",
        _GEO_MODIFIERS,
        540,
    ),
    (
        "portfolio_gap",
        "Funds with a relevant portfolio and a visible hole where we would sit.",
        _GAP_MODIFIERS,
        365,
    ),
    ("recent_exit", "Partners who have already carried this buyer set through an exit.", _EXIT_MODIFIERS, 730),
)


def _subjects(profile: CompanyProfile) -> list[str]:
    subjects = [*profile.keywords, *profile.sectors]
    subjects += [f"{k} {g}" for k, g in product(profile.keywords[:4], profile.geographies[:2])]
    subjects.append(profile.one_liner.split(".")[0][:80])
    return [s for s in dict.fromkeys(s.strip() for s in subjects) if s]


def deterministic_plan(profile: CompanyProfile) -> SearchPlan:
    intents: list[SearchIntent] = []
    subjects = _subjects(profile)
    for kind, rationale, modifiers, recency in _INTENT_SPECS:
        queries = [f"{subject} {modifier}" for subject in subjects for modifier in modifiers]
        intents.append(
            SearchIntent(
                kind=kind,
                rationale=rationale,
                queries=list(dict.fromkeys(queries)),
                domain_hints=["techcrunch.com", "sifted.eu", "axios.com", "sec.gov"] if kind == "fund_activity" else [],
                recency_days=recency,
            )
        )
    return SearchPlan(profile_id=profile.id, intents=intents, generated_by="deterministic")


async def build_plan(profile: CompanyProfile) -> SearchPlan:
    llm = planner_llm()
    if llm.available:
        payload = await llm.complete(
            system=SYSTEM,
            user=(
                f"Company: {profile.company} ({profile.round}, raising {profile.raise_target}).\n"
                f"One-liner: {profile.one_liner}\n"
                f"Sectors: {', '.join(profile.sectors)}\nKeywords: {', '.join(profile.keywords)}\n"
                f"Geographies: {', '.join(profile.geographies)}\nTraction: {'; '.join(profile.traction)}"
            ),
            schema=PLAN_SCHEMA,
            schema_name="search_plan",
        )
        if payload and payload.get("intents"):
            intents = [SearchIntent(**intent) for intent in payload["intents"] if intent.get("queries")]
            if intents:
                plan = SearchPlan(profile_id=profile.id, intents=intents, generated_by="openai")
                log.info("plan generated by model: %d intents, %d queries", len(intents), plan.query_count)
                return plan
        log.info("planner fell back to deterministic plan")
    return deterministic_plan(profile)
