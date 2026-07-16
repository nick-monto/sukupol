from __future__ import annotations

from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


AgentBuilder = Callable[..., Any]
ToolFunc = Callable[[], str]
ToolBuilder = Callable[..., tuple[ToolFunc, ...]]


_AGENT_BUILDERS: dict[str, AgentBuilder] = {}
_TOOL_BUILDERS: dict[str, ToolBuilder] = {}


def register_agent_builder(name: str, builder: AgentBuilder) -> None:
    _AGENT_BUILDERS[name] = builder


def register_tool_builder(name: str, builder: ToolBuilder) -> None:
    _TOOL_BUILDERS[name] = builder


def build_agent(name: str, *args: Any, **kwargs: Any) -> Any:
    if name not in _AGENT_BUILDERS:
        raise KeyError(f"Unknown agent builder: {name}")
    logger.debug("agent_tool_registered", extra={"name": name, "kind": "agent"})
    return _AGENT_BUILDERS[name](*args, **kwargs)


def build_tools(name: str, *args: Any, **kwargs: Any) -> tuple[ToolFunc, ...]:
    if name not in _TOOL_BUILDERS:
        raise KeyError(f"unknown tool: {name}")
    logger.debug("agent_tool_registered", extra={"name": name, "kind": "tool"})
    return _TOOL_BUILDERS[name](*args, **kwargs)


def list_registered_agents() -> list[str]:
    return sorted(_AGENT_BUILDERS)


def list_registered_tools() -> list[str]:
    return sorted(_TOOL_BUILDERS)