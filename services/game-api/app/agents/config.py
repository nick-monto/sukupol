from __future__ import annotations

__all__ = ["resolve_base_url"]


def resolve_base_url(raw: str, *, for_framework: bool = False) -> str:
    """Normalize an agent base URL.

    *for_framework* (True): returns an openai-SDK ``base_url``
    ending with ``/v1/`` (used by the agent-framework runtime).

    *for_framework* (False): returns a chat-completions endpoint URL
    ending with ``/v1/chat/completions`` (used by the direct LLM provider).

    Raises ``RuntimeError`` when the input is empty or has no URI scheme.
    """
    if not raw or "://" not in raw:
        raise RuntimeError(f"invalid agent base_url: {raw!r}")

    normalized = raw.rstrip("/")

    if for_framework:
        # OpenAI SDK form: ensure trailing /v1/
        if normalized.endswith("/v1"):
            normalized = f"{normalized}/"
        elif not normalized.endswith("/chat/completions"):
            normalized = f"{normalized}/v1/"
    else:
        # Chat-completions endpoint form: build full URL
        if normalized.endswith("/chat/completions"):
            pass
        elif normalized.endswith("/v1"):
            normalized = f"{normalized}/chat/completions"
        else:
            normalized = f"{normalized}/v1/chat/completions"

    return normalized
