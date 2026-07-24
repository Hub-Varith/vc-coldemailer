"""End-to-end pipeline and HTTP surface, against the local index."""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.octen.executor import Executor
from app.octen.planner import deterministic_plan


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def completed_run(client) -> str:
    response = client.post("/api/v1/runs", json={})
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    status = {}
    for _ in range(300):
        status = client.get(f"/api/v1/runs/{run_id}").json()
        if status["status"] in ("complete", "failed"):
            break
        time.sleep(0.1)
    assert status["status"] == "complete", status
    return run_id


def test_plan_fans_out_to_hundreds_of_narrow_queries(profile):
    plan = deterministic_plan(profile)
    assert plan.query_count >= 150, "a ten-query plan means a conventional search API would do"
    assert len(plan.intents) == 6
    assert all(len(q.split()) >= 2 for intent in plan.intents for q in intent.queries), "queries are narrow"


@pytest.mark.asyncio
async def test_executor_dedupes_and_caches(profile):
    executor = Executor()
    plan = deterministic_plan(profile)
    plan.intents[1].queries.append(plan.intents[1].queries[0].upper())

    prepared = executor.build_queries(plan)
    texts = [q.query.lower() for _, _, q in prepared]
    assert len(texts) == len(set(texts)), "identical query strings are fired once"

    first = await executor.execute(plan)
    second = await executor.execute(plan)
    assert first.stats.cache_hits == 0
    assert second.stats.cache_hits > 0, "the retrieval cache serves the re-run"


def test_run_reports_concurrency_and_wall_time(client, completed_run):
    stats = client.get(f"/api/v1/runs/{completed_run}").json()["retrieval_stats"]
    assert stats["queries_issued"] >= 150
    assert stats["max_concurrency"] > 1, "the fan-out is concurrent, not sequential"
    assert stats["wall_time_ms"] > 0
    assert stats["failed_queries"] == 0


def test_every_listed_investor_carries_dated_evidence(client, completed_run):
    page = client.get(f"/api/v1/runs/{completed_run}/targets?limit=80").json()
    assert page["total"] > 0
    for row in page["rows"]:
        lead = row["lead_evidence"]
        assert lead["source_url"], "no evidence, no listing"
        assert lead["event_date"] or lead["source_published_at"]
        assert lead["stale"] is False, "the opening fact is never stale"


def test_decayed_records_are_rejected_not_listed(client, completed_run):
    run = client.get(f"/api/v1/runs/{completed_run}").json()
    page = client.get(f"/api/v1/runs/{completed_run}/targets?limit=80").json()
    names = {row["investor_person"] for row in page["rows"]}

    # Two decayed records reach the freshness gate and are rejected there. The third
    # (Peter Nyland, 2023 speaker bio) is excluded earlier by the retrieval-time
    # `published_after` filter, so it is never a candidate to reject.
    assert run["rejected_count"] >= 2
    assert "Arjun Mehta" not in names, "departed partner"
    assert "Claire Dubois" not in names, "fund not deploying"
    assert "Peter Nyland" not in names, "no dated evidence inside the window"


def test_rows_are_sorted_by_score_and_capped(client, completed_run):
    rows = client.get(f"/api/v1/runs/{completed_run}/targets?limit=80").json()["rows"]
    scores = [row["score"] for row in rows]
    assert scores == sorted(scores, reverse=True)
    assert len(rows) <= 80


def test_filters_and_sorting(client, completed_run):
    base = f"/api/v1/runs/{completed_run}/targets"
    high = client.get(f"{base}?min_score=0.9").json()
    assert all(row["score"] >= 0.9 for row in high["rows"])

    by_firm = client.get(f"{base}?sort=firm").json()["rows"]
    assert [r["investor_firm"] for r in by_firm] == sorted(r["investor_firm"] for r in by_firm)


def test_pagination_cursor_walks_the_list(client, completed_run):
    first = client.get(f"/api/v1/runs/{completed_run}/targets?limit=3").json()
    assert len(first["rows"]) == 3 and first["next_cursor"]
    second = client.get(f"/api/v1/runs/{completed_run}/targets?limit=3&cursor={first['next_cursor']}").json()
    assert {r["target_id"] for r in first["rows"]}.isdisjoint({r["target_id"] for r in second["rows"]})


def test_approval_flow_blocks_send_until_approved(client, completed_run):
    target_id = client.get(f"/api/v1/runs/{completed_run}/targets?limit=1").json()["rows"][0]["target_id"]
    draft = client.post(f"/api/v1/targets/{target_id}/draft").json()
    draft_id = draft["draft_id"]

    assert 80 <= draft["word_count"] <= 120

    no_key = client.post(f"/api/v1/drafts/{draft_id}/send")
    assert no_key.status_code == 400
    assert no_key.json()["error"]["code"] == "idempotency_key_required"

    unapproved = client.post(f"/api/v1/drafts/{draft_id}/send", headers={"Idempotency-Key": "t1"})
    assert unapproved.status_code == 409
    assert unapproved.json()["error"]["code"] == "draft_not_approved"

    approved = client.post(f"/api/v1/drafts/{draft_id}/approve", json={"approved_by": "founder"})
    assert approved.status_code == 200 and approved.json()["approved_at"]

    sent = client.post(f"/api/v1/drafts/{draft_id}/send", headers={"Idempotency-Key": "t1"})
    assert sent.status_code == 200 and sent.json()["status"] == "delivered"


def test_editing_a_draft_revokes_approval(client, completed_run):
    rows = client.get(f"/api/v1/runs/{completed_run}/targets?limit=3").json()["rows"]
    draft = client.post(f"/api/v1/targets/{rows[1]['target_id']}/draft").json()
    client.post(f"/api/v1/drafts/{draft['draft_id']}/approve", json={"approved_by": "founder"})

    edited = client.patch(f"/api/v1/drafts/{draft['draft_id']}", json={"body": draft["body"] + "\n\nOne more line."})
    assert edited.status_code == 200
    assert edited.json()["approved_at"] is None, "a human edit revokes approval"
    assert edited.json()["version"] == 2


def test_bulk_send_rejects_unapproved_drafts(client, completed_run):
    rows = client.get(f"/api/v1/runs/{completed_run}/targets?limit=4").json()["rows"]
    draft = client.post(f"/api/v1/targets/{rows[2]['target_id']}/draft").json()
    response = client.post(
        "/api/v1/sends/bulk", json={"draft_ids": [draft["draft_id"]]}, headers={"Idempotency-Key": "bulk-1"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "unapproved_drafts"


def test_errors_use_the_envelope(client):
    response = client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_profile_validation_flags_vague_positioning(client):
    profile_id = client.get("/api/v1/profiles").json()[0]["id"]
    ok = client.post(f"/api/v1/profiles/{profile_id}/validate").json()
    assert ok["ok"] is True

    vague = client.post("/api/v1/profiles", json={"company": "Generic Co", "sectors": ["medtech"]}).json()
    result = client.post(f"/api/v1/profiles/{vague['id']}/validate").json()
    assert result["ok"] is False
    assert "sector_too_broad" in result["warnings"]
    assert result["suggestions"]


def test_plan_endpoint_exposes_the_query_fanout(client, completed_run):
    plan = client.get(f"/api/v1/runs/{completed_run}/plan").json()
    assert sum(len(intent["queries"]) for intent in plan["intents"]) >= 150


def test_csv_export(client, completed_run):
    response = client.get(f"/api/v1/runs/{completed_run}/targets/export")
    assert response.status_code == 200
    assert "lead_claim" in response.text.splitlines()[0]
