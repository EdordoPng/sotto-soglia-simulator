"""Game-level result models."""

from dataclasses import dataclass, field


@dataclass
class GameResult:
    """Minimal result data for one game."""

    game_id: int
    winner_ids: list[int] = field(default_factory=list)
    is_draw: bool = False
    rounds_count: int = 0
