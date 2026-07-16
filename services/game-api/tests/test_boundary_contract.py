"""Boundary contract tests for the API.

Defends FB2/FB7 contracts:
- Unknown action strings return 422 (not 200-with-message).
- Movement actions are rejected via Pydantic validation.
- Combat actions with unknown patterns are rejected.
- Bootstrap endpoint returns expected shape.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unknown_movement_rejected() -> None:
    """Unknown movement action returns 422."""
    with client:
        resp = client.post("/api/runs", json={"player_name": "TestRunner"})
        assert resp.status_code == 200, resp.text
        run_id = resp.json()["run_id"]
        resp = client.post(f"/api/runs/{run_id}/actions", json={"action": "fly_away"})
        assert resp.status_code == 422, (
            f"Expected 422 for unknown movement action, got {resp.status_code}: {resp.text}"
        )


def test_unknown_combat_action_rejected() -> None:
    """Unknown combat action pattern returns 422."""
    with client:
        resp = client.post("/api/runs", json={"player_name": "TestRunner"})
        assert resp.status_code == 200, resp.text
        run_id = resp.json()["run_id"]
        resp = client.post(f"/api/runs/{run_id}/combat", json={"action": "ludicrous_maneuver"})
        assert resp.status_code == 422, (
            f"Expected 422 for unknown combat action, got {resp.status_code}: {resp.text}"
        )


def test_bootstrap_returns_expected_shape() -> None:
    """GET /api/bootstrap returns 200 with the expected top-level keys."""
    with client:
        resp = client.get("/api/bootstrap")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["title"] == "Sukupol"
        assert "dialogue_mode" in data
        assert isinstance(data["dungeon_biomes"], list)
        assert isinstance(data["locations"], list)
