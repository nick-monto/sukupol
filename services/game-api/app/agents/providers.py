from __future__ import annotations

import asyncio
import importlib
import json
import os
from typing import Any, AsyncIterator, Iterator
from urllib import error, request


class OpenAICompatibleAgentClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("SUKUPOL_OPENAI_BASE_URL", "http://127.0.0.1:8033")
        self.model = os.getenv("SUKUPOL_OPENAI_MODEL", "agent-framework")
        self.api_key = os.getenv("SUKUPOL_OPENAI_API_KEY", "")
        self.timeout = float(os.getenv("SUKUPOL_OPENAI_TIMEOUT", "20"))
        self.temperature = float(os.getenv("SUKUPOL_OPENAI_TEMPERATURE", "1.0"))

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return extract_json_payload(self.chat_text(system_prompt, user_prompt))

    def chat_text(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        return self._post(payload)

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


class AgentFrameworkClient:
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
        return extract_json_payload(self.chat_text(agent_name, instructions, user_prompt, tools=tools))

    def chat_text(
        self,
        agent_name: str,
        instructions: str,
        user_prompt: str,
        tools: Any = None,
    ) -> str:
        return asyncio.run(self.achat_text(agent_name, instructions, user_prompt, tools=tools))

    async def achat_json(
        self,
        agent_name: str,
        instructions: str,
        user_prompt: str,
        tools: Any = None,
    ) -> dict[str, Any]:
        return extract_json_payload(await self.achat_text(agent_name, instructions, user_prompt, tools=tools))

    async def achat_text(
        self,
        agent_name: str,
        instructions: str,
        user_prompt: str,
        tools: Any = None,
    ) -> str:
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
        return normalize_agent_result(result)

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


def normalize_agent_result(result: Any) -> str:
    direct_text = _extract_text_value(result)
    if direct_text:
        return direct_text

    if isinstance(result, str):
        return result

    output = getattr(result, "output", None)
    output_text = _extract_text_value(output)
    if output_text:
        return output_text

    messages = getattr(result, "messages", None)
    if isinstance(messages, list):
        for message in reversed(messages):
            message_text = _extract_text_value(message)
            if message_text:
                return message_text

    return str(result)


def _extract_text_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float, bool, bytes)):
        return ""

    if isinstance(value, dict):
        for key in ("text", "content", "message", "output", "root"):
            nested = _extract_text_value(value.get(key))
            if nested:
                return nested
        return ""

    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            nested = _extract_text_value(item)
            if nested:
                parts.append(nested)
        return "\n".join(parts).strip()

    for attr in ("text", "content", "message", "output", "root"):
        nested = _extract_text_value(getattr(value, attr, None))
        if nested:
            return nested

    return ""


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