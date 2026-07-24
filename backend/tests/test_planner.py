"""M2: confirms the planner wires the OpenAI structured-output response
into a SearchPlan without inventing a profile_id."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.models import CompanyProfile, SearchIntent
from app.planner import _PlanSchema, build_search_plan


def _fake_openai_client(intents: list[SearchIntent]) -> AsyncMock:
    parsed = _PlanSchema(intents=intents)
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])
    client = AsyncMock()
    client.chat.completions.parse.return_value = response
    return client


async def test_build_search_plan_attaches_profile_id(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL_PLANNER", "test-model")
    profile = CompanyProfile(
        id=uuid4(),
        company_name="Acme Hearing",
        one_liner="Bone-conduction hearing aids for emerging markets",
        sector="medtech",
        product_description="Affordable bone-conduction hearing devices",
        stage="seed",
        geography="Kenya",
    )
    intent = SearchIntent(kind="thesis_signal", rationale="r", queries=["q1", "q2", "q3", "q4", "q5"])
    client = _fake_openai_client([intent])

    plan = await build_search_plan(profile, client=client)

    assert plan.profile_id == profile.id
    assert plan.intents == [intent]
    client.chat.completions.parse.assert_awaited_once()
    _, kwargs = client.chat.completions.parse.call_args
    assert kwargs["model"] == "test-model"
    assert kwargs["response_format"] is _PlanSchema
