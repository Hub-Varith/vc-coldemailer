"""Confirms the /api/v1 HTTP surface (API_ENDPOINTS.md) for the routes this
backend owns: profiles, runs, targets, system health/usage. FastAPI's
TestClient runs BackgroundTasks synchronously, so by the time POST
/api/v1/runs returns, the mocked pipeline has already completed."""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.models import EvidenceRecord, TargetList, TargetRow
from app.store import RunStore, get_store


@pytest.fixture()
def store() -> RunStore:
    return RunStore()


@pytest.fixture()
def client(store, monkeypatch) -> TestClient:
    main.app.dependency_overrides[get_store] = lambda: store

    async def fake_run_pipeline(run_id, profile, settings, store):
        store.update_run_stage(run_id, "complete")

    monkeypatch.setattr(main, "run_pipeline", AsyncMock(side_effect=fake_run_pipeline))
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _profile_payload(**overrides) -> dict:
    payload = {
        "company_name": "Acme Hearing",
        "one_liner": "Bone-conduction hearing aids",
        "sector": "bone-conduction hearing hardware",
        "product_description": "Affordable bone-conduction hearing devices for rural clinics",
        "stage": "seed",
        "geography": "Kenya",
    }
    payload.update(overrides)
    return payload


def _make_target_row(**overrides) -> TargetRow:
    evidence = EvidenceRecord(
        investor_firm="Acme Ventures", kind="portfolio_investment", claim="c",
        event_date=None, source_url="https://x.com", source_published_at=None,
        confidence=0.9, stale=False,
    )
    defaults = dict(investor_firm="Acme Ventures", score=1.0, evidence=[evidence], lead_evidence=evidence)
    defaults.update(overrides)
    return TargetRow(**defaults)


def _seed_target_list(store: RunStore, run_id, profile_id, rows: list[TargetRow]) -> TargetList:
    from datetime import datetime, timezone

    from app.models import RetrievalStats

    target_list = TargetList(
        run_id=run_id, profile_id=profile_id, generated_at=datetime.now(timezone.utc), rows=rows,
        retrieval_stats=RetrievalStats(query_count=10, result_count=5, failed_query_count=0, wall_time_s=1.0),
    )
    store.save_target_list(run_id, target_list)
    return target_list


# --- system ---


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_usage_reports_only_tracked_numbers(client):
    resp = client.get("/api/v1/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"runs_used": 0, "queries_consumed": 0, "token_spend_usd": None}


# --- profiles ---


def test_profile_crud_and_validate(client):
    create_resp = client.post("/api/v1/profiles", json=_profile_payload())
    assert create_resp.status_code == 200
    profile_id = create_resp.json()["id"]

    assert client.get(f"/api/v1/profiles/{profile_id}").status_code == 200
    assert len(client.get("/api/v1/profiles").json()) == 1

    patch_resp = client.patch(f"/api/v1/profiles/{profile_id}", json={"stage": "series-a"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["stage"] == "series-a"
    assert patch_resp.json()["company_name"] == "Acme Hearing"  # untouched fields survive

    validate_resp = client.post(f"/api/v1/profiles/{profile_id}/validate")
    assert validate_resp.status_code == 200
    assert validate_resp.json()["ok"] is True

    assert client.delete(f"/api/v1/profiles/{profile_id}").status_code == 204
    assert client.get(f"/api/v1/profiles/{profile_id}").status_code == 404


def test_validate_flags_generic_sector_and_thin_description(client):
    create_resp = client.post("/api/v1/profiles", json=_profile_payload(sector="tech", product_description="an app"))
    profile_id = create_resp.json()["id"]

    body = client.post(f"/api/v1/profiles/{profile_id}/validate").json()

    assert body["ok"] is False
    assert "sector_too_broad" in body["warnings"]
    assert "product_description_too_thin" in body["warnings"]


def test_error_envelope_shape_on_404(client):
    resp = client.get(f"/api/v1/profiles/{uuid4()}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "profile_not_found"
    assert "message" in body["error"]


# --- runs ---


def test_full_run_lifecycle(client):
    profile_resp = client.post("/api/v1/profiles", json=_profile_payload())
    profile_id = profile_resp.json()["id"]

    run_resp = client.post("/api/v1/runs", json={"profile_id": profile_id})
    assert run_resp.status_code == 202
    run_id = run_resp.json()["run_id"]

    status_resp = client.get(f"/api/v1/runs/{run_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "complete"
    assert status_resp.json()["stage"] == "complete"

    list_resp = client.get("/api/v1/runs", params={"profile_id": profile_id})
    assert len(list_resp.json()["runs"]) == 1

    assert client.delete(f"/api/v1/runs/{run_id}").status_code == 204
    assert client.get(f"/api/v1/runs/{run_id}").status_code == 404


def test_start_run_404_for_unknown_profile(client):
    resp = client.post("/api/v1/runs", json={"profile_id": str(uuid4())})
    assert resp.status_code == 404


def test_cancel_run_sets_cancel_flag(client, store):
    profile_id = client.post("/api/v1/profiles", json=_profile_payload()).json()["id"]
    run_id = client.post("/api/v1/runs", json={"profile_id": profile_id}).json()["run_id"]

    resp = client.post(f"/api/v1/runs/{run_id}/cancel")

    assert resp.status_code == 200
    assert store.is_cancel_requested(UUID(run_id)) is True


def test_run_events_returns_final_state_for_a_completed_run(client):
    profile_id = client.post("/api/v1/profiles", json=_profile_payload()).json()["id"]
    run_id = client.post("/api/v1/runs", json={"profile_id": profile_id}).json()["run_id"]

    with client.stream("GET", f"/api/v1/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    assert "event: run_complete" in body


def test_get_targets_404_before_run_completes(client):
    resp = client.get(f"/api/v1/runs/{uuid4()}/targets")
    assert resp.status_code == 404


# --- targets ---


def test_list_targets_pagination_and_filters(store):
    run_id, profile_id = uuid4(), uuid4()
    rows = [_make_target_row(investor_firm=f"Firm {i}", score=float(10 - i)) for i in range(3)]
    _seed_target_list(store, run_id, profile_id, rows)
    main.app.dependency_overrides[get_store] = lambda: store
    client = TestClient(main.app)

    page1 = client.get(f"/api/v1/runs/{run_id}/targets", params={"limit": 2}).json()
    assert len(page1["rows"]) == 2
    assert page1["total"] == 3
    assert page1["next_cursor"] is not None

    page2 = client.get(f"/api/v1/runs/{run_id}/targets", params={"limit": 2, "cursor": page1["next_cursor"]}).json()
    assert len(page2["rows"]) == 1

    main.app.dependency_overrides.clear()


def test_get_patch_and_dismiss_target(store):
    run_id, profile_id = uuid4(), uuid4()
    row = _make_target_row()
    _seed_target_list(store, run_id, profile_id, [row])
    main.app.dependency_overrides[get_store] = lambda: store
    client = TestClient(main.app)

    get_resp = client.get(f"/api/v1/targets/{row.target_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["evidence"]  # full evidence array, unlike the list endpoint

    patch_resp = client.patch(f"/api/v1/targets/{row.target_id}", json={"notes": "follow up next week"})
    assert patch_resp.json()["notes"] == "follow up next week"

    dismiss_resp = client.post(f"/api/v1/targets/{row.target_id}/dismiss")
    assert dismiss_resp.json()["status"] == "dismissed"

    main.app.dependency_overrides.clear()


def test_export_targets_returns_csv(store):
    run_id, profile_id = uuid4(), uuid4()
    _seed_target_list(store, run_id, profile_id, [_make_target_row()])
    main.app.dependency_overrides[get_store] = lambda: store
    client = TestClient(main.app)

    resp = client.get(f"/api/v1/runs/{run_id}/targets/export")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "Acme Ventures" in resp.text

    main.app.dependency_overrides.clear()
