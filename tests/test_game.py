from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig
from sotto_soglia.game import GameResult, play_game
from sotto_soglia.round import RoundResult


def _assert_valid_result(result: GameResult) -> None:
    assert result.rounds_count > 0
    assert result.winner_ids
    assert len(result.round_history) == result.rounds_count
    assert all(isinstance(round_result, RoundResult) for round_result in result.round_history)
    assert len(result.final_players) >= 2


def test_play_game_with_two_players_returns_valid_result():
    result = play_game(game_id=1, players_count=2, seed=42)

    _assert_valid_result(result)


def test_play_game_with_three_players_returns_valid_result():
    result = play_game(game_id=1, players_count=3, seed=42)

    _assert_valid_result(result)


def test_play_game_with_four_players_returns_valid_result():
    result = play_game(game_id=1, players_count=4, seed=42)

    _assert_valid_result(result)


def test_play_game_rejects_too_few_players():
    try:
        play_game(players_count=1, seed=42)
    except ValueError:
        return

    assert False, "Expected ValueError for players_count < 2"


def test_play_game_rejects_too_many_players():
    try:
        play_game(players_count=5, seed=42)
    except ValueError:
        return

    assert False, "Expected ValueError for players_count > 4"


def test_play_game_raises_when_max_rounds_is_exceeded():
    try:
        play_game(players_count=2, seed=42, max_rounds=0)
    except RuntimeError:
        return

    assert False, "Expected RuntimeError when max_rounds is exceeded"


def test_round_history_and_elimination_order_are_populated():
    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(initial_lives=1),
    )

    assert result.round_history
    assert all(isinstance(round_result, RoundResult) for round_result in result.round_history)
    assert result.elimination_order
