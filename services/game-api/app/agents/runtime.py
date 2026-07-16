from __future__ import annotations

import asyncio
import importlib
import os
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from .config import resolve_base_url
from .providers import (
    OpenAICompatibleAgentClient,
    extract_json_payload,
    iter_stream_text_parts,
    normalize_agent_result,
)
logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class AgentInvocation:
    agent_name: str
    instructions: str
    user_prompt: str
    tools: tuple[Any, ...] = field(default_factory=tuple)


def _get_framework_config() -> tuple[str, str, str]:
    """Return (base_url, model, api_key) for agent-framework mode."""
    base_url = (
        os.getenv("SUKUPOL_AGENT_FRAMEWORK_BASE_URL")
        or os.getenv("SUKUPOL_OPENAI_BASE_URL")
        or os.getenv("OLLAMA_ENDPOINT")
        or "http://127.0.0.1:8033/v1/"
    )
    normalized = resolve_base_url(base_url, for_framework=True)
    model = (
        os.getenv("SUKUPOL_AGENT_FRAMEWORK_MODEL")
        or os.getenv("SUKUPOL_OPENAI_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or "local-model"
    )
    api_key = (
        os.getenv("SUKUPOL_AGENT_FRAMEWORK_API_KEY")
        or os.getenv("SUKUPOL_OPENAI_API_KEY")
        or os.getenv("OLLAMA_API_KEY")
        or "ollama"
    )
    return normalized, model, api_key


def _load_openai_module() -> Any:
    try:
        return importlib.import_module("agent_framework.openai")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Microsoft Agent Framework is not installed in this environment. Install the 'agent-framework' package "
            "or switch SUKUPOL_DIALOGUE_MODE to 'local-llm' or 'stub'."
        ) from exc


class AgentExecutor:
    def __init__(
        self,
        mode: str | None = None,
        text_client: OpenAICompatibleAgentClient | None = None,
    ) -> None:
        self.mode = mode or os.getenv("SUKUPOL_DIALOGUE_MODE", "stub")
        logger.info("agent_executor_ready", extra={"mode": self.mode})
        self.text_client = text_client or OpenAICompatibleAgentClient()
        # ponytail: lazy-init framework config on first use, not at construction
        self._fw_config: tuple[str, str, str] | None = None

    @property
    def _config(self) -> tuple[str, str, str]:
        if self._fw_config is None:
            self._fw_config = _get_framework_config()
        return self._fw_config

    def status(self) -> dict[str, str | None]:
        if self.mode == "agent-framework":
            base_url, model, _ = self._config
            provider_base_url, provider_model = base_url, model
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
            text = asyncio.run(self._afw_invoke_text(invocation))
            return extract_json_payload(text)
        if self.mode == "local-llm":
            return self.text_client.chat_json(invocation.instructions, invocation.user_prompt)
        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    async def ainvoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        if self.mode == "agent-framework":
            text = await self._afw_invoke_text(invocation)
            return extract_json_payload(text)
        if self.mode == "local-llm":
            return await self.text_client.achat_json(invocation.instructions, invocation.user_prompt)
        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    def invoke_text(self, invocation: AgentInvocation) -> str:
        if self.mode == "agent-framework":
            return asyncio.run(self._afw_invoke_text(invocation))
        if self.mode == "local-llm":
            return self.text_client.chat_text(invocation.instructions, invocation.user_prompt)
        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    async def astream_text(self, invocation: AgentInvocation) -> AsyncIterator[str]:
        if self.mode == "agent-framework":
            async for chunk in self._afw_stream_text(invocation):
                yield chunk
            return

        if self.mode == "local-llm":
            async for chunk in self.text_client.astream_text(invocation.instructions, invocation.user_prompt):
                yield chunk
            return

        raise RuntimeError(f"unsupported agent mode: {self.mode}")

    # -- agent-framework internals (inlined from AgentFrameworkClient)

    async def _afw_invoke_text(self, invocation: AgentInvocation) -> str:
        openai_module = _load_openai_module()
        base_url, model, api_key = self._config
        try:
            client_class = (
                openai_module.OpenAIChatCompletionClient if invocation.tools else openai_module.OpenAIChatClient
            )
            client = client_class(api_key=api_key, base_url=base_url, model=model)
            agent = client.as_agent(
                name=invocation.agent_name,
                instructions=invocation.instructions,
                tools=invocation.tools,
            )
            result = await agent.run(invocation.user_prompt)
            logger.debug("agent_framework_invoked", extra={"agent": invocation.agent_name, "stream": False})
        except Exception as exc:
            logger.warning("agent-framework call failed: %s: %s", type(exc).__name__, exc)
            raise RuntimeError(f"Agent Framework request failed: {exc}") from exc
        return normalize_agent_result(result)

    async def _afw_stream_text(self, invocation: AgentInvocation) -> AsyncIterator[str]:
        openai_module = _load_openai_module()
        base_url, model, api_key = self._config
        try:
            client_class = (
                openai_module.OpenAIChatCompletionClient if invocation.tools else openai_module.OpenAIChatClient
            )
            client = client_class(api_key=api_key, base_url=base_url, model=model)
            agent = client.as_agent(
                name=invocation.agent_name,
                instructions=invocation.instructions,
                tools=invocation.tools,
            )
            logger.debug("agent_framework_invoked", extra={"agent": invocation.agent_name, "stream": True})
            async for chunk in agent.run(invocation.user_prompt, stream=True):  # type: ignore[union-attr]
                for text in iter_stream_text_parts(chunk):
                    yield text
        except Exception as exc:
            logger.warning("agent-framework call failed: %s: %s", type(exc).__name__, exc)
            raise RuntimeError(f"Agent Framework stream failed: {exc}") from exc
