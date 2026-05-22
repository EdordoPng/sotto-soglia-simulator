import csv
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.exporters import CSV_DELIMITER, export_strategy_tournament_result
from sotto_soglia.tournament import StrategyTournamentRunner


def _four_strategy_tournament(games_per_lineup=2):
    return StrategyTournamentRunner().run(
        players_count=4,
        strategy_names=[
            "adaptive_pressure",
            "random",
            "defensive",
            "aggressive",
        ],
        games_per_lineup=games_per_lineup,
        seed=42,
    )


def test_tournament_generates_all_lineups_for_four_distinct_strategies():
    result = _four_strategy_tournament(games_per_lineup=1)

    assert result.lineups_tested == 24
    assert len(result.lineup_results) == 24


def test_tournament_total_games_matches_lineups_times_games_per_lineup():
    result = _four_strategy_tournament(games_per_lineup=2)

    assert result.total_games == result.lineups_tested * result.games_per_lineup
    assert result.aggregate_stats["total_games"] == result.total_games


def test_tournament_balances_strategy_appearances_by_player_id():
    games_per_lineup = 3
    result = _four_strategy_tournament(games_per_lineup=games_per_lineup)
    appearances = result.aggregate_stats["appearances_by_strategy_player_id"]
    expected_per_player = 6 * games_per_lineup

    for strategy_counts in appearances.values():
        assert strategy_counts == {
            1: expected_per_player,
            2: expected_per_player,
            3: expected_per_player,
            4: expected_per_player,
        }


def test_tournament_aggregate_stats_contains_strategy_win_rates():
    result = _four_strategy_tournament(games_per_lineup=1)

    assert "win_rate_by_strategy" in result.aggregate_stats
    assert "adaptive_pressure" in result.aggregate_stats["win_rate_by_strategy"]


def test_tournament_same_seed_produces_same_essential_result():
    first = _four_strategy_tournament(games_per_lineup=2)
    second = _four_strategy_tournament(games_per_lineup=2)

    assert first.aggregate_stats == second.aggregate_stats
    assert [
        (lineup.lineup_seed, lineup.strategies_by_player, lineup.aggregate_stats)
        for lineup in first.lineup_results
    ] == [
        (lineup.lineup_seed, lineup.strategies_by_player, lineup.aggregate_stats)
        for lineup in second.lineup_results
    ]


def test_tournament_rejects_strategy_count_different_from_players_count():
    try:
        StrategyTournamentRunner().run(
            players_count=4,
            strategy_names=["random", "defensive"],
            games_per_lineup=1,
            seed=42,
        )
    except ValueError:
        return

    assert False, "Expected ValueError for strategy/player count mismatch"


def test_tournament_rejects_unknown_strategy():
    try:
        StrategyTournamentRunner().run(
            players_count=2,
            strategy_names=["random", "unknown"],
            games_per_lineup=1,
            seed=42,
        )
    except ValueError:
        return

    assert False, "Expected ValueError for unknown strategy"


def test_tournament_runner_works_with_two_players_and_two_strategies():
    result = StrategyTournamentRunner().run(
        players_count=2,
        strategy_names=["adaptive_pressure", "random"],
        games_per_lineup=2,
        seed=42,
    )

    assert result.lineups_tested == 2
    assert result.total_games == 4
    assert "win_rate_by_strategy" in result.aggregate_stats


def test_tournament_runner_accepts_v05_animal_aware_strategy():
    result = StrategyTournamentRunner().run(
        players_count=2,
        strategy_names=["v05_animal_aware", "random"],
        games_per_lineup=1,
        seed=42,
    )

    assert result.lineups_tested == 2
    assert "v05_animal_aware" in result.aggregate_stats["win_rate_by_strategy"]


def test_tournament_does_not_duplicate_repeated_strategy_lineups():
    result = StrategyTournamentRunner().run(
        players_count=3,
        strategy_names=["random", "random", "defensive"],
        games_per_lineup=1,
        seed=42,
    )

    assert result.lineups_tested == 3


def test_tournament_export_creates_expected_files(tmp_path):
    result = StrategyTournamentRunner().run(
        players_count=2,
        strategy_names=["adaptive_pressure", "random"],
        games_per_lineup=2,
        seed=42,
    )

    exported_files = export_strategy_tournament_result(result, tmp_path)

    assert exported_files["strategy_tournament_stats"].exists()
    assert exported_files["strategy_tournament_lineups"].exists()

    with exported_files["strategy_tournament_stats"].open(encoding="utf-8") as file:
        stats_data = json.load(file)

    assert stats_data["total_games"] == 4
    assert stats_data["lineups_tested"] == 2

    with exported_files["strategy_tournament_lineups"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 2
    assert "strategies_by_player" in rows[0]
    assert "wins_by_strategy" in rows[0]
