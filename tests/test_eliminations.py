from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig
from sotto_soglia.models import Card, Color, EliminationReason, PlayerState
from sotto_soglia.round import resolve_round


def test_player_is_eliminated_when_lives_reach_zero():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=3),
    ]
    selected_cards = {
        1: Card(color=Color.BLUE, value=1),
        2: Card(color=Color.GREEN, value=3),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.eliminated_players == [2]
    assert players[1].lives == 0
    assert players[1].is_alive is False
    assert players[1].elimination_reason == EliminationReason.LIVES


def test_player_is_eliminated_when_reaching_critical_wound_limit():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18, critical_wounds=2),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.GREEN, value=1),
        2: Card(color=Color.YELLOW, value=3),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.eliminated_players == [1]
    assert players[0].critical_wounds == 3
    assert players[0].is_alive is False
    assert players[0].elimination_reason == EliminationReason.CRITICAL_WOUNDS


def test_lives_never_drop_below_zero():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=2),
    ]
    selected_cards = {
        1: Card(color=Color.BLUE, value=1),
        2: Card(color=Color.GREEN, value=5),
    }

    resolve_round(players, selected_cards, GameConfig())

    assert players[1].lives == 0


def test_elimination_does_not_cancel_effects_already_revealed_this_round():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=1),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.RED, value=4),
        2: Card(color=Color.BLUE, value=3),
        3: Card(color=Color.YELLOW, value=1),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.critical_wound_players == [3]
    assert result.extra_damage_by_player[1] == 1
    assert result.total_damage_by_player[1] == 5
    assert players[0].lives == 5
    assert players[1].is_alive is False
    assert players[1].elimination_reason == EliminationReason.LIVES
