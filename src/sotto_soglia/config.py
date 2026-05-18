"""Configuration defaults for the Sotto Soglia simulator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    """Static configuration values for a standard game."""

    initial_lives: int = 18
    critical_wounds_limit: int = 3
    cards_per_player: int = 3
    min_players: int = 2
    max_players: int = 4
    card_values: tuple[int, ...] = (1, 2, 3, 4, 5)
