from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.round import resolve_round
from sotto_soglia.rules import calculate_base_damage


def test_standard_card_uses_printed_value_for_consumption_and_comparison():
    card = Card(color=Color.BLUE, value=4)

    assert card.value == 4
    assert card.consumption_value == 4
    assert card.comparison_value == 4


def test_card_with_comparison_override_keeps_printed_and_consumption_values():
    card = Card(color=Color.BLUE, value=1, custom_comparison_value=2)

    assert card.value == 1
    assert card.consumption_value == 1
    assert card.comparison_value == 2


def test_card_with_consumption_override_keeps_printed_and_comparison_values():
    card = Card(color=Color.BLUE, value=4, custom_consumption_value=2)

    assert card.value == 4
    assert card.consumption_value == 2
    assert card.comparison_value == 4


def test_card_with_both_value_overrides_uses_both():
    card = Card(
        color=Color.BLUE,
        value=4,
        custom_consumption_value=2,
        custom_comparison_value=5,
    )

    assert card.value == 4
    assert card.consumption_value == 2
    assert card.comparison_value == 5


def test_single_lowest_value_gets_critical_and_other_player_loses_card_value():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.BLUE, value=1),
        2: Card(color=Color.GREEN, value=3),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [1]
    assert players[0].critical_wounds == 1
    assert players[0].lives == 18
    assert players[1].lives == 15
    assert result.total_damage_by_player[1] == 0
    assert result.total_damage_by_player[2] == 3


def test_own_color_reduces_base_damage_by_one():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.BLUE, value=4),
        2: Card(color=Color.YELLOW, value=2),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 15


def test_legacy_own_color_reduction_starts_from_consumption_value():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    card = Card(
        color=Color.BLUE,
        value=5,
        custom_consumption_value=3,
    )

    damage = calculate_base_damage(
        player,
        card,
        received_critical_wound=False,
        color_effects_enabled=True,
    )

    assert damage == 2


def test_own_color_damage_has_minimum_one_when_not_critical():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    card = Card(color=Color.BLUE, value=1)

    assert calculate_base_damage(player, card, received_critical_wound=False) == 1


def test_opponent_color_adds_one_extra_damage_to_matching_player():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.GREEN, value=4),
        2: Card(color=Color.BLUE, value=3),
        3: Card(color=Color.YELLOW, value=1),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [3]
    assert result.extra_damage_by_player[1] == 1
    assert players[0].lives == 13


def test_extra_color_damage_is_cumulative():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
        PlayerState(player_id=4, color=Color.YELLOW, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.RED, value=4),
        2: Card(color=Color.BLUE, value=3),
        3: Card(color=Color.BLUE, value=5),
        4: Card(color=Color.YELLOW, value=2),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [4]
    assert result.extra_damage_by_player[1] == 2
    assert result.total_damage_by_player[1] == 6
    assert players[0].lives == 12


def test_critical_wound_player_is_immune_to_extra_color_damage():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.GREEN, value=1),
        2: Card(color=Color.BLUE, value=3),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [1]
    assert result.extra_damage_by_player[1] == 0
    assert result.total_damage_by_player[1] == 0
    assert players[0].lives == 18


def test_critical_wound_player_does_not_activate_color_effect():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.RED, value=3),
        2: Card(color=Color.BLUE, value=1),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [2]
    assert result.extra_damage_by_player[1] == 0
    assert players[0].lives == 15


def test_v05_own_color_does_not_reduce_base_damage():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(color=Color.BLUE, value=4),
        2: Card(color=Color.YELLOW, value=2),
    }

    result = resolve_round(
        players,
        selected_cards,
        get_v05_config_for_players(2),
    )

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 4
    assert result.extra_damage_by_player[1] == 0
    assert players[0].lives == 8


def test_v05_opponent_color_does_not_add_extra_damage():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=17),
        PlayerState(player_id=2, color=Color.RED, lives=17),
        PlayerState(player_id=3, color=Color.GREEN, lives=17),
    ]
    selected_cards = {
        1: Card(color=Color.GREEN, value=3),
        2: Card(color=Color.BLUE, value=4),
        3: Card(color=Color.YELLOW, value=1),
    }

    result = resolve_round(
        players,
        selected_cards,
        get_v05_config_for_players(3),
    )

    assert result.critical_wound_players == [3]
    assert result.extra_damage_by_player[1] == 0
    assert result.total_damage_by_player[1] == 3
    assert players[0].lives == 14


def test_round_critical_assignment_uses_comparison_value():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(
            color=Color.BLUE,
            value=1,
            custom_comparison_value=5,
        ),
        2: Card(color=Color.RED, value=3),
    }

    result = resolve_round(
        players,
        selected_cards,
        get_v05_config_for_players(2),
    )

    assert result.lowest_value == 3
    assert result.critical_wound_players == [2]
    assert players[0].critical_wounds == 0
    assert players[1].critical_wounds == 1


def test_round_base_damage_uses_consumption_value():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(
            color=Color.BLUE,
            value=5,
            custom_consumption_value=2,
        ),
        2: Card(color=Color.RED, value=1),
    }

    result = resolve_round(
        players,
        selected_cards,
        get_v05_config_for_players(2),
    )

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 2
    assert result.total_damage_by_player[1] == 2
    assert players[0].lives == 10
