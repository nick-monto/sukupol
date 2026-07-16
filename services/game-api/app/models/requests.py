from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field, field_validator


class MovementAction(StrEnum):
    MOVE_NORTH = "move_north"
    MOVE_EAST = "move_east"
    MOVE_SOUTH = "move_south"
    MOVE_WEST = "move_west"
    FORWARD = "forward"
    BACKWARD = "backward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"


class CombatAction(StrEnum):
    """Fixed set of known combat actions.

    The CombatRequest action field accepts these AND dynamic patterns
    (pinball_strike:<int>, use_item:*, parley_*), so it remains `str`
    with a field_validator. CombatAction exists for grep-uniqueness and
    reuse in the validator.
    """

    ATTACK = "attack"
    DEFEND = "defend"
    FLEE = "flee"


_COMBAT_KNOWN_ACTIONS = frozenset({"attack", "defend", "flee"})


class StartRunRequest(BaseModel):
    player_name: str = Field(default="Wayfarer", min_length=1, max_length=32)


class ActionRequest(BaseModel):
    action: MovementAction


class TalkRequest(BaseModel):
    run_id: str
    message: str = Field(min_length=1, max_length=500)


class RunScopedRequest(BaseModel):
    run_id: str


class CombatRequest(BaseModel):
    action: str
    message: str | None = Field(default=None, max_length=500)

    @field_validator("action")
    @classmethod
    def validate_combat_action(cls, v: str) -> str:
        if v in _COMBAT_KNOWN_ACTIONS:
            return v
        if v.startswith("pinball_strike:"):
            suffix = v.removeprefix("pinball_strike:")
            if suffix.isdigit():
                return v
            raise ValueError("Invalid pinball_strike format")
        if v.startswith("use_item:"):
            return v
        if v.startswith("parley_"):
            return v
        raise ValueError(f"Unknown combat action: {v}")
