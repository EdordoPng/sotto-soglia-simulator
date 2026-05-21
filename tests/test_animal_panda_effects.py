from dataclasses import replace
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import RAZIONE_RISPARMIATA, V05_HUNGER_DECK_PROFILE_ID
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.round import resolve_round
from sotto_soglia.rules import (
    get_effective_comparison_value,
    get_effective_consumption_value,
)


def _animal_config(**overrides) -> GameConfig:
    return GameConfig(
        initial_lives=12,
        critical_wounds_limit=5,
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
        **overrides,
    )


def test_respiro_lento_reduces_own_panda_three_consumption_by_one():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3)
    config = _animal_config()

    assert card.value == 3
    assert card.consumption_value == 3
    assert card.comparison_value == 3
    assert get_effective_consumption_value(player, card, config) == 2
    assert get_effective_comparison_value(player, card, config) == 3


def test_respiro_lento_is_inactive_when_animal_effects_are_disabled():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3)

    assert get_effective_consumption_value(player, card, GameConfig()) == 3


def test_respiro_lento_is_inactive_when_other_animals_play_panda_three():
    card = Card(Color.BLUE, 3)

    for color in (Color.RED, Color.GREEN, Color.YELLOW):
        player = PlayerState(player_id=1, color=color, lives=12)

        assert get_effective_consumption_value(player, card, _animal_config()) == 3
        assert get_effective_comparison_value(player, card, _animal_config()) == 3


def test_round_base_consumption_uses_respiro_lento_when_panda_is_not_affamato():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 1),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 2
    assert players[0].lives == 10


def test_respiro_lento_does_not_make_affamato_panda_consume_two():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0
    assert players[0].lives == 12


def test_respiro_lento_does_not_modify_effective_comparison_value():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3)

    assert get_effective_comparison_value(player, card, _animal_config()) == 3


def test_respiro_lento_combines_with_razione_risparmiata_to_minimum_one():
    players = [
        PlayerState(
            player_id=1,
            color=Color.BLUE,
            lives=12,
            active_critical_effects=[RAZIONE_RISPARMIATA],
        ),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 1),
    }
    config = _animal_config(
        critical_card_effects_enabled=True,
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )

    result = resolve_round(players, selected_cards, config)

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 1
    assert players[0].lives == 11
    assert players[0].consumed_critical_effects == [RAZIONE_RISPARMIATA]


def test_respiro_lento_consumption_never_drops_below_one():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3, custom_consumption_value=1)

    assert get_effective_consumption_value(player, card, _animal_config()) == 1


def test_other_panda_effect_cards_keep_standard_values_for_now():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)

    assert get_effective_consumption_value(
        player,
        Card(Color.BLUE, 1),
        _animal_config(),
    ) == 1
    assert get_effective_comparison_value(
        player,
        Card(Color.BLUE, 1),
        _animal_config(),
    ) == 1
    assert get_effective_consumption_value(
        player,
        Card(Color.BLUE, 5),
        _animal_config(),
    ) == 5
    assert get_effective_comparison_value(
        player,
        Card(Color.BLUE, 5),
        _animal_config(),
    ) == 5


def test_scimmia_and_scoiattolo_effect_cards_keep_standard_values_for_now():
    cases = (
        (Color.GREEN, 1),
        (Color.GREEN, 2),
        (Color.GREEN, 5),
        (Color.YELLOW, 1),
        (Color.YELLOW, 3),
        (Color.YELLOW, 4),
    )

    for color, value in cases:
        player = PlayerState(player_id=1, color=color, lives=12)
        card = Card(color, value)

        assert get_effective_consumption_value(player, card, _animal_config()) == value
        assert get_effective_comparison_value(player, card, _animal_config()) == value


def test_runtime_standard_result_does_not_change_without_animal_effect_flag_for_panda_three():
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 1),
    }

    baseline = resolve_round(
        [
            PlayerState(player_id=1, color=Color.BLUE, lives=12),
            PlayerState(player_id=2, color=Color.RED, lives=12),
        ],
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )
    v05_without_animals = resolve_round(
        [
            PlayerState(player_id=1, color=Color.BLUE, lives=12),
            PlayerState(player_id=2, color=Color.RED, lives=12),
        ],
        selected_cards,
        replace(get_v05_config_for_players(2), critical_card_effects_enabled=False),
    )

    assert v05_without_animals.critical_wound_players == baseline.critical_wound_players
    assert v05_without_animals.base_damage_by_player == baseline.base_damage_by_player
    assert v05_without_animals.lowest_value == baseline.lowest_value


def test_game_config_and_v05_presets_keep_animal_effects_disabled():
    assert GameConfig().animal_card_effects_enabled is False
    assert get_v05_config_for_players(2).animal_card_effects_enabled is False
    assert get_v05_config_for_players(3).animal_card_effects_enabled is False
    assert get_v05_config_for_players(4).animal_card_effects_enabled is False
