from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from .providers import AgentFrameworkClient, OpenAICompatibleAgentClient


@dataclass(frozen=True)
class AgentInvocation:
    agent_name: str
    instructions: str
    user_prompt: str
    tools: tuple[Any, ...] = field(default_factory=tuple)


class AgentExecutor:
    def __init__(
        self,
        mode: str | None = None,
        text_client: OpenAICompatibleAgentClient | None = None,
        agent_framework_client: AgentFrameworkClient | None = None,
    ) -> None:
        self.mode = mode or os.getenv("SUKUPOL_DIALOGUE_MODE", "stub")
        self.text_client = text_client or OpenAICompatibleAgentClient()
        self.agent_framework_client = agent_framework_client if self.mode == "agent-framework" else agent_framework_client

    def status(self) -> dict[str, str | None]:
        if self.mode == "agent-framework":
            agent_client = self._require_agent_framework_client()
            provider_base_url = agent_client.base_url
            provider_model = agent_client.model
        elif self.mode == "local-llm":
            provider_base_url = self.text_client.base_url
            provider_model = self.text_client.model
        else:
            provider_base_url = None
            provider_model = None
        return {
            "mode": self.mode,
            "provider_base_url": provider_base_url,
            "provider_model": provider_model,
        }

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        if self.mode == "agent-framework":
            return self._require_agent_framework_client().chat_json(
                agent_name=invocation.agent_name,
                instructions=invocation.instructions,
                user_prompt=invocation.user_prompt,
                tools=invocation.tools,
            )
        if self.mode == "local-llm":
            return self.text_client.chat_json(invocation.instructions, invocation.user_prompt)
        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    async def ainvoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        if self.mode == "agent-framework":
            return await self._require_agent_framework_client().achat_json(
                agent_name=invocation.agent_name,
                instructions=invocation.instructions,
                user_prompt=invocation.user_prompt,
                tools=invocation.tools,
            )
        if self.mode == "local-llm":
            return self.text_client.chat_json(invocation.instructions, invocation.user_prompt)
        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    def invoke_text(self, invocation: AgentInvocation) -> str:
        if self.mode == "agent-framework":
            return self._require_agent_framework_client().chat_text(
                agent_name=invocation.agent_name,
                instructions=invocation.instructions,
                user_prompt=invocation.user_prompt,
                tools=invocation.tools,
            )
        if self.mode == "local-llm":
            return self.text_client.chat_text(invocation.instructions, invocation.user_prompt)
        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    async def astream_text(self, invocation: AgentInvocation) -> AsyncIterator[str]:
        if self.mode == "agent-framework":
            async for chunk in self._require_agent_framework_client().astream_text(
                agent_name=invocation.agent_name,
                instructions=invocation.instructions,
                user_prompt=invocation.user_prompt,
                tools=invocation.tools,
            ):
                yield chunk
            return

        if self.mode == "local-llm":
            for chunk in self.text_client.stream_text(invocation.instructions, invocation.user_prompt):
                yield chunk
            return

        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    def _require_agent_framework_client(self) -> AgentFrameworkClient:
        if self.agent_framework_client is None:
            self.agent_framework_client = AgentFrameworkClient()
        return self.agent_framework_client
