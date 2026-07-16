from __future__ import annotations

import inspect

import pytest


def test_agent_framework_openai_api_shape() -> None:
    """API-shape contract test: fails when agent_framework.openai renames
    the client constructor or drops as_agent.

    Uses pytest.importorskip so this test is a no-op in the default
    test environment (agent-framework is optional, not installed).
    """
    openai_module = pytest.importorskip("agent_framework.openai")

    # Assert the client class exists
    assert hasattr(openai_module, "OpenAIChatCompletionClient")

    cls = openai_module.OpenAIChatCompletionClient
    sig = inspect.signature(cls.__init__)

    # The constructor must accept model, api_key, base_url by name
    for kwarg in ("model", "api_key", "base_url"):
        assert kwarg in sig.parameters, (
            f"OpenAIChatCompletionClient.__init__ missing parameter "
            f"{kwarg!r}; got {list(sig.parameters.keys())}"
        )

    # The client must expose as_agent (called by runtime._afw_invoke_text)
    assert hasattr(cls, "as_agent"), (
        "OpenAIChatCompletionClient missing as_agent method"
    )
