from argparse import Namespace
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.cli import build_arg_parser, build_game_config_from_args
from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import (
    LEGACY_CRITICAL_DECK_PROFILE_ID,
    V05_HUNGER_DECK_PROFILE_ID,
)
from sotto_soglia.simulation import SimulationRunner
from sotto_soglia.models import Color


def _cli_args(
    players: int,
    initial_lives: int | None = None,
    critical_wounds_max: int | None = None,
    critical_card_effects: str = "auto",
    animal_card_effects: str = "auto",
) -> Namespace:
    return Namespace(
        players=players,
        initial_lives=initial_lives,
        critical_wounds_max=critical_wounds_max,
        critical_card_effects=critical_card_effects,
        animal_card_effects=animal_card_effects,
        critical_deck_seed=None,
        critical_deck_order=None,
        sono_ancora_qui_variant="single_2",
        animal_lineup=None,
    )


def test_game_config_keeps_legacy_numeric_defaults():
    config = GameConfig()

    assert config.initial_lives == 18
    assert config.critical_wounds_limit == 3
    assert config.color_effects_enabled is True
    assert config.critical_card_effects_enabled is False
    assert config.animal_card_effects_enabled is False
    assert config.critical_deck_profile_id == LEGACY_CRITICAL_DECK_PROFILE_ID


@pytest.mark.parametrize(
    ("players_count", "initial_lives", "critical_wounds_limit"),
    [
        (2, 12, 5),
        (3, 17, 4),
        (4, 24, 4),
    ],
)
def test_v05_config_for_players_returns_numeric_presets(
    players_count,
    initial_lives,
    critical_wounds_limit,
):
    config = get_v05_config_for_players(players_count)

    assert config.initial_lives == initial_lives
    assert config.critical_wounds_limit == critical_wounds_limit
    assert config.color_effects_enabled is False
    assert config.critical_card_effects_enabled is True
    assert config.animal_card_effects_enabled is True
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_v05_config_for_players_rejects_invalid_player_count():
    with pytest.raises(
        ValueError,
        match="players_count must be one of: 2, 3, 4",
    ):
        get_v05_config_for_players(5)


def test_v05_config_for_players_uses_hunger_deck_profile():
    config = get_v05_config_for_players(
        4,
        base_config=GameConfig(critical_deck_profile_id=LEGACY_CRITICAL_DECK_PROFILE_ID),
    )

    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


@pytest.mark.parametrize(
    ("players_count", "initial_lives", "critical_wounds_limit"),
    [
        (2, 12, 5),
        (3, 17, 4),
        (4, 24, 4),
    ],
)
def test_cli_config_uses_v05_numeric_presets_without_manual_overrides(
    players_count,
    initial_lives,
    critical_wounds_limit,
):
    config = build_game_config_from_args(_cli_args(players_count))

    assert config.initial_lives == initial_lives
    assert config.critical_wounds_limit == critical_wounds_limit
    assert config.color_effects_enabled is False
    assert config.critical_card_effects_enabled is True
    assert config.animal_card_effects_enabled is True
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_critical_card_effects_auto_keeps_v05_preset():
    config = build_game_config_from_args(_cli_args(4))

    assert config.critical_card_effects_enabled is True
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_animal_card_effects_auto_keeps_v05_preset():
    config = build_game_config_from_args(_cli_args(4))

    assert config.animal_card_effects_enabled is True
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_can_explicitly_disable_critical_card_effects():
    config = build_game_config_from_args(
        _cli_args(4, critical_card_effects="off")
    )

    assert config.critical_card_effects_enabled is False
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_can_explicitly_enable_critical_card_effects():
    config = build_game_config_from_args(
        _cli_args(4, critical_card_effects="on")
    )

    assert config.critical_card_effects_enabled is True
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_can_explicitly_enable_animal_card_effects():
    config = build_game_config_from_args(
        _cli_args(4, animal_card_effects="on")
    )

    assert config.animal_card_effects_enabled is True
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_can_explicitly_disable_animal_card_effects():
    config = build_game_config_from_args(
        _cli_args(4, animal_card_effects="off")
    )

    assert config.animal_card_effects_enabled is False
    assert config.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_cli_config_manual_overrides_take_precedence_over_v05_presets():
    config = build_game_config_from_args(
        _cli_args(
            players=4,
            initial_lives=30,
            critical_wounds_max=6,
        )
    )

    assert config.initial_lives == 30
    assert config.critical_wounds_limit == 6


def test_cli_parser_accepts_valid_two_player_animal_lineup():
    args = build_arg_parser().parse_args(
        ["--players", "2", "--animal-lineup", "Panda", "Scoiattolo"]
    )

    assert args.animal_lineup == ["Panda", "Scoiattolo"]
    config = build_game_config_from_args(args)
    assert config.animal_lineup == (Color.BLUE, Color.YELLOW)


def test_cli_parser_accepts_valid_three_player_animal_lineup():
    args = build_arg_parser().parse_args(
        ["--players", "3", "--animal-lineup", "Coniglio", "Scimmia", "Scoiattolo"]
    )

    assert args.animal_lineup == ["Coniglio", "Scimmia", "Scoiattolo"]
    config = build_game_config_from_args(args)
    assert config.animal_lineup == (Color.RED, Color.GREEN, Color.YELLOW)


def test_cli_config_rejects_animal_lineup_length_mismatch():
    args = _cli_args(2)
    args.animal_lineup = ["Panda", "Coniglio", "Scimmia"]

    with pytest.raises(ValueError, match="one animal per player"):
        build_game_config_from_args(args)


def test_cli_config_rejects_duplicate_animal_lineup():
    args = _cli_args(2)
    args.animal_lineup = ["Panda", "Panda"]

    with pytest.raises(ValueError, match="duplicate animals"):
        build_game_config_from_args(args)


def test_cli_config_rejects_unknown_animal_lineup():
    args = _cli_args(2)
    args.animal_lineup = ["Panda", "Volpe"]

    with pytest.raises(ValueError, match="unknown animal"):
        build_game_config_from_args(args)


def test_simulation_runner_uses_v05_preset_when_config_is_omitted():
    result = SimulationRunner().run(players_count=3, games_count=1, seed=42)

    assert result.initial_lives == 17
    assert result.critical_wounds_limit == 4
    assert result.color_effects_enabled is False
    assert result.critical_card_effects_enabled is True
    assert result.animal_card_effects_enabled is True
    assert result.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_simulation_runner_preserves_explicit_legacy_config():
    result = SimulationRunner().run(
        players_count=3,
        games_count=1,
        seed=42,
        config=GameConfig(),
    )

    assert result.initial_lives == 18
    assert result.critical_wounds_limit == 3
    assert result.color_effects_enabled is True
    assert result.critical_card_effects_enabled is False
    assert result.animal_card_effects_enabled is False
    assert result.critical_deck_profile_id == LEGACY_CRITICAL_DECK_PROFILE_ID
