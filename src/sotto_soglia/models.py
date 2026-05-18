"""Core data models for Sotto Soglia."""

from dataclasses import dataclass
from enum import Enum


class Color(Enum):
    """Available player and card colors."""

    BLUE = "blue"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"


class EliminationReason(Enum):
    """Reason why a player has been eliminated."""

    LIVES = "lives"
    CRITICAL_WOUNDS = "critical_wounds"
    NONE = "none"


@dataclass(frozen=True)
class Card:
    """A single card in the shared deck."""

    color: Color
    value: int


@dataclass
class PlayerState:
    """Minimal state tracked for one player."""

    player_id: int
    color: Color
    lives: int
    critical_wounds: int = 0
    is_alive: bool = True
    elimination_reason: EliminationReason = EliminationReason.NONE
    strategy_name: str = "random"
