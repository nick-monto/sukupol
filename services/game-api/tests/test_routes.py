"""Route integration tests using TestClient (no real server).

Each test runs inside the lifespan (DB initialized, world loaded) and
asserts status codes + snapshot shapes for the settled route contracts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.connection import resolve_db_path
from app.db.quests import create_player_quest
from app.main import app


def test_health_200() -> None:
    """GET /api/health returns 200 with status ok."""
    with TestClient(app) as c:
        resp = c.get("/api/health")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "ok"


def test_bootstrap_200() -> None:
    """GET /api/bootstrap returns 200 and matches BootstrapResponse shape."""
    with TestClient(app) as c:
        resp = c.get("/api/bootstrap")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["title"] == "Sukupol"
        assert "dialogue_mode" in data
        assert isinstance(data["dungeon_biomes"], list)
        assert isinstance(data["locations"], list)
        if data["dungeon_biomes"]:
            biome = data["dungeon_biomes"][0]
            assert "id" in biome
            assert "name" in biome


def test_start_run_200() -> None:
    """POST /api/runs returns 200 with a run_id."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "TestRunner"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "run_id" in data
        assert data["player_name"] == "TestRunner"
        assert data["run_id"]


def test_valid_action_returns_snapshot() -> None:
    """POST /api/runs/{id}/actions with a valid action returns 200
    and a snapshot with location/position/stats."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp = c.post(
            f"/api/runs/{run_id}/actions",
            json={"action": "move_north"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["run_id"] == run_id
        assert "location" in data
        assert "position" in data
        assert "stats" in data
        assert "map_view" in data


def test_unknown_action_422() -> None:
    """Unknown action string returns 422 (Pydantic rejection)."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp = c.post(
            f"/api/runs/{run_id}/actions",
            json={"action": "fly_away"},
        )
        assert resp.status_code == 422, (
            f"Expected 422 for unknown action, got {resp.status_code}: {resp.text}"
        )


def test_combat_no_active_combat_400() -> None:
    """POST /api/runs/{id}/combat without active combat returns 400."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp = c.post(
            f"/api/runs/{run_id}/combat",
            json={"action": "defend"},
        )
        assert resp.status_code == 400, resp.text
        assert "No active combat" in resp.json()["detail"]


def test_npc_talk_not_found_404() -> None:
    """Talking to a non-existent NPC returns 404."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp = c.post(
            "/api/npcs/nonexistent_npc/talk",
            json={"run_id": run_id, "message": "hello"},
        )
        assert resp.status_code == 404, resp.text
        assert "NPC not found" in resp.json()["detail"]


def test_npc_talk_not_nearby_400() -> None:
    """Talking to an NPC not in the current location returns 400."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        # petra-scout is in dungeon_approach, not in town_square where
        # the player starts.
        resp = c.post(
            "/api/npcs/petra-scout/talk",
            json={"run_id": run_id, "message": "hello"},
        )
        assert resp.status_code == 400, resp.text
        assert "NPC is not nearby" in resp.json()["detail"]


def test_quest_accept_not_found_404() -> None:
    """Accepting a non-existent quest returns 404."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp = c.post(
            "/api/quests/nonexistent_quest/accept",
            json={"run_id": run_id},
        )
        assert resp.status_code == 404, resp.text
        assert "Quest not found" in resp.json()["detail"]


def test_quest_accept_not_nearby_400() -> None:
    """Accepting a quest whose giver is not nearby returns 400."""
    with TestClient(app) as c:
        resp = c.post("/api/runs", json={"player_name": "Tester"})
        assert resp.status_code == 200
        data = resp.json()
        run_id = data["run_id"]

        # Grab the cached state so we can create a quest for this player
        state = app.state.runs[run_id]

        # Create a quest offered by petra-scout (in dungeon_approach,
        # not in town_square — the player's current location).
        # Template ID format: fetch|{npc_id}|{target_biome_id}|{floor_num}|{item_id}|{gold}
        template_id = "fetch|petra-scout|whispering_caverns|1|petra_scout_compass|10"
        quest = create_player_quest(
            player_id=state.player_id,
            template_id=template_id,
            run_id=run_id,
            offered_by_npc_id="petra-scout",
            title="Far Away Quest",
            summary="The giver is in another location.",
            objective_text="Travel far",
            objective_kind="fetch",
            target_location_id=None,
            target_biome_id="whispering_caverns",
            target_floor_number=1,
            target_count=1,
            progress_value=0,
            progress_target=1,
            status="offered",
            db_path=resolve_db_path(),
        )

        resp = c.post(
            f"/api/quests/{quest.id}/accept",
            json={"run_id": run_id},
        )
        assert resp.status_code == 400, resp.text
        assert "Quest giver is not nearby" in resp.json()["detail"]
