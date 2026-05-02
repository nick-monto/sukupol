from __future__ import annotations

import os
from dataclasses import dataclass

from .content import WorldContent
from .db import load_conversation_summary, upsert_conversation_summary
from .game import RunState


@dataclass
class DialogueReply:
    npc_id: str
    npc_name: str
    text: str
    source: str


class NpcDialogueService:
    def __init__(self) -> None:
        self.mode = os.getenv("SUKUPOL_DIALOGUE_MODE", "stub")

    def talk(self, world: WorldContent, state: RunState, npc_id: str, player_message: str) -> DialogueReply:
        npc = world.npcs[npc_id]
        prior_summary = load_conversation_summary(state.player_id, npc_id)

        if self.mode == "agent-framework":
            text = self._agent_framework_placeholder(npc, player_message)
            source = "agent-framework-placeholder"
        else:
            text = self._fallback_response(npc, player_message, prior_summary)
            source = "stub"

        summary = f"Player asked: {player_message.strip()} | NPC replied: {text}"
        upsert_conversation_summary(state.player_id, npc_id, summary)
        return DialogueReply(
            npc_id=npc_id,
            npc_name=npc["display_name"],
            text=text,
            source=source,
        )

    def _agent_framework_placeholder(self, npc: dict[str, str], player_message: str) -> str:
        return (
            f"{npc['display_name']} weighs your words about '{player_message.strip()}'. "
            "The live Agent Framework path is not wired yet, so this placeholder marks where the local model response will land."
        )

    def _fallback_response(self, npc: dict[str, str], player_message: str, prior_summary: str) -> str:
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
