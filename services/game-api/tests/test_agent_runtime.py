from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

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


class _FakeAgentFrameworkClient:
    def __init__(self) -> None:
        self.base_url = "http://af-client"
        self.model = "af-model"
        self.calls: list[tuple[str, str, str, object, str]] = []

    def chat_json(self, agent_name: str, instructions: str, user_prompt: str, tools=None) -> dict[str, str]:
        self.calls.append((agent_name, instructions, user_prompt, tools, "json"))
        return {"reply": "agent-json"}

    async def achat_json(self, agent_name: str, instructions: str, user_prompt: str, tools=None) -> dict[str, str]:
        self.calls.append((agent_name, instructions, user_prompt, tools, "ajson"))
        return {"reply": "agent-async-json"}

    def chat_text(self, agent_name: str, instructions: str, user_prompt: str, tools=None) -> str:
        self.calls.append((agent_name, instructions, user_prompt, tools, "text"))
        return "agent-text"

    async def astream_text(self, agent_name: str, instructions: str, user_prompt: str, tools=None):
        self.calls.append((agent_name, instructions, user_prompt, tools, "stream"))
        yield "agent-chunk"


class AgentRuntimeTests(unittest.TestCase):
    def test_local_executor_uses_text_client(self) -> None:
        text_client = _FakeTextClient()
        executor = AgentExecutor(mode="local-llm", text_client=text_client)
        invocation = AgentInvocation("demo", "system", "user", tools=(lambda: "{}",))

        self.assertEqual({"reply": "json-ok"}, executor.invoke_json(invocation))
        self.assertEqual("text-ok", executor.invoke_text(invocation))
        self.assertEqual(["chunk-a", "chunk-b"], asyncio.run(self._collect_stream(executor, invocation)))
        self.assertEqual("local-llm", executor.status()["mode"])
        self.assertEqual("http://text-client", executor.status()["provider_base_url"])

    def test_agent_framework_executor_uses_framework_client(self) -> None:
        framework_client = _FakeAgentFrameworkClient()
        executor = AgentExecutor(mode="agent-framework", agent_framework_client=framework_client)
        invocation = AgentInvocation("demo", "system", "user", tools=(lambda: "{}",))

        self.assertEqual({"reply": "agent-json"}, executor.invoke_json(invocation))
        self.assertEqual({"reply": "agent-async-json"}, asyncio.run(executor.ainvoke_json(invocation)))
        self.assertEqual("agent-text", executor.invoke_text(invocation))
        self.assertEqual(["agent-chunk"], asyncio.run(self._collect_stream(executor, invocation)))
        self.assertTrue(any(call[0] == "demo" and call[4] == "json" for call in framework_client.calls))

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