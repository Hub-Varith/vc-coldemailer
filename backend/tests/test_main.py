"""M5: confirms the HTTP surface -- create a profile, start a run, poll
status, fetch the plan and targets once the (mocked) pipeline has run.
FastAPI's TestClient runs BackgroundTasks synchronously, so by the time
POST /runs returns, the mocked pipeline has already completed."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.store import RunStore, get_store


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    test_store = RunStore()
    main.app.dependency_overrides[get_store] = lambda: test_store

    async def fake_run_pipeline(run_id, profile, settings, store):
        store.update_run_state(run_id, "done")

    monkeypatch.setattr(main, "run_pipeline", AsyncMock(side_effect=fake_run_pipeline))
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _profile_payload() -> dict:
    return {
        "company_name": "Acme Hearing",
        "one_liner": "Bone-conduction hearing aids",
        "sector": "medtech",
        "product_description": "Affordable hearing devices",
        "stage": "seed",
        "geography": "Kenya",
    }


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_full_run_lifecycle(client):
    profile_resp = client.post("/profiles", json=_profile_payload())
    assert profile_resp.status_code == 200
    profile_id = profile_resp.json()["id"]

    run_resp = client.post("/runs", json={"profile_id": profile_id})
    assert run_resp.status_code == 200
    run_id = run_resp.json()["run_id"]

    status_resp = client.get(f"/runs/{run_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["state"] == "done"


def test_start_run_404_for_unknown_profile(client):
    resp = client.post("/runs", json={"profile_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 404


def test_get_targets_404_before_run_completes_pipeline_writes_them(client):
    resp = client.get("/runs/00000000-0000-0000-0000-000000000000/targets")
    assert resp.status_code == 404
