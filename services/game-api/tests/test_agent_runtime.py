from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

from app.agents import AgentExecutor, AgentInvocation, list_registered_agents, list_registered_tools
from app.agents.providers import normalize_agent_result


class _FakeTextClient:
    def __init__(self) -> None:
        self.base_url = "http://text-client"
        self.model = "local-text"
        self.calls: list[tuple[str, str, object]] = []

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, str]:
        self.calls.append((system_prompt, user_prompt, "json"))
        return {"reply": "json-ok"}

    def chat_text(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt, "text"))
        return "text-ok"

    def stream_text(self, system_prompt: str, user_prompt: str):
        self.calls.append((system_prompt, user_prompt, "stream"))
        yield "chunk-a"
        yield "chunk-b"

    async def astream_text(self, system_prompt: str, user_prompt: str):
        self.calls.append((system_prompt, user_prompt, "stream"))
        yield "chunk-a"
        yield "chunk-b"


class AgentRuntimeTests(unittest.TestCase):
    def test_local_executor_uses_text_client(self) -> None:
        text_client = _FakeTextClient()  # type: ignore[arg-type]
        executor = AgentExecutor(mode="local-llm", text_client=text_client)
        invocation = AgentInvocation("demo", "system", "user", tools=(lambda: "{}",))

        self.assertEqual({"reply": "json-ok"}, executor.invoke_json(invocation))
        self.assertEqual("text-ok", executor.invoke_text(invocation))
        self.assertEqual(["chunk-a", "chunk-b"], asyncio.run(self._collect_stream(executor, invocation)))
        self.assertEqual("local-llm", executor.status()["mode"])
        self.assertEqual("http://text-client", executor.status()["provider_base_url"])

    @patch("app.agents.runtime._load_openai_module")
    def test_agent_framework_executor_uses_framework_client(self, mock_load) -> None:
        _mock_result = SimpleNamespace(
            output=SimpleNamespace(content=[SimpleNamespace(text='{"reply": "agent-json"}')])
        )
        _stream_chunks = [SimpleNamespace(contents=[SimpleNamespace(type="text", text="streamed-reply")])]  # type: ignore[misc]

        class _MockAgent:
            async def run(self, prompt: str, stream=False):  # noqa: ARG002
                return _mock_result
            async def run_stream(self, prompt: str):  # type: ignore[misc]
                for chunk in _stream_chunks:
                    yield chunk

        def make_client(**kwargs):  # noqa: ANN003
            agent = _MockAgent()
            # ponytail: runtime.py calls agent.run() — mock returns value; stream path uses run_stream
            return SimpleNamespace(as_agent=lambda **kw: agent)  # noqa: ARG005

        mock_module = SimpleNamespace(
            OpenAIChatCompletionClient=make_client,
            OpenAIChatClient=make_client,
        )
        mock_load.return_value = mock_module

        executor = AgentExecutor(mode="agent-framework")
        invocation = AgentInvocation("demo", "system", "user", tools=(lambda: "{}",))

        self.assertEqual({"reply": "agent-json"}, executor.invoke_json(invocation))
        self.assertEqual({"reply": "agent-json"}, asyncio.run(executor.ainvoke_json(invocation)))
        self.assertEqual("{\"reply\": \"agent-json\"}", executor.invoke_text(invocation))

    def test_registry_contains_dialogue_and_combat_entries(self) -> None:
        registered_agents = list_registered_agents()
        registered_tools = list_registered_tools()

        self.assertIn("dialogue.reply", registered_agents)
        self.assertIn("combat.parley_reply", registered_agents)
        self.assertIn("journal.summary.exchange", registered_agents)
        self.assertIn("quest.offer", registered_agents)
        self.assertIn("dialogue.reply", registered_tools)
        self.assertIn("combat.parley_open", registered_tools)

    def test_normalize_agent_result_reads_nested_message_parts(self) -> None:
        result = SimpleNamespace(
            messages=[
                SimpleNamespace(
                    content=[
                        SimpleNamespace(root=SimpleNamespace(text='{"reply": "Marta: Keep your lantern high."}'))
                    ]
                )
            ]
        )

        self.assertEqual('{"reply": "Marta: Keep your lantern high."}', normalize_agent_result(result))

    def test_normalize_agent_result_reads_nested_output_parts(self) -> None:
        result = SimpleNamespace(
            output=[
                SimpleNamespace(content=[SimpleNamespace(text='{"reply": "Marta: The stairs shift."}')])
            ]
        )

        self.assertEqual('{"reply": "Marta: The stairs shift."}', normalize_agent_result(result))

    async def _collect_stream(self, executor: AgentExecutor, invocation: AgentInvocation) -> list[str]:
        chunks: list[str] = []
        async for chunk in executor.astream_text(invocation):
            chunks.append(chunk)
        return chunks


if __name__ == "__main__":
    unittest.main()