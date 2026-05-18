"""Core data models for Sotto Soglia."""

from dataclasses import dataclass, field
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
    critical_cards_drawn: list[str] = field(default_factory=list)
    active_critical_effects: list[str] = field(default_factory=list)
    consumed_critical_effects: list[str] = field(default_factory=list)
    life_gained_from_critical_cards: int = 0
    life_lost_from_critical_cards: int = 0
    damage_prevented_by_critical_cards: int = 0
