"""Round-level result models."""

from dataclasses import dataclass, field

from sotto_soglia.models import Card


@dataclass
class RoundResult:
    """Minimal result data for one resolved round."""

    round_number: int
    selected_cards: dict[int, Card] = field(default_factory=dict)
    critical_wound_players: list[int] = field(default_factory=list)
    damage_by_player: dict[int, int] = field(default_factory=dict)
    eliminated_players: list[int] = field(default_factory=list)
