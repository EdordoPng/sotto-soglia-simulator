from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.simulation import SimulationRunner
from sotto_soglia.statistics import StatisticAggregator
from sotto_soglia.game import GameResult
from sotto_soglia.models import Color, EliminationReason, PlayerState


def test_statistic_aggregator_returns_required_fields():
    simulation = SimulationRunner().run(players_count=4, games_count=10, seed=42)
    stats = StatisticAggregator().aggregate(simulation.game_results)

    assert stats["games_count"] == 10
    assert isinstance(stats["average_rounds"], int | float)
    assert stats["min_rounds"] <= stats["max_rounds"]
    assert "draw_count" in stats
    assert 0 <= stats["draw_rate"] <= 1
    assert "wins_by_player_id" in stats
    assert "wins_by_color" in stats
    assert "wins_by_strategy" in stats
    assert "win_rate_by_strategy" in stats
    assert "eliminations_by_lives" in stats
    assert "eliminations_by_critical_wounds" in stats
    assert "average_winner_lives" in stats
    assert "average_winner_critical_wounds" in stats


def test_statistic_aggregator_empty_input_is_stable():
    stats = StatisticAggregator().aggregate([])

    assert stats["games_count"] == 0
    assert stats["average_rounds"] == 0.0
    assert stats["min_rounds"] == 0
    assert stats["max_rounds"] == 0
    assert stats["draw_rate"] == 0.0


def test_statistic_aggregator_does_not_count_non_draw_winner_as_eliminated():
    result = GameResult(
        game_id=1,
        winner_ids=[1],
        is_draw=False,
        rounds_count=3,
        final_players=[
            PlayerState(
                player_id=1,
                color=Color.BLUE,
                lives=0,
                critical_wounds=2,
                is_alive=False,
                elimination_reason=EliminationReason.LIVES,
            ),
            PlayerState(
                player_id=2,
                color=Color.RED,
                lives=0,
                critical_wounds=3,
                is_alive=False,
                elimination_reason=EliminationReason.CRITICAL_WOUNDS,
            ),
        ],
        seed=42,
    )

    stats = StatisticAggregator().aggregate([result])

    assert stats["eliminations_by_lives"] == 0
    assert stats["eliminations_by_critical_wounds"] == 1
