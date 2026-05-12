from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator
from urllib import error, request

from .content import WorldContent
from .db import (
    create_npc_journal_entry,
    list_npc_shared_knowledge,
    load_npc_player_memory,
    utc_now,
    upsert_conversation_summary,
    upsert_npc_player_memory,
    upsert_npc_shared_knowledge,
)
from .game import RunState, nearby_npcs, resolve_location


logger = logging.getLogger(__name__)
JOURNAL_SUMMARY_AGENT_NAME = "Journal Summary"


@dataclass
class DialogueReply:
    npc_id: str
    npc_name: str
    text: str
    source: str


@dataclass
class ModelDialogueResult:
    reply: str


class OpenAICompatibleDialogueClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("SUKUPOL_OPENAI_BASE_URL", "http://127.0.0.1:8033")
        self.model = os.getenv("SUKUPOL_OPENAI_MODEL", "agent-framework")
        self.api_key = os.getenv("SUKUPOL_OPENAI_API_KEY", "")
        self.timeout = float(os.getenv("SUKUPOL_OPENAI_TIMEOUT", "20"))
        self.temperature = float(os.getenv("SUKUPOL_OPENAI_TEMPERATURE", "1.0"))

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response_text = self._post(payload)
        return extract_json_payload(response_text)

    def stream_text(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        yield from self._post_stream(payload)

    def _post(self, payload: dict[str, Any]) -> str:
        endpoint = resolve_chat_endpoint(self.base_url)
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        http_request = request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Dialogue provider request failed: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Dialogue provider response did not contain a chat completion message") from exc

    def _post_stream(self, payload: dict[str, Any]) -> Iterator[str]:
        endpoint = resolve_chat_endpoint(self.base_url)
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        http_request = request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(http_request, timeout=self.timeout) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        payload = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = payload.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    text = delta.get("content")
                    if isinstance(text, str) and text:
                        yield text
        except (error.URLError, error.HTTPError, TimeoutError) as exc:
            raise RuntimeError(f"Dialogue provider stream failed: {exc}") from exc


class AgentFrameworkDialogueClient:
    def __init__(self) -> None:
        self.base_url = resolve_agent_framework_base_url(
            os.getenv("SUKUPOL_AGENT_FRAMEWORK_BASE_URL")
            or os.getenv("SUKUPOL_OPENAI_BASE_URL")
            or os.getenv("OLLAMA_ENDPOINT")
            or "http://127.0.0.1:8033/v1/"
        )
        self.model = (
            os.getenv("SUKUPOL_AGENT_FRAMEWORK_MODEL")
            or os.getenv("SUKUPOL_OPENAI_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or "local-model"
        )
        self.api_key = (
            os.getenv("SUKUPOL_AGENT_FRAMEWORK_API_KEY")
            or os.getenv("SUKUPOL_OPENAI_API_KEY")
            or os.getenv("OLLAMA_API_KEY")
            or "ollama"
        )

    def chat_json(
        self,
        agent_name: str,
        instructions: str,
        user_prompt: str,
        tools: Any = None,
    ) -> dict[str, Any]:
        return asyncio.run(self.achat_json(agent_name, instructions, user_prompt, tools=tools))

    async def achat_json(
        self,
        agent_name: str,
        instructions: str,
        user_prompt: str,
        tools: Any = None,
    ) -> dict[str, Any]:
        openai_module = self._load_openai_module()
        try:
            client_class = openai_module.OpenAIChatCompletionClient if tools else openai_module.OpenAIChatClient
            client = client_class(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
            )
            agent = client.as_agent(
                name=agent_name,
                instructions=instructions,
                tools=tools,
            )
            result = await agent.run(user_prompt)
        except Exception as exc:
            raise RuntimeError(f"Agent Framework request failed: {exc}") from exc
        return extract_json_payload(normalize_agent_result(result))

    async def astream_text(
        self,
        agent_name: str,
        instructions: str,
        user_prompt: str,
        tools: Any = None,
    ) -> AsyncIterator[str]:
        openai_module = self._load_openai_module()
        try:
            client_class = openai_module.OpenAIChatCompletionClient if tools else openai_module.OpenAIChatClient
            client = client_class(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
            )
            agent = client.as_agent(
                name=agent_name,
                instructions=instructions,
                tools=tools,
            )
            async for chunk in agent.run(user_prompt, stream=True):
                for text in iter_stream_text_parts(chunk):
                    yield text
        except Exception as exc:
            raise RuntimeError(f"Agent Framework stream failed: {exc}") from exc

    def _load_openai_module(self) -> Any:
        try:
            return importlib.import_module("agent_framework.openai")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Microsoft Agent Framework is not installed in this environment. Install the 'agent-framework' package "
                "or switch SUKUPOL_DIALOGUE_MODE to 'local-llm' or 'stub'."
            ) from exc


class NpcDialogueService:
    def __init__(self) -> None:
        self.mode = os.getenv("SUKUPOL_DIALOGUE_MODE", "stub")
        self.client = OpenAICompatibleDialogueClient()
        self.agent_framework_client = AgentFrameworkDialogueClient()

    def status(self) -> dict[str, str | None]:
        if self.mode == "agent-framework":
            provider_base_url = self.agent_framework_client.base_url
            provider_model = self.agent_framework_client.model
        elif self.mode == "local-llm":
            provider_base_url = self.client.base_url
            provider_model = self.client.model
        else:
            provider_base_url = None
            provider_model = None

        return {
            "mode": self.mode,
            "provider_base_url": provider_base_url,
            "provider_model": provider_model,
        }

    def talk(self, world: WorldContent, state: RunState, npc_id: str, player_message: str) -> DialogueReply:
        self.finalize_other_active_visits(world, state, npc_id)
        npc = world.npcs[npc_id]
        player_memory = load_npc_player_memory(state.player_id, npc_id)
        shared_knowledge = list_npc_shared_knowledge(npc_id)

        if self.mode in {"agent-framework", "local-llm"}:
            try:
                if self.mode == "agent-framework":
                    model_result = self._agent_framework_response(
                        world=world,
                        npc=npc,
                        state=state,
                        player_message=player_message,
                        player_memory=player_memory,
                        shared_knowledge=shared_knowledge,
                    )
                    source = "agent-framework"
                else:
                    model_result = self._local_llm_response(
                        npc=npc,
                        state=state,
                        player_message=player_message,
                        player_memory=player_memory,
                        shared_knowledge=shared_knowledge,
                    )
                    source = "local-llm"
                text = model_result.reply
            except RuntimeError as error:
                logger.exception("Dialogue provider failed in %s mode", self.mode)
                text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
                source = format_fallback_source(self.mode, error)
        else:
            text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
            source = "stub"

        summary, lore_updates = self._summarize_exchange(
            npc=npc,
            player_message=player_message,
            reply_text=text,
            prior_summary=player_memory.get("summary", ""),
        )
        upsert_npc_player_memory(state.player_id, npc_id, summary, player_message.strip(), text)
        upsert_conversation_summary(state.player_id, npc_id, summary)
        for lore_update in lore_updates:
            upsert_npc_shared_knowledge(
                npc_id=npc_id,
                category=lore_update.get("category", "conversation"),
                content=lore_update.get("content", ""),
                source="summary",
            )
        self.record_visit_turn(state, npc_id, npc["display_name"], player_message, text, source)
        return DialogueReply(
            npc_id=npc_id,
            npc_name=npc["display_name"],
            text=text,
            source=source,
        )

    async def stream_talk(
        self,
        world: WorldContent,
        state: RunState,
        npc_id: str,
        player_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        await self.afinalize_other_active_visits(world, state, npc_id)
        npc = world.npcs[npc_id]
        player_memory = load_npc_player_memory(state.player_id, npc_id)
        shared_knowledge = list_npc_shared_knowledge(npc_id)
        instructions = build_stream_dialogue_instructions(npc)
        user_prompt = build_stream_dialogue_user_prompt(state, player_message, player_memory, shared_knowledge)
        source = self.mode if self.mode in {"agent-framework", "local-llm"} else "stub"

        yield {
            "type": "start",
            "npc_id": npc_id,
            "npc_name": npc["display_name"],
            "source": source,
        }

        chunks: list[str] = []
        if self.mode == "stub":
            fallback_text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
            async for chunk in synthesize_stream_chunks(fallback_text):
                chunks.append(chunk)
                yield {"type": "chunk", "text": chunk}

        try:
            if self.mode == "agent-framework":
                tools = build_npc_agent_tools(world, state, npc, player_memory, shared_knowledge)
                async for chunk in self.agent_framework_client.astream_text(
                    agent_name=f"npc-{npc['id']}",
                    instructions=instructions,
                    user_prompt=user_prompt,
                    tools=tools,
                ):
                    chunks.append(chunk)
                    yield {"type": "chunk", "text": chunk}
                source = "agent-framework"
            elif self.mode == "local-llm":
                for chunk in self.client.stream_text(instructions, user_prompt):
                    chunks.append(chunk)
                    yield {"type": "chunk", "text": chunk}
                source = "local-llm"
            elif self.mode != "stub":
                raise RuntimeError(f"unsupported dialogue mode: {self.mode}")
        except RuntimeError as error:
            logger.exception("Dialogue stream provider failed in %s mode", self.mode)
            source = format_fallback_source(self.mode, error) if self.mode in {"agent-framework", "local-llm"} else "stub"
            if not chunks:
                fallback_text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
                async for chunk in synthesize_stream_chunks(fallback_text):
                    chunks.append(chunk)
                    yield {"type": "chunk", "text": chunk}

        text = "".join(chunks).strip()
        text = coerce_dialogue_reply_text(text)
        if not text:
            text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))

        summary, lore_updates = await self._asummarize_exchange(
            npc=npc,
            player_message=player_message,
            reply_text=text,
            prior_summary=player_memory.get("summary", ""),
        )
        upsert_npc_player_memory(state.player_id, npc_id, summary, player_message.strip(), text)
        upsert_conversation_summary(state.player_id, npc_id, summary)
        for lore_update in lore_updates:
            upsert_npc_shared_knowledge(
                npc_id=npc_id,
                category=lore_update.get("category", "conversation"),
                content=lore_update.get("content", ""),
                source="summary",
            )
        self.record_visit_turn(state, npc_id, npc["display_name"], player_message, text, source)

        yield {
            "type": "complete",
            "reply": {
                "npc_id": npc_id,
                "npc_name": npc["display_name"],
                "text": text,
                "source": source,
            },
        }

    def leave(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        return self._finalize_visit(world, state, npc_id)

    async def aleave(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        return await self._afinalize_visit(world, state, npc_id)

    def finalize_other_active_visits(self, world: WorldContent, state: RunState, active_npc_id: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            if npc_id == active_npc_id:
                continue
            entry = self._finalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    async def afinalize_other_active_visits(self, world: WorldContent, state: RunState, active_npc_id: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            if npc_id == active_npc_id:
                continue
            entry = await self._afinalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    def finalize_departed_visits(self, world: WorldContent, state: RunState) -> list[dict[str, Any]]:
        nearby_ids = {npc["id"] for npc in nearby_npcs(world, state)}
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            if npc_id in nearby_ids:
                continue
            entry = self._finalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    def finalize_all_active_visits(self, world: WorldContent, state: RunState) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            entry = self._finalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    def record_visit_turn(
        self,
        state: RunState,
        npc_id: str,
        npc_name: str,
        player_message: str,
        reply_text: str,
        source: str,
    ) -> None:
        visits = state.active_dialogue_visits or {}
        now = utc_now()
        visit = visits.get(npc_id)
        if not isinstance(visit, dict):
            visit = {
                "npc_id": npc_id,
                "npc_name": npc_name,
                "started_at": now,
                "updated_at": now,
                "turns": [],
            }

        turns = visit.get("turns")
        if not isinstance(turns, list):
            turns = []
            visit["turns"] = turns

        turns.append(
            {
                "player_message": player_message.strip(),
                "npc_reply": reply_text.strip(),
                "source": source,
                "timestamp": now,
            }
        )
        visit["npc_id"] = npc_id
        visit["npc_name"] = npc_name
        visit["updated_at"] = now
        visits[npc_id] = visit
        state.active_dialogue_visits = visits

    def _finalize_visit(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        visits = state.active_dialogue_visits or {}
        visit = visits.get(npc_id)
        if not isinstance(visit, dict):
            return None

        turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
        visits.pop(npc_id, None)
        state.active_dialogue_visits = visits
        if not turns:
            return None

        npc = world.npcs.get(npc_id, {"id": npc_id, "display_name": visit.get("npc_name", npc_id), "role": "contact"})
        visit_ended_at = utc_now()
        summary = self._summarize_visit(npc, visit, visit_ended_at)
        return create_npc_journal_entry(
            player_id=state.player_id,
            npc_id=npc_id,
            run_id=state.id,
            summary=summary,
            visit_started_at=str(visit.get("started_at") or visit_ended_at),
            visit_ended_at=visit_ended_at,
            turn_count=len(turns),
        )

    async def _afinalize_visit(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        visits = state.active_dialogue_visits or {}
        visit = visits.get(npc_id)
        if not isinstance(visit, dict):
            return None

        turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
        visits.pop(npc_id, None)
        state.active_dialogue_visits = visits
        if not turns:
            return None

        npc = world.npcs.get(npc_id, {"id": npc_id, "display_name": visit.get("npc_name", npc_id), "role": "contact"})
        visit_ended_at = utc_now()
        summary = await self._asummarize_visit(npc, visit, visit_ended_at)
        return create_npc_journal_entry(
            player_id=state.player_id,
            npc_id=npc_id,
            run_id=state.id,
            summary=summary,
            visit_started_at=str(visit.get("started_at") or visit_ended_at),
            visit_ended_at=visit_ended_at,
            turn_count=len(turns),
        )

    def _agent_framework_response(
        self,
        world: WorldContent,
        npc: dict[str, Any],
        state: RunState,
        player_message: str,
        player_memory: dict[str, str],
        shared_knowledge: list[dict[str, Any]],
    ) -> ModelDialogueResult:
        tools = build_npc_agent_tools(world, state, npc, player_memory, shared_knowledge)
        payload = self.agent_framework_client.chat_json(
            agent_name=f"npc-{npc['id']}",
            instructions=build_dialogue_instructions(npc),
            user_prompt=build_dialogue_user_prompt(state, player_message, player_memory, shared_knowledge),
            tools=tools,
        )
        return parse_model_dialogue_result(payload)

    def _local_llm_response(
        self,
        npc: dict[str, Any],
        state: RunState,
        player_message: str,
        player_memory: dict[str, str],
        shared_knowledge: list[dict[str, Any]],
    ) -> ModelDialogueResult:
        payload = self.client.chat_json(
            build_dialogue_instructions(npc),
            build_dialogue_user_prompt(state, player_message, player_memory, shared_knowledge),
        )
        return parse_model_dialogue_result(payload)

    def _summarize_exchange(
        self,
        npc: dict[str, Any],
        player_message: str,
        reply_text: str,
        prior_summary: str,
    ) -> tuple[str, list[dict[str, str]]]:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        instructions = (
            "Summarize one NPC conversation turn for future retrieval. "
            "Return strict JSON with keys: summary, lore_updates. "
            "summary must be a compact memory for this player and NPC. lore_updates must be an array of objects with category and content for durable non-player-specific facts only."
        )
        user_prompt = (
            f"NPC: {npc['display_name']}\n"
            f"Prior memory: {prior_summary or 'none'}\n"
            f"Player said: {player_message.strip()}\n"
            f"NPC replied: {reply_text.strip()}\n"
            "Do not include ephemeral phrasing or duplicate persona facts already obvious from the character description."
        )

        try:
            if self.mode == "agent-framework":
                payload = self.agent_framework_client.chat_json(
                    agent_name=f"npc-summary-{npc['id']}",
                    instructions=instructions,
                    user_prompt=user_prompt,
                )
            else:
                payload = self.client.chat_json(instructions, user_prompt)
        except RuntimeError:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        summary = str(payload.get("summary", "")).strip() or self._fallback_summary(player_message, reply_text, prior_summary)
        lore_updates = payload.get("lore_updates", [])
        if not isinstance(lore_updates, list):
            lore_updates = []

        normalized_lore: list[dict[str, str]] = []
        for entry in lore_updates[:4]:
            if not isinstance(entry, dict):
                continue
            category = str(entry.get("category", "conversation")).strip()
            content = str(entry.get("content", "")).strip()
            if not content:
                continue
            normalized_lore.append({"category": category, "content": content})
        return summary, normalized_lore

    async def _asummarize_exchange(
        self,
        npc: dict[str, Any],
        player_message: str,
        reply_text: str,
        prior_summary: str,
    ) -> tuple[str, list[dict[str, str]]]:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        instructions = (
            "Summarize one NPC conversation turn for future retrieval. "
            "Return strict JSON with keys: summary, lore_updates. "
            "summary must be a compact memory for this player and NPC. lore_updates must be an array of objects with category and content for durable non-player-specific facts only."
        )
        user_prompt = (
            f"NPC: {npc['display_name']}\n"
            f"Prior memory: {prior_summary or 'none'}\n"
            f"Player said: {player_message.strip()}\n"
            f"NPC replied: {reply_text.strip()}\n"
            "Do not include ephemeral phrasing or duplicate persona facts already obvious from the character description."
        )

        try:
            if self.mode == "agent-framework":
                payload = await self.agent_framework_client.achat_json(
                    agent_name=f"npc-summary-{npc['id']}",
                    instructions=instructions,
                    user_prompt=user_prompt,
                )
            else:
                payload = self.client.chat_json(instructions, user_prompt)
        except RuntimeError:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        summary = str(payload.get("summary", "")).strip() or self._fallback_summary(player_message, reply_text, prior_summary)
        lore_updates = payload.get("lore_updates", [])
        if not isinstance(lore_updates, list):
            lore_updates = []

        normalized_lore: list[dict[str, str]] = []
        for entry in lore_updates[:4]:
            if not isinstance(entry, dict):
                continue
            category = str(entry.get("category", "conversation")).strip()
            content = str(entry.get("content", "")).strip()
            if not content:
                continue
            normalized_lore.append({"category": category, "content": content})
        return summary, normalized_lore

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

    def _fallback_summary(self, player_message: str, reply_text: str, prior_summary: str) -> str:
        latest = f"Player asked about '{player_message.strip()}'. NPC replied '{reply_text.strip()}'."
        if prior_summary:
            return f"{prior_summary} {latest}"[:600]
        return latest[:600]

    def _summarize_visit(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> str:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_visit_summary(npc, visit)

        instructions = (
            "You are Journal Summary. Write one player-facing journal entry for a completed visit with an NPC. "
            "Return strict JSON with key: summary. "
            "summary must be 2 to 4 sentences in past tense, focused on what was discussed, any offers or warnings, and unresolved leads from this visit only. "
            "Do not invent facts, do not repeat generic character description, and do not mention the existence of an AI or model."
        )
        user_prompt = self._build_visit_summary_prompt(npc, visit, visit_ended_at)

        try:
            if self.mode == "agent-framework":
                payload = self.agent_framework_client.chat_json(
                    agent_name=JOURNAL_SUMMARY_AGENT_NAME,
                    instructions=instructions,
                    user_prompt=user_prompt,
                )
            else:
                payload = self.client.chat_json(instructions, user_prompt)
        except RuntimeError:
            return self._fallback_visit_summary(npc, visit)

        summary = str(payload.get("summary", "")).strip()
        return summary or self._fallback_visit_summary(npc, visit)

    async def _asummarize_visit(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> str:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_visit_summary(npc, visit)

        instructions = (
            "You are Journal Summary. Write one player-facing journal entry for a completed visit with an NPC. "
            "Return strict JSON with key: summary. "
            "summary must be 2 to 4 sentences in past tense, focused on what was discussed, any offers or warnings, and unresolved leads from this visit only. "
            "Do not invent facts, do not repeat generic character description, and do not mention the existence of an AI or model."
        )
        user_prompt = self._build_visit_summary_prompt(npc, visit, visit_ended_at)

        try:
            if self.mode == "agent-framework":
                payload = await self.agent_framework_client.achat_json(
                    agent_name=JOURNAL_SUMMARY_AGENT_NAME,
                    instructions=instructions,
                    user_prompt=user_prompt,
                )
            else:
                payload = self.client.chat_json(instructions, user_prompt)
        except RuntimeError:
            return self._fallback_visit_summary(npc, visit)

        summary = str(payload.get("summary", "")).strip()
        return summary or self._fallback_visit_summary(npc, visit)

    def _build_visit_summary_prompt(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> str:
        raw_turns = visit.get("turns")
        turns: list[dict[str, Any]] = raw_turns if isinstance(raw_turns, list) else []
        formatted_turns: list[str] = []
        for index, turn in enumerate(turns[-8:], start=max(len(turns) - 7, 1)):
            if not isinstance(turn, dict):
                continue
            player_message = str(turn.get("player_message", "")).strip()
            npc_reply = str(turn.get("npc_reply", "")).strip()
            if not player_message and not npc_reply:
                continue
            formatted_turns.append(
                f"Turn {index}:\nPlayer: {player_message or '...'}\nNPC: {npc_reply or '...'}"
            )

        transcript = "\n\n".join(formatted_turns) or "No transcript available."
        return (
            f"NPC: {npc.get('display_name', visit.get('npc_name', 'Unknown contact'))}\n"
            f"Role: {npc.get('role', 'contact')}\n"
            f"Visit started: {visit.get('started_at') or 'unknown'}\n"
            f"Visit ended: {visit_ended_at}\n"
            f"Turn count: {len(turns)}\n\n"
            f"Transcript:\n{transcript}"
        )

    def _fallback_visit_summary(self, npc: dict[str, Any], visit: dict[str, Any]) -> str:
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


def build_dialogue_instructions(npc: dict[str, Any]) -> str:
    return (
        f"{npc['system_prompt']}\n"
        "Stay in character, keep responses grounded in the provided game state, and never invent mechanics or places that are not in context. "
        "Use the available tools when you need exact live state or inventory; prefer tool results over guessing. "
        "Return strict JSON with key: reply."
    )


def build_stream_dialogue_instructions(npc: dict[str, Any]) -> str:
    return (
        f"{npc['system_prompt']}\n"
        "Stay in character, keep responses grounded in the provided game state, and never invent mechanics or places that are not in context. "
        "Use the available tools when you need exact live state or inventory; prefer tool results over guessing. "
        "Reply with plain in-character prose only. Do not wrap the response in JSON, markdown fences, or bullet lists unless the player explicitly asks for that format."
    )


def build_npc_agent_tools(
    world: WorldContent,
    state: RunState,
    npc: dict[str, Any],
    player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]],
) -> tuple[Any, ...]:
    def get_player_run_context() -> str:
        """Get the player's exact current run state, location, and nearby NPCs."""
        location = resolve_location(world, state.location_id)
        payload = {
            "player": {
                "id": state.player_id,
                "name": state.player_name,
                "hp": state.hp,
                "max_hp": state.max_hp,
                "gold": state.gold,
                "facing": state.facing,
                "run_depth": state.run_depth,
                "status": state.status,
                "in_combat": state.in_combat,
            },
            "location": {
                "id": location["id"],
                "name": location["name"],
                "description": location["description"],
                "type": location.get("location_type"),
                "biome_id": location.get("biome_id"),
                "floor_number": location.get("floor_number"),
            },
            "nearby_npcs": [
                {
                    "id": nearby_npc["id"],
                    "display_name": nearby_npc["display_name"],
                    "role": nearby_npc["role"],
                    "distance": nearby_npc["distance"],
                }
                for nearby_npc in nearby_npcs(world, state)
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    def get_player_inventory() -> str:
        """Get the player's current inventory with exact item names, quantities, and equipped state."""
        payload = {
            "equipped_weapon": state.equipped_weapon,
            "inventory": [
                {
                    "item_id": entry["item_id"],
                    "name": world.items.get(entry["item_id"], {}).get("name", entry["item_id"]),
                    "item_type": world.items.get(entry["item_id"], {}).get("item_type"),
                    "quantity": entry.get("quantity", 1),
                    "equipped": bool(entry.get("equipped", False)),
                    "description": world.items.get(entry["item_id"], {}).get("description", ""),
                }
                for entry in state.inventory or []
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    def get_conversation_context() -> str:
        """Get the NPC's remembered player summary and current shared knowledge facts."""
        payload = {
            "prior_memory": player_memory.get("summary", "") or "none",
            "shared_knowledge": [
                {
                    "category": entry.get("category", "conversation"),
                    "content": entry.get("content", ""),
                }
                for entry in shared_knowledge[:8]
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    return (
        get_player_run_context,
        get_player_inventory,
        get_conversation_context,
    )


def build_dialogue_user_prompt(
    state: RunState,
    player_message: str,
    player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]],
) -> str:
    knowledge_text = "\n".join(f"- {entry['category']}: {entry['content']}" for entry in shared_knowledge[:6])
    return (
        f"Player: {state.player_name}\n"
        f"Location: {state.location_id}\n"
        f"Depth reached: {state.run_depth}\n"
        f"HP: {state.hp}/{state.max_hp}\n"
        f"Gold: {state.gold}\n"
        f"Prior memory: {player_memory.get('summary', '') or 'none'}\n"
        f"Shared knowledge:\n{knowledge_text or '- none'}\n\n"
        f"Player message: {player_message.strip()}\n\n"
        "Respond as JSON only."
    )


def build_stream_dialogue_user_prompt(
    state: RunState,
    player_message: str,
    player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]],
) -> str:
    knowledge_text = "\n".join(f"- {entry['category']}: {entry['content']}" for entry in shared_knowledge[:6])
    return (
        f"Player: {state.player_name}\n"
        f"Location: {state.location_id}\n"
        f"Depth reached: {state.run_depth}\n"
        f"HP: {state.hp}/{state.max_hp}\n"
        f"Gold: {state.gold}\n"
        f"Prior memory: {player_memory.get('summary', '') or 'none'}\n"
        f"Shared knowledge:\n{knowledge_text or '- none'}\n\n"
        f"Player message: {player_message.strip()}\n\n"
        "Respond with plain in-character prose only."
    )


def resolve_chat_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def resolve_agent_framework_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/"
    if normalized.endswith("/chat/completions"):
        return f"{normalized[: -len('/chat/completions')]}/"
    return f"{normalized}/v1/"


def format_fallback_source(mode: str, error: Exception) -> str:
    detail = str(error).strip().replace("\n", " ")
    if len(detail) > 96:
        detail = f"{detail[:93]}..."
    return f"{mode}-fallback: {detail}" if detail else f"{mode}-fallback"


def parse_model_dialogue_result(payload: dict[str, Any]) -> ModelDialogueResult:
    reply = str(payload.get("reply", "")).strip()
    if not reply:
        raise RuntimeError("Dialogue provider returned an empty reply")
    return ModelDialogueResult(reply=reply)


def coerce_dialogue_reply_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped

    try:
        payload = extract_json_payload(stripped)
    except RuntimeError:
        return stripped

    reply = payload.get("reply")
    if reply is None:
        return stripped

    normalized = str(reply).strip()
    return normalized or stripped


def normalize_agent_result(result: Any) -> str:
    text = getattr(result, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    if isinstance(result, str):
        return result

    output = getattr(result, "output", None)
    if isinstance(output, str) and output.strip():
        return output

    messages = getattr(result, "messages", None)
    if isinstance(messages, list):
        for message in reversed(messages):
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content

    return str(result)


def iter_stream_text_parts(chunk: Any) -> Iterator[str]:
    contents = getattr(chunk, "contents", None) or []
    if contents:
      yielded = False
      for content in contents:
          content_type = getattr(content, "type", None)
          if content_type in {"text_reasoning", "usage"}:
              continue

          text = getattr(content, "text", None)
          if isinstance(text, str) and text:
              yielded = True
              yield text

      if yielded:
          return

    text = getattr(chunk, "text", None)
    if isinstance(text, str) and text:
        yield text


async def synthesize_stream_chunks(text: str) -> AsyncIterator[str]:
    for chunk in split_text_for_stream(text):
        yield chunk
        await asyncio.sleep(0.012)


def split_text_for_stream(text: str, target_size: int = 18) -> list[str]:
    words = text.split(" ")
    if len(words) <= 1:
        return [text]

    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) > target_size and current:
            chunks.append(f"{current} ")
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def extract_json_payload(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1]
        if stripped.endswith("```"):
            stripped = stripped.rsplit("```", 1)[0]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("Dialogue provider did not return JSON")
    try:
        return json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("Dialogue provider returned invalid JSON") from exc
