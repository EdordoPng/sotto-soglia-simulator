from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.cli import format_simulation_summary
from sotto_soglia.simulation import SimulationRunner, SimulationResult


def test_simulation_runner_returns_ten_results_for_two_players():
    result = SimulationRunner().run(players_count=2, games_count=10, seed=42)

    assert isinstance(result, SimulationResult)
    assert result.players_count == 2
    assert result.games_count == 10
    assert result.base_seed == 42
    assert len(result.game_results) == 10


def test_simulation_runner_returns_ten_results_for_four_players():
    result = SimulationRunner().run(players_count=4, games_count=10, seed=42)

    assert result.players_count == 4
    assert len(result.game_results) == 10


def test_simulation_runner_uses_incremental_game_seeds():
    result = SimulationRunner().run(players_count=4, games_count=4, seed=42)

    assert [game.seed for game in result.game_results] == [42, 43, 44, 45]


def test_simulation_runner_rejects_invalid_players_count():
    try:
        SimulationRunner().run(players_count=1, games_count=10, seed=42)
    except ValueError:
        return

    assert False, "Expected ValueError for invalid players_count"


def test_simulation_runner_rejects_invalid_games_count():
    try:
        SimulationRunner().run(players_count=4, games_count=0, seed=42)
    except ValueError:
        return

    assert False, "Expected ValueError for invalid games_count"


def test_simulation_is_reproducible_with_same_seed():
    first = SimulationRunner().run(players_count=4, games_count=10, seed=42)
    second = SimulationRunner().run(players_count=4, games_count=10, seed=42)

    assert first.aggregate_stats == second.aggregate_stats
    assert [
        (game.winner_ids, game.is_draw, game.rounds_count)
        for game in first.game_results
    ] == [
        (game.winner_ids, game.is_draw, game.rounds_count)
        for game in second.game_results
    ]


def test_format_simulation_summary_contains_core_sections():
    result = SimulationRunner().run(players_count=2, games_count=3, seed=42)
    summary = format_simulation_summary(result)

    assert "Sotto Soglia Simulation" in summary
    assert "Players: 2" in summary
    assert "Games: 3" in summary
    assert "Win rate by player:" in summary
    assert "Win rate by color:" in summary
