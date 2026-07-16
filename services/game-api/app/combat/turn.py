from __future__ import annotations

import logging
from typing import Any

from ..agents import CombatParleyService
from ..content import WorldContent
from ..game import RunState
from ..inventory import use_item

from .loot import apply_loot, deterministic_roll, player_attack_value
from .negotiation import append_negotiation_transcript
from .parley import resolve_ally_support, resolve_parley_action
from .party import build_available_actions, build_party_slots, consume_party_allies
from .state import append_combat_events, normalize_combat_state

logger = logging.getLogger(__name__)

ROLL_VARIANCE_LOW = 0
ROLL_VARIANCE_HIGH = 2
PINBALL_ACTION_PREFIX = "pinball_strike:"




def _sync_enemy_flat_keys(combat_state: dict[str, Any], enemy_state: dict[str, Any]) -> None:
    combat_state["enemy_hp"] = enemy_state["hp"]
    combat_state["enemy_max_hp"] = enemy_state["max_hp"]
    combat_state["enemy_damage"] = enemy_state["attack"]
    combat_state["enemy_defence"] = enemy_state["defence"]

def _verify_combat_state(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    if not state.in_combat or state.combat_state is None:
        logger.error("No active combat state for run %s", state.id)
        state.message = "There is no active combat to resolve."
        return None
    combat_state = normalize_combat_state(world, state)
    if combat_state is None:
        logger.error("Combat state could not be restored for run %s", state.id)
        state.message = "Combat state could not be restored."
    return combat_state

def _resolve_parley_path(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], action: str, message: str | None,
    parley_service: CombatParleyService | None, round_number: int,
    combat_events: list[tuple[str, str, str]], enemy_state: dict[str, Any],
) -> bool:
    resolved, enemy_attacks, events = resolve_parley_action(
        world, state, combat_state, enemy_def, action, message=message, parley_service=parley_service,
    )
    if resolved:
        return True
    if events:
        combat_events.extend(events)
    _sync_enemy_flat_keys(combat_state, enemy_state)
    if not enemy_attacks:
        _update_combat_state_ui(world, state, combat_state, round_number, combat_events)
        return True
    return False

def _resolve_attack_action(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_state: dict[str, Any], enemy_defence: int, round_number: int,
    action: str, combat_events: list[tuple[str, str, str]],
) -> None:
    negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
    if negotiation and negotiation.get("active"):
        negotiation["active"] = False
        negotiation["locked"] = True
        negotiation["available"] = False
        negotiation["lock_reason"] = "Steel ended the talk."
        append_negotiation_transcript(negotiation, "system", "Steel ends the parley.")
    variance = deterministic_roll(
        state.run_seed, combat_state["enemy_id"], round_number, action,
        low=ROLL_VARIANCE_LOW, high=ROLL_VARIANCE_HIGH,
    )
    damage = max(1, player_attack_value(world, state) + variance - enemy_defence)
    enemy_state["hp"] = max(0, int(enemy_state["hp"]) - damage)
    combat_events.append(("player", f"You strike for {damage} damage.", "impact"))

def _resolve_pinball_action(
    action: str, combat_state: dict[str, Any], enemy_state: dict[str, Any],
    enemy_def: dict[str, Any], enemy_defence: int,
    combat_events: list[tuple[str, str, str]],
) -> bool:
    raw_score = action[len(PINBALL_ACTION_PREFIX):]
    if not raw_score.isdigit():
        logger.warning("Invalid pinball_strike format: %s", action)
        return False
    score = max(0, int(raw_score))
    damage = max(0, score - enemy_defence)
    if damage > 0:
        enemy_state["hp"] = max(0, int(enemy_state["hp"]) - damage)
        combat_events.append(("player", f"You channel {damage} damage into {enemy_def['name']}.", "impact"))
    else:
        combat_events.append(("player", "Your strike glances off.", "guard"))
    return True

def _resolve_flee_action(state: RunState, combat_state: dict[str, Any]) -> None:
    consume_party_allies(state, combat_state)
    state.in_combat = False
    state.combat_state = None
    state.message = "You break away and regain your footing."

def _resolve_use_item_action(
    state: RunState, world: WorldContent, action: str,
    combat_state: dict[str, Any], combat_events: list[tuple[str, str, str]],
) -> bool:
    item_id = action.split(":", 1)[1]
    success, msg = use_item(state, world, item_id)
    if not success:
        state.message = msg
        combat_state["available_actions"] = build_available_actions(world, state, combat_state)
        return False
    combat_events.append(("player", msg, "item"))
    return True

def _check_enemy_defeated(
    state: RunState,
    enemy_state: dict[str, Any],
    enemy_def: dict[str, Any],
    world: WorldContent,
    combat_state: dict[str, Any],
    label: str,
) -> bool:
    if int(enemy_state["hp"]) > 0:
        return False
    loot_summary = apply_loot(world, state, enemy_def)
    state.enemies_defeated += 1
    consume_party_allies(state, combat_state)
    state.in_combat = False
    state.combat_state = None
    state.message = f"{label} {enemy_def['name']}. {loot_summary}".strip()
    return True

def _handle_enemy_attack(
    state: RunState,
    combat_state: dict[str, Any],
    enemy_state: dict[str, Any],
    enemy_def: dict[str, Any],
    round_number: int,
    defended: bool,
    combat_events: list[tuple[str, str, str]],
) -> None:
    negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
    anger_bonus = int(negotiation.get("anger", 0)) if negotiation else 0
    variance = deterministic_roll(
        state.run_seed, combat_state["enemy_id"], round_number, "enemy",
        low=ROLL_VARIANCE_LOW, high=ROLL_VARIANCE_HIGH,
    )
    enemy_damage = max(1, int(enemy_def["damage"]) + variance + min(2, anger_bonus) - (2 if defended else 0))
    state.hp = max(0, state.hp - enemy_damage)
    combat_events.append(("enemy", f"{enemy_def['name']} hits you for {enemy_damage} damage.", "impact"))

def _update_combat_state_ui(
    world: WorldContent,
    state: RunState,
    combat_state: dict[str, Any],
    round_number: int,
    combat_events: list[tuple[str, str, str]],
) -> None:
    append_combat_events(combat_state, round_number, combat_events)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    combat_state["party"] = build_party_slots(world, state, combat_state.get("party"))
    state.combat_state = combat_state
    if combat_events:
        state.message = combat_events[-1][1]

def _finalize_turn(
    world: WorldContent,
    state: RunState,
    combat_state: dict[str, Any],
    enemy_state: dict[str, Any],
    enemy_def: dict[str, Any],
    round_number: int,
    combat_events: list[tuple[str, str, str]],
) -> None:
    combat_state["round"] = round_number + 1
    _sync_enemy_flat_keys(combat_state, enemy_state)
    _update_combat_state_ui(world, state, combat_state, round_number, combat_events)
    if state.hp <= 0:
        state.hp = 0
        consume_party_allies(state, combat_state)
        state.in_combat = False
        state.combat_state = None
        state.run_result = "death"
        state.status = "dead"
        state.message = f"{enemy_def['name']} cuts you down in the dark."

def _process_enemy_phase(
    world: WorldContent,
    state: RunState,
    combat_state: dict[str, Any],
    enemy_state: dict[str, Any],
    enemy_def: dict[str, Any],
    round_number: int,
    combat_events: list[tuple[str, str, str]],
    defended: bool,
) -> None:
    if _check_enemy_defeated(state, enemy_state, enemy_def, world, combat_state, "You defeat"):
        return
    combat_events.extend(resolve_ally_support(state, combat_state, enemy_state, int(enemy_state.get("defence", 0))))
    if _check_enemy_defeated(state, enemy_state, enemy_def, world, combat_state, "Your party breaks"):
        return
    _handle_enemy_attack(state, combat_state, enemy_state, enemy_def, round_number, defended, combat_events)
    _finalize_turn(world, state, combat_state, enemy_state, enemy_def, round_number, combat_events)

def _handle_basic_action(
    action: str, world: WorldContent, state: RunState,
    combat_state: dict[str, Any], enemy_state: dict[str, Any],
    enemy_defence: int, round_number: int,
    combat_events: list[tuple[str, str, str]],
) -> tuple[bool, bool] | None:
    if action == "attack":
        _resolve_attack_action(world, state, combat_state, enemy_state, enemy_defence, round_number, action, combat_events)
        return (False, False)
    if action == "defend":
        combat_events.append(("player", "You brace for the enemy's counterattack.", "guard"))
        return (False, True)
    return None

def _handle_extended_action(
    action: str, world: WorldContent, state: RunState,
    combat_state: dict[str, Any], enemy_state: dict[str, Any],
    enemy_def: dict[str, Any], enemy_defence: int, combat_events: list[tuple[str, str, str]],
) -> tuple[bool, bool] | None:
    if action.startswith(PINBALL_ACTION_PREFIX):
        if _resolve_pinball_action(action, combat_state, enemy_state, enemy_def, enemy_defence, combat_events):
            return (False, False)
        state.message = f"Invalid combat action format: {action}"
        return None
    if action.startswith("use_item:"):
        if _resolve_use_item_action(state, world, action, combat_state, combat_events):
            return (False, False)
        return None
    if action == "flee":
        _resolve_flee_action(state, combat_state)
        return None
    logger.warning("Unknown combat action in resolve_turn: %s", action)
    state.message = f"Unknown combat action: {action}"
    return None
def _perform_action(
    world: WorldContent, state: RunState,
    combat_state: dict[str, Any], action: str,
    message: str | None, parley_service: CombatParleyService | None,
    round_number: int, combat_events: list[tuple[str, str, str]],
    enemy_state: dict[str, Any], enemy_def: dict[str, Any],
    enemy_defence: int,
) -> tuple[bool, bool] | None:
    if action.startswith("parley_"):
        return (_resolve_parley_path(world, state, combat_state, enemy_def, action, message, parley_service, round_number, combat_events, enemy_state), False)
    basic = _handle_basic_action(action, world, state, combat_state, enemy_state, enemy_defence, round_number, combat_events)
    if basic is not None:
        return basic
    return _handle_extended_action(action, world, state, combat_state, enemy_state, enemy_def, enemy_defence, combat_events)

def resolve_turn(
    world: WorldContent, state: RunState, action: str,
    message: str | None = None, parley_service: CombatParleyService | None = None,
) -> None:
    combat_state = _verify_combat_state(world, state)
    if combat_state is None:
        return
    enemy_state = combat_state["enemy"]
    enemy_def = world.enemies[enemy_state["id"]]
    combat_events: list[tuple[str, str, str]] = []
    enemy_defence = int(enemy_state.get("defence", 0))
    round_number = int(combat_state.get("round", 1))
    result = _perform_action(world, state, combat_state, action, message, parley_service, round_number, combat_events, enemy_state, enemy_def, enemy_defence)
    if result is None:
        return
    is_done, defended = result
    if is_done:
        return
    _process_enemy_phase(world, state, combat_state, enemy_state, enemy_def, round_number, combat_events, defended)
