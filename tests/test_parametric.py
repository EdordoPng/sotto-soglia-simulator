import csv
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig
from sotto_soglia.exporters import CSV_DELIMITER, export_parametric_simulation_result
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.parametric import ParametricSimulationRunner
from sotto_soglia.round import resolve_round


def test_game_config_defaults_to_color_effects_enabled():
    assert GameConfig().color_effects_enabled is True


def test_color_effects_off_disables_own_color_reduction():
    selected_cards = {
        1: Card(color=Color.BLUE, value=4),
        2: Card(color=Color.YELLOW, value=1),
    }

    players_on = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    result_on = resolve_round(
        players_on,
        selected_cards,
        GameConfig(color_effects_enabled=True),
    )

    players_off = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    result_off = resolve_round(
        players_off,
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )

    assert result_on.critical_wound_players == [2]
    assert result_off.critical_wound_players == [2]
    assert result_on.total_damage_by_player[1] == 3
    assert result_off.total_damage_by_player[1] == 4


def test_color_effects_off_disables_opponent_color_extra_damage():
    selected_cards = {
        1: Card(color=Color.GREEN, value=3),
        2: Card(color=Color.BLUE, value=4),
        3: Card(color=Color.YELLOW, value=1),
    }

    players_on = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    result_on = resolve_round(
        players_on,
        selected_cards,
        GameConfig(color_effects_enabled=True),
    )

    players_off = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    result_off = resolve_round(
        players_off,
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )

    assert result_on.critical_wound_players == [3]
    assert result_off.critical_wound_players == [3]
    assert result_on.extra_damage_by_player[1] == 1
    assert result_off.extra_damage_by_player[1] == 0
    assert result_on.total_damage_by_player[1] == 4
    assert result_off.total_damage_by_player[1] == 3


def test_parametric_runner_tests_all_configurations():
    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=1,
        seed=42,
        initial_lives_values=[15, 18],
        critical_wounds_values=[2, 3],
        color_effects_values=[True, False],
        strategy_names="random",
    )

    assert result.tested_configs == 8
    assert len(result.config_results) == 8


def test_parametric_total_games():
    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=2,
        seed=42,
        initial_lives_values=[15, 18],
        critical_wounds_values=[2, 3],
        color_effects_values=[True, False],
        strategy_names="random",
    )

    assert result.total_games == 16


def test_parametric_marks_baseline():
    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=1,
        seed=42,
        initial_lives_values=[15, 18],
        critical_wounds_values=[2, 3],
        color_effects_values=[True, False],
        strategy_names="random",
    )

    baselines = [
        config_result
        for config_result in result.config_results
        if config_result.is_baseline
    ]

    assert len(baselines) == 1
    assert baselines[0].initial_lives == 18
    assert baselines[0].critical_wounds_limit == 3
    assert baselines[0].color_effects_enabled is True


def test_parametric_runner_works_with_random_and_adaptive_pressure():
    for strategy_name in ["random", "adaptive_pressure"]:
        result = ParametricSimulationRunner().run(
            players_count=2,
            games_per_config=2,
            seed=42,
            initial_lives_values=[18],
            critical_wounds_values=[3],
            color_effects_values=[True],
            strategy_names=strategy_name,
        )

        assert result.tested_configs == 1
        assert result.config_results[0].aggregate_stats["games_count"] == 2


def test_parametric_export_creates_json_and_csv(tmp_path):
    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=1,
        seed=42,
        initial_lives_values=[15, 18],
        critical_wounds_values=[2, 3],
        color_effects_values=[True, False],
        strategy_names="random",
    )

    exported_files = export_parametric_simulation_result(result, tmp_path)

    assert exported_files["parametric_stats"].exists()
    assert exported_files["parametric_summary"].exists()

    with exported_files["parametric_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["baseline_config"] == {
        "initial_lives": 18,
        "critical_wounds_limit": 3,
        "color_effects_enabled": True,
    }

    with exported_files["parametric_summary"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == result.tested_configs
