from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, AsyncIterator

from app.agents import AgentExecutor, AgentInvocation
from app.content import load_world_content
from app.db.connection import initialize_database
from app.db.runs import ensure_player_profile
from app.dialogue import NpcDialogueService
from app.dialogue.normalize import format_fallback_source
from app.game import create_run
from app.services.run_state import stream_talk_events


async def _raising_async_gen() -> AsyncIterator[str]:
    """Async generator that raises RuntimeError on first iteration."""
    raise RuntimeError("internal: httpx connect to 10.0.0.5:8033 failed")
    yield  # noqa: unreachable — required for Python to treat as async generator


class _RaisingFakeExecutor(AgentExecutor):
    """Fake executor that raises RuntimeError with internal details."""

    def __init__(self) -> None:
        super().__init__(mode="local-llm")

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        raise RuntimeError("internal: httpx connect to 10.0.0.5:8033 failed")

    async def ainvoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        raise RuntimeError("internal: httpx connect to 10.0.0.5:8033 failed")

    async def astream_text(self, invocation: AgentInvocation) -> AsyncIterator[str]:
        gen = _raising_async_gen()
        async for chunk in gen:
            yield chunk


class DialogueErrorLeakTests(unittest.TestCase):
    """AF1: internal error strings must not leak to the client."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()
        cls.secret = "10.0.0.5"

    def setUp(self) -> None:
        # Each test gets its own temp DB so we can persist without polluting
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmp_dir.name) / "sukupol.db"
        self._old_db_path = os.environ.get("SUKUPOL_DB_PATH")
        os.environ["SUKUPOL_DB_PATH"] = str(self._db_path)

        initialize_database(self.world, db_path=self._db_path)
        self.state = create_run(self.world, "Wayfarer")

        # Ensure player profile exists in DB so stream_persist FK passes
        ensure_player_profile(self.state.player_id, "Wayfarer", db_path=self._db_path)

        self.error = RuntimeError("internal: httpx connect to 10.0.0.5:8033 failed")

    def tearDown(self) -> None:
        if self._old_db_path is None:
            os.environ.pop("SUKUPOL_DB_PATH", None)
        else:
            os.environ["SUKUPOL_DB_PATH"] = self._old_db_path
        self._tmp_dir.cleanup()

    # ── format_fallback_source ────────────────────────────────────────

    def test_format_fallback_source_omits_error_detail(self) -> None:
        """format_fallback_source returns '{mode}-fallback' with no trace of the internal error."""
        result = format_fallback_source("local-llm", self.error)
        self.assertEqual(result, "local-llm-fallback")
        self.assertNotIn(self.secret, result)
        self.assertNotIn("httpx", result)

    def test_format_fallback_source_agent_framework(self) -> None:
        """Same protection applies in agent-framework mode."""
        result = format_fallback_source("agent-framework", self.error)
        self.assertEqual(result, "agent-framework-fallback")
        self.assertNotIn(self.secret, result)

    # ── stream_talk_events error event ────────────────────────────────

    def test_stream_error_event_is_generic(self) -> None:
        """The error event detail is 'Dialogue unavailable' with no internal leak."""
        dialogue_svc = NpcDialogueService(executor=_RaisingFakeExecutor())

        # Monkey-patch stream_talk to re-raise so stream_talk_events catches it
        async def _raising(*_a: Any, **_kw: Any) -> AsyncIterator[dict[str, Any]]:
            raise RuntimeError("internal: httpx connect to 10.0.0.5:8033 failed")
            yield  # noqa: unreachable — makes this an async generator

        original = dialogue_svc.stream_talk  # type: ignore[assignment]
        dialogue_svc.stream_talk = _raising  # type: ignore[assignment]

        try:

            async def _collect() -> list[dict[str, Any]]:
                events: list[dict[str, Any]] = []
                async for raw_line in stream_talk_events(
                    self.world, self.state, "marta-innkeeper", "hello", dialogue_svc,
                ):
                    events.append(json.loads(raw_line))
                return events

            events = asyncio.run(_collect())
        finally:
            dialogue_svc.stream_talk = original

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "error")
        self.assertEqual(events[0]["detail"], "Dialogue unavailable")

        # The secret must NOT appear anywhere in the NDJSON output
        output = "".join(json.dumps(e) for e in events)
        self.assertNotIn(self.secret, output)
        self.assertNotIn("httpx", output)

    # ── RunSnapshot source (full stream path) ─────────────────────────

    def test_snapshot_source_does_not_leak_internal_error(self) -> None:
        """RunSnapshot.dialogue.source must not contain internal error details."""
        dialogue_svc = NpcDialogueService(executor=_RaisingFakeExecutor())

        async def _stream_to_snapshot() -> dict[str, Any] | None:
            snapshot: dict[str, Any] | None = None
            async for raw_line in stream_talk_events(
                self.world, self.state, "marta-innkeeper", "hello", dialogue_svc,
            ):
                event = json.loads(raw_line)
                if event["type"] == "snapshot":
                    snapshot = event["snapshot"]
            return snapshot

        snapshot = asyncio.run(_stream_to_snapshot())
        self.assertIsNotNone(snapshot, "Expected a snapshot event from the stream")

        dialogue = snapshot.get("dialogue") or {}
        source = dialogue.get("source", "")

        self.assertEqual(source, "local-llm-fallback")
        self.assertNotIn(self.secret, source)
        self.assertNotIn("httpx", source)


if __name__ == "__main__":
    unittest.main()
