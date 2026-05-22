"""Configuration defaults for the Sotto Soglia simulator."""

from dataclasses import dataclass, replace

from sotto_soglia.critical import (
    LEGACY_CRITICAL_DECK_PROFILE_ID,
    V05_HUNGER_DECK_PROFILE_ID,
)
from sotto_soglia.models import Color


V05_PLAYER_PRESETS = {
    2: {
        "initial_lives": 12,
        "critical_wounds_limit": 5,
        "color_effects_enabled": False,
        "critical_card_effects_enabled": True,
        "animal_card_effects_enabled": True,
    },
    3: {
        "initial_lives": 17,
        "critical_wounds_limit": 4,
        "color_effects_enabled": False,
        "critical_card_effects_enabled": True,
        "animal_card_effects_enabled": True,
    },
    4: {
        "initial_lives": 24,
        "critical_wounds_limit": 4,
        "color_effects_enabled": False,
        "critical_card_effects_enabled": True,
        "animal_card_effects_enabled": True,
    },
}


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
    animal_card_effects_enabled: bool = False
    critical_deck_profile_id: str = LEGACY_CRITICAL_DECK_PROFILE_ID
    critical_deck_seed: int | None = None
    critical_deck_order: tuple[str, ...] | None = None
    sono_ancora_qui_variant: str = "single_2"
    animal_lineup: tuple[Color, ...] | None = None


def get_v05_config_for_players(
    players_count: int,
    base_config: GameConfig | None = None,
) -> GameConfig:
    """Return the v0.5 numeric preset for the given player count.

    The legacy field names are intentionally preserved in this step:
    initial_lives means Scorte, critical_wounds_limit means the Affamato limit.
    """

    if players_count not in V05_PLAYER_PRESETS:
        valid_counts = ", ".join(str(count) for count in sorted(V05_PLAYER_PRESETS))
        raise ValueError(f"players_count must be one of: {valid_counts}")

    preset = V05_PLAYER_PRESETS[players_count]
    return replace(
        base_config or GameConfig(),
        initial_lives=preset["initial_lives"],
        critical_wounds_limit=preset["critical_wounds_limit"],
        color_effects_enabled=preset["color_effects_enabled"],
        critical_card_effects_enabled=preset["critical_card_effects_enabled"],
        animal_card_effects_enabled=preset["animal_card_effects_enabled"],
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )
