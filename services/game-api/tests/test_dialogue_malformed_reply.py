"""Test malformed reply handling in the dialogue talk path.

AF8 residual gaps: empty reply, missing keys, and executor exception
all fall through to stub fallback without leaking error internals.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.agents import AgentExecutor, AgentInvocation
from app.content import load_world_content
from app.db.connection import initialize_database
from app.db.runs import ensure_player_profile
from app.dialogue import NpcDialogueService, parse_model_dialogue_result
from app.game import create_run


class _EmptyReplyExecutor(AgentExecutor):
    """Fake executor that returns an empty dict (no known text key)."""

    def __init__(self) -> None:
        super().__init__(mode="agent-framework")

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, str]:
        return {}


class _UnrelatedKeysExecutor(AgentExecutor):
    """Fake executor that returns a dict with only unknown keys."""

    def __init__(self) -> None:
        super().__init__(mode="agent-framework")

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, str]:
        return {"unrelated": "x"}


class _RaisingExecutor(AgentExecutor):
    """Fake executor that raises RuntimeError."""

    def __init__(self) -> None:
        super().__init__(mode="agent-framework")

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, str]:
        raise RuntimeError("agent-framework boom")


class DialogueMalformedReplyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()

    def setUp(self) -> None:
        # Isolated temp DB so persistence FK constraints are satisfied
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmp_dir.name) / "sukupol.db"
        self._old_db_path = os.environ.get("SUKUPOL_DB_PATH")
        os.environ["SUKUPOL_DB_PATH"] = str(self._db_path)

        initialize_database(self.world, db_path=self._db_path)
        self.state = create_run(self.world, "Wayfarer")
        ensure_player_profile(
            self.state.player_id, "Wayfarer", db_path=self._db_path,
        )
        self.npc_id = "marta-innkeeper"

    def tearDown(self) -> None:
        if self._old_db_path is None:
            os.environ.pop("SUKUPOL_DB_PATH", None)
        else:
            os.environ["SUKUPOL_DB_PATH"] = self._old_db_path
        self._tmp_dir.cleanup()

    def test_empty_llm_reply_falls_back(self) -> None:
        """Empty {} from executor -> parse_model_dialogue_result raises
        RuntimeError -> _talk_model_reply catches and returns stub fallback.
        The source field must NOT leak {} or RuntimeError text.
        """
        executor = _EmptyReplyExecutor()
        service = NpcDialogueService(executor=executor)
        reply = service.talk(self.world, self.state, self.npc_id, "hello")
        self.assertTrue(reply.text)
        self.assertNotEqual(reply.text, "{}")
        self.assertNotIn("{}", reply.source)
        self.assertNotIn("RuntimeError", reply.source)

    def test_all_known_keys_missing_falls_back(self) -> None:
        """Dict with only unknown keys -> parse_model_dialogue_result
        raises RuntimeError (no known key found) -> talk path falls
        back to stub.
        """
        with self.assertRaises(RuntimeError):
            parse_model_dialogue_result({"unrelated": "x"})
        executor = _UnrelatedKeysExecutor()
        service = NpcDialogueService(executor=executor)
        reply = service.talk(self.world, self.state, self.npc_id, "hello")
        self.assertTrue(reply.text)

    def test_llm_raises_falls_back_without_leak(self) -> None:
        """Executor raises RuntimeError -> fallback reply without error
        detail leaking to the client (AF1 leak-seal contract).
        """
        executor = _RaisingExecutor()
        service = NpcDialogueService(executor=executor)
        reply = service.talk(self.world, self.state, self.npc_id, "hello")
        self.assertTrue(reply.text)
        self.assertNotIn("boom", reply.text)
        self.assertNotIn("boom", reply.source)


if __name__ == "__main__":
    unittest.main()
