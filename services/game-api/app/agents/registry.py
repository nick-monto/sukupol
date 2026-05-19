from __future__ import annotations

from typing import Any, Callable


AgentBuilder = Callable[..., Any]
ToolBuilder = Callable[..., tuple[Any, ...]]


_AGENT_BUILDERS: dict[str, AgentBuilder] = {}
_TOOL_BUILDERS: dict[str, ToolBuilder] = {}


def register_agent_builder(name: str, builder: AgentBuilder) -> None:
    _AGENT_BUILDERS[name] = builder


def register_tool_builder(name: str, builder: ToolBuilder) -> None:
    _TOOL_BUILDERS[name] = builder


def build_agent(name: str, *args: Any, **kwargs: Any) -> Any:
    if name not in _AGENT_BUILDERS:
        raise KeyError(f"Unknown agent builder: {name}")
    return _AGENT_BUILDERS[name](*args, **kwargs)


def build_tools(name: str, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
    if name not in _TOOL_BUILDERS:
        return ()
    return _TOOL_BUILDERS[name](*args, **kwargs)


def list_registered_agents() -> list[str]:
    return sorted(_AGENT_BUILDERS)


def list_registered_tools() -> list[str]:
    return sorted(_TOOL_BUILDERS)