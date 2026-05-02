from __future__ import annotations

import json

from .game import RunState


def finalize_run(state: RunState, result: str) -> dict:
    state.run_result = result
    state.status = result
    state.in_combat = False
    state.combat_state = None
    state.outcome_summary = {
        "result": result,
        "depth_reached": state.run_depth,
        "enemies_defeated": state.enemies_defeated,
        "gold_earned": state.gold,
        "items_found": [
            {
                "item_id": item["item_id"],
                "quantity": item["quantity"],
            }
            for item in state.inventory or []
        ],
    }
    state.message = (
        "You return to town with what you salvaged."
        if result == "extraction"
        else "Your run ends in the dungeon's dark."
    )
    return {
        "depth_reached": state.run_depth,
        "enemies_defeated": state.enemies_defeated,
        "gold_earned": state.gold,
        "items_json": json.dumps(state.outcome_summary["items_found"], sort_keys=True),
    }
