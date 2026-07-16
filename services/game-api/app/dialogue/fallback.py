from __future__ import annotations

from typing import Any


def fallback_response(npc: dict[str, str], player_message: str, prior_summary: str) -> str:
    message = player_message.lower()
    prefix = f"{npc['display_name']}: "
    if "dungeon" in message or "depth" in message:
        body = npc["dungeon_hint"]
    elif "town" in message or "sukupol" in message:
        body = npc["town_hint"]
    elif "supply" in message or "food" in message or "gear" in message:
        body = npc["supply_hint"]
    else:
        body = npc["greeting"]

    if prior_summary:
        body = f"{body} We have spoken recently, and I have not forgotten it."

    return prefix + body


def fallback_summary(player_message: str, reply_text: str, prior_summary: str) -> str:
    latest = f"Player asked about '{player_message.strip()}'. NPC replied '{reply_text.strip()}'."
    if prior_summary:
        return f"{prior_summary} {latest}"[:600]
    return latest[:600]


def fallback_visit_summary(npc: dict[str, Any], visit: dict[str, Any]) -> str:
    turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
    if not turns:
        return f"Visited {npc.get('display_name', visit.get('npc_name', 'this contact'))}, but no details were recorded."

    opening = turns[0] if isinstance(turns[0], dict) else {}
    closing = turns[-1] if isinstance(turns[-1], dict) else {}
    first_topic = str(opening.get("player_message", "")).strip() or "general matters"
    closing_reply = str(closing.get("npc_reply", "")).strip() or "they gave no clear closing remark"
    npc_name = npc.get("display_name", visit.get("npc_name", "This contact"))
    summary = (
        f"I spoke with {npc_name} about {first_topic}. "
        f"The discussion covered {len(turns)} exchange{'s' if len(turns) != 1 else ''}, and they closed by saying: {closing_reply}"
    )
    return summary[:600]
