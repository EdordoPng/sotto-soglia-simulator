from dataclasses import replace
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.cli import format_simulation_summary
from sotto_soglia.critical import V05_HUNGER_DECK_PROFILE_ID
from sotto_soglia.config import get_v05_config_for_players
from sotto_soglia.simulation import SimulationRunner, SimulationResult
from sotto_soglia.strategies import create_strategy


def test_simulation_runner_returns_ten_results_for_two_players():
    result = SimulationRunner().run(players_count=2, games_count=10, seed=42)

    assert isinstance(result, SimulationResult)
    assert result.players_count == 2
    assert result.games_count == 10
    assert result.base_seed == 42
    assert len(result.game_results) == 10
    assert result.critical_card_effects_enabled is True
    assert result.animal_card_effects_enabled is True
    assert result.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID
    assert result.cards_per_player == 3


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
    assert "Win rate by strategy:" in summary


def test_simulation_runner_accepts_single_strategy_for_all_players():
    result = SimulationRunner().run(
        players_count=4,
        games_count=5,
        seed=42,
        strategies=create_strategy("prudent"),
    )

    assert len(result.game_results) == 5
    assert {
        player.strategy_name
        for player in result.game_results[0].final_players
    } == {"prudent"}


def test_simulation_runner_accepts_one_strategy_per_player():
    result = SimulationRunner().run(
        players_count=4,
        games_count=5,
        seed=42,
        strategies=[
            create_strategy("random"),
            create_strategy("prudent"),
            create_strategy("defensive"),
            create_strategy("aggressive"),
        ],
    )

    strategy_names = [
        player.strategy_name
        for player in result.game_results[0].final_players
    ]

    assert strategy_names == ["random", "prudent", "defensive", "aggressive"]


def test_simulation_runner_smoke_with_animal_card_effects_enabled():
    result = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
    )

    assert result.players_count == 4
    assert result.games_count == 1
    assert len(result.game_results) == 1
    assert result.critical_card_effects_enabled is True
    assert result.animal_card_effects_enabled is True
    assert result.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID


def test_simulation_runner_smoke_with_animal_card_effects_disabled():
    result = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        config=replace(
            get_v05_config_for_players(4),
            animal_card_effects_enabled=False,
        ),
    )

    assert result.players_count == 4
    assert result.games_count == 1
    assert len(result.game_results) == 1
    assert result.critical_card_effects_enabled is True
    assert result.animal_card_effects_enabled is False
    assert result.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID
