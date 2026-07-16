from __future__ import annotations

from typing import Any
from ..agents.sanitize import sanitize_prompt_input

from ..agents import CombatParleyService
from ..content import WorldContent
from ..game import RunState
from ..inventory import add_item

from .loot import deterministic_roll
from .negotiation import (
    NEGOTIATION_OUTCOMES,
    analyze_parley_message,
    append_negotiation_transcript,
    enemy_negotiation_profile,
    parley_target_number,
    update_negotiation_lock,
)
from .party import active_party_allies, build_available_actions, grant_recruited_ally


PARLEY_ROLL_LOW = 1
PARLEY_ROLL_HIGH = 10


def _handle_parley_open(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], negotiation: dict[str, Any],
    parley_service: CombatParleyService | None,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    if not negotiation.get("available"):
        state.message = str(negotiation.get("lock_reason") or "No opening for parley.")
        return False, False, []
    negotiation["active"] = True
    line = sanitize_prompt_input(
        parley_service.generate_open_line(world, state, combat_state, enemy_def, negotiation)
        if parley_service is not None
        else f"You open parley. {enemy_def['name']} answers by {negotiation['communication_mode']}, waiting for your terms."
    )
    append_negotiation_transcript(negotiation, "player", "You call for terms.")
    append_negotiation_transcript(negotiation, "enemy", line)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    state.message = line
    return False, False, [("system", line, "parley")]

def _handle_parley_end(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], negotiation: dict[str, Any],
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    if not negotiation.get("active"):
        state.message = "No active parley to break."
        return False, False, []
    negotiation["active"] = False
    negotiation["anger"] = int(negotiation.get("anger", 0)) + 1
    append_negotiation_transcript(negotiation, "player", "You let the talks fall away.")
    update_negotiation_lock(negotiation, enemy_def)
    line = "The silence hardens the creature's posture."
    append_negotiation_transcript(negotiation, "system", line)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    state.message = line
    return False, True, [("system", line, "warning")]

def _update_from_analysis(
    negotiation: dict[str, Any], analysis: dict[str, Any], profile: dict[str, Any],
) -> None:
    leverage = int(negotiation.get("leverage", 0)) + int(analysis["leverage_delta"])
    anger = int(negotiation.get("anger", 0)) + int(analysis["anger_delta"])
    negotiation["leverage"] = max(-3, min(3, leverage))
    negotiation["anger"] = max(0, anger)
    if analysis["inferred_intent"] in profile["outcomes"]:
        negotiation["active_intent"] = analysis["inferred_intent"]

def _execute_parley_message(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], negotiation: dict[str, Any],
    profile: dict[str, Any], text: str,
    parley_service: CombatParleyService | None,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    negotiation["attempts"] = int(negotiation.get("attempts", 0)) + 1
    analysis = analyze_parley_message(profile, text, negotiation)
    _update_from_analysis(negotiation, analysis, profile)
    line = sanitize_prompt_input(parley_service.generate_reply(world, state, combat_state, enemy_def, negotiation, text, analysis) if parley_service is not None else str(analysis["reply"]))
    append_negotiation_transcript(negotiation, "player", text)
    append_negotiation_transcript(negotiation, "enemy", line)
    update_negotiation_lock(negotiation, enemy_def)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    state.message = line
    return False, not bool(analysis["grants_pause"]) or bool(analysis["provoked"]), [("enemy" if analysis["provoked"] else "system", line, "warning" if analysis["provoked"] else "parley")]
def _handle_parley_message(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], negotiation: dict[str, Any],
    profile: dict[str, Any], message: str,
    parley_service: CombatParleyService | None,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    text = str(message or "").strip()
    if not text:
        state.message = "Say something concrete before sending the line."
        return False, False, []
    if not negotiation.get("active"):
        state.message = "Open parley before you speak."
        return False, False, []
    return _execute_parley_message(world, state, combat_state, enemy_def, negotiation, profile, text, parley_service)

def _success_line(world: WorldContent, state: RunState, enemy_def: dict[str, Any], profile: dict[str, Any], action: str) -> str:
    if action == "parley_recruit":
        ally = grant_recruited_ally(state, enemy_def, int(profile["ally_battles"]))
        return f"{enemy_def['name']} lowers its guard and agrees to fight beside you for {ally['remaining_battles']} battles."
    if action == "parley_tribute":
        return award_tribute(world, state, enemy_def)
    return f"{enemy_def['name']} yields the ground and withdraws."

def _apply_parley_success(
    world: WorldContent, state: RunState, enemy_def: dict[str, Any],
    negotiation: dict[str, Any], profile: dict[str, Any],
    action: str, requested_outcome: str,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    negotiation["outcome"] = requested_outcome
    negotiation["active"] = False
    negotiation["available"] = False
    negotiation["locked"] = True
    line = _success_line(world, state, enemy_def, profile, action)
    negotiation["lock_reason"] = line
    append_negotiation_transcript(negotiation, "enemy", line)
    state.in_combat = False
    state.combat_state = None
    state.message = line
    return True, False, [("enemy", line, "parley")]

def _apply_outcome_failure(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], negotiation: dict[str, Any],
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    negotiation["anger"] = int(negotiation.get("anger", 0)) + 1
    update_negotiation_lock(negotiation, enemy_def)
    line = f"{enemy_def['name']} rejects the offer and grows sharper."
    append_negotiation_transcript(negotiation, "enemy", line)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    state.message = line
    return False, True, [("enemy", line, "warning")]

def _roll_parley_outcome(
    state: RunState, enemy_def: dict[str, Any],
    combat_state: dict[str, Any], negotiation: dict[str, Any],
    action: str,
) -> tuple[int, str]:
    requested_outcome = action.removeprefix("parley_")
    negotiation["attempts"] = int(negotiation.get("attempts", 0)) + 1
    negotiation["active_intent"] = requested_outcome
    roll = deterministic_roll(
        state.run_seed, enemy_def["id"], state.steps_taken,
        combat_state.get("round", 1), action, negotiation.get("attempts", 0),
        low=PARLEY_ROLL_LOW, high=PARLEY_ROLL_HIGH,
    )
    return roll, requested_outcome


def _handle_parley_outcome(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], negotiation: dict[str, Any],
    profile: dict[str, Any], action: str,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    if not negotiation.get("active"):
        state.message = "Open parley before you press for terms."
        return False, False, []
    if action not in {"parley_recruit", "parley_tribute", "parley_retreat"}:
        state.message = f"Unknown combat action: {action}"
        return False, False, []
    ro = action.removeprefix("parley_")
    if ro not in profile["outcomes"]:
        state.message = "That demand finds no purchase with this foe."
        return False, False, []
    roll, _ = _roll_parley_outcome(state, enemy_def, combat_state, negotiation, action)
    append_negotiation_transcript(negotiation, "player", NEGOTIATION_OUTCOMES[ro])
    if roll >= parley_target_number(profile, negotiation, action):
        return _apply_parley_success(world, state, enemy_def, negotiation, profile, action, ro)
    return _apply_outcome_failure(world, state, combat_state, enemy_def, negotiation)


def resolve_parley_action(
    world: WorldContent, state: RunState, combat_state: dict[str, Any],
    enemy_def: dict[str, Any], action: str,
    message: str | None = None,
    parley_service: CombatParleyService | None = None,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
    profile = enemy_negotiation_profile(enemy_def)
    if negotiation is None or profile is None:
        state.message = "This enemy cannot reason with you."
        return False, False, []
    if action == "parley_open":
        return _handle_parley_open(world, state, combat_state, enemy_def, negotiation, parley_service)
    if action == "parley_end":
        return _handle_parley_end(world, state, combat_state, enemy_def, negotiation)
    if action == "parley_message":
        return _handle_parley_message(world, state, combat_state, enemy_def, negotiation, profile, message or "", parley_service)
    return _handle_parley_outcome(world, state, combat_state, enemy_def, negotiation, profile, action)


def award_tribute(world: WorldContent, state: RunState, enemy_def: dict[str, Any]) -> str:
    profile = enemy_negotiation_profile(enemy_def)
    if profile is None or not profile.get("tribute_item_id"):
        gold_min, gold_max = enemy_def.get("gold_drop", [1, 2])
        gold = deterministic_roll(state.run_seed, enemy_def["id"], state.steps_taken, "tribute-gold", low=gold_min, high=gold_max)
        state.gold += gold
        return f"{enemy_def['name']} yields {gold} gold rather than risk your blade."
    item_id = str(profile["tribute_item_id"])
    quantity = int(profile["tribute_quantity"])
    add_item(state, world, item_id, quantity)
    return f"{enemy_def['name']} offers {world.items[item_id]['name']} x{quantity} to end the standoff."

def resolve_ally_support(
    state: RunState, combat_state: dict[str, Any],
    enemy_state: dict[str, Any], enemy_defence: int,
) -> list[tuple[str, str, str]]:
    combat_events: list[tuple[str, str, str]] = []
    allies = active_party_allies(state)
    if not allies:
        return combat_events
    total_damage = 0
    names: list[str] = []
    rn = int(combat_state.get("round", 1))
    for ally in allies:
        variance = deterministic_roll(state.run_seed, ally.get("ally_id", ally.get("name", "ally")), rn, "ally", low=0, high=1)
        damage = max(1, int(ally.get("attack", 1)) + variance - enemy_defence)
        total_damage += damage
        names.append(str(ally.get("name", "Ally")))
    enemy_state["hp"] = max(0, int(enemy_state["hp"]) - total_damage)
    combat_events.append(("ally", f"{', '.join(names)} strike for {total_damage} damage.", "support"))
    return combat_events
