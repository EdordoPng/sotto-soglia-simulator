from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.round import resolve_round


def test_tied_lowest_value_players_all_receive_critical_wound():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.BLUE, value=2),
        2: Card(color=Color.RED, value=2),
        3: Card(color=Color.YELLOW, value=5),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 2]
    assert players[0].critical_wounds == 1
    assert players[1].critical_wounds == 1
    assert players[0].lives == 18
    assert players[1].lives == 18
    assert players[2].lives == 13


def test_round_result_tracks_lives_and_critical_wounds_before_and_after():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18, critical_wounds=1),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    selected_cards = {
        1: Card(color=Color.GREEN, value=1),
        2: Card(color=Color.YELLOW, value=4),
    }

    result = resolve_round(players, selected_cards, GameConfig())

    assert result.lives_before == {1: 18, 2: 18}
    assert result.lives_after == {1: 18, 2: 14}
    assert result.critical_wounds_before == {1: 1, 2: 0}
    assert result.critical_wounds_after == {1: 2, 2: 0}
