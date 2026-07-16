from __future__ import annotations

# ponytail: TODO — uses synchronous urllib.request.urlopen() blocking event loop during LLM inference.
# Future migration target: aiohttp/httpx.AsyncClient
import asyncio
import importlib
import json
import os
from typing import Any, AsyncIterator, Iterator
from urllib import error, request
from .config import resolve_base_url


class OpenAICompatibleAgentClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("SUKUPOL_OPENAI_BASE_URL", "http://127.0.0.1:8033")
        self.model = os.getenv("SUKUPOL_OPENAI_MODEL", "agent-framework")
        self.api_key = os.getenv("SUKUPOL_OPENAI_API_KEY", "")
        try:
            self.timeout = float(os.getenv("SUKUPOL_OPENAI_TIMEOUT", "20"))
        except ValueError:
            self.timeout = 20.0
        try:
            self.temperature = float(os.getenv("SUKUPOL_OPENAI_TEMPERATURE", "1.0"))
        except ValueError:
            self.temperature = 1.0

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return extract_json_payload(self.chat_text(system_prompt, user_prompt))
    async def achat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        return extract_json_payload(await self.achat_text(system_prompt, user_prompt))

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
    async def achat_text(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        return await self._apost(payload)

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
    async def astream_text(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async for chunk in self._apost_stream(payload):
            yield chunk

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
    async def _apost(self, payload: dict[str, Any]) -> str:
        return await asyncio.to_thread(self._post, payload)

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
                    except (json.JSONDecodeError, ValueError):
                        # Skip malformed SSE data frames
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

    async def _apost_stream(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        """Async generator that drains sync _post_stream via per-chunk asyncio.to_thread."""
        iterator = iter(self._post_stream(payload))
        _sentinel = object()

        def _next() -> str | object:
            try:
                return next(iterator)
            except StopIteration:
                return _sentinel

        while True:
            chunk = await asyncio.to_thread(_next)
            if chunk is _sentinel:
                return
            yield chunk  # type: ignore[misc]


def resolve_chat_endpoint(base_url: str) -> str:
    return resolve_base_url(base_url, for_framework=False)


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