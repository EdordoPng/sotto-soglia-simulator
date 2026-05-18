"""Configuration defaults for the Sotto Soglia simulator."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    """Static configuration values for a standard game."""

    initial_lives: int = 18
    critical_wounds_limit: int = 3
    color_effects_enabled: bool = True
    cards_per_player: int = 3
    min_players: int = 2
    max_players: int = 4
    card_values: tuple[int, ...] = (1, 2, 3, 4, 5)
    critical_card_effects_enabled: bool = False
    critical_deck_seed: int | None = None
    critical_deck_order: tuple[str, ...] | None = None
    sono_ancora_qui_variant: str = "single_1"
