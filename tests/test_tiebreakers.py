from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.game import resolve_game_tiebreaker
from sotto_soglia.round import RoundResult


def test_final_tiebreaker_prefers_fewer_critical_wounds():
    final_round = RoundResult(
        round_number=3,
        lives_before={1: 5, 2: 8},
        critical_wounds_after={1: 2, 2: 3},
    )

    winner_ids, is_draw = resolve_game_tiebreaker([1, 2], final_round)

    assert winner_ids == [1]
    assert is_draw is False


def test_final_tiebreaker_uses_previous_lives_when_critical_wounds_are_tied():
    final_round = RoundResult(
        round_number=3,
        lives_before={1: 5, 2: 8},
        critical_wounds_after={1: 3, 2: 3},
    )

    winner_ids, is_draw = resolve_game_tiebreaker([1, 2], final_round)

    assert winner_ids == [2]
    assert is_draw is False


def test_final_tiebreaker_can_end_in_draw():
    final_round = RoundResult(
        round_number=3,
        lives_before={1: 8, 2: 8},
        critical_wounds_after={1: 3, 2: 3},
    )

    winner_ids, is_draw = resolve_game_tiebreaker([1, 2], final_round)

    assert winner_ids == [1, 2]
    assert is_draw is True
