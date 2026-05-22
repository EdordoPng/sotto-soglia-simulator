import csv
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import V05_HUNGER_DECK_PROFILE_ID
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


def test_parametric_runner_preserves_v05_base_config():
    base_config = get_v05_config_for_players(4)

    result = ParametricSimulationRunner().run(
        players_count=4,
        games_per_config=1,
        seed=42,
        initial_lives_values=[20, 24],
        critical_wounds_values=[4, 5],
        color_effects_values=[False],
        strategy_names="v05_animal_aware",
        base_config=base_config,
    )

    tested_pairs = {
        (config_result.initial_lives, config_result.critical_wounds_limit)
        for config_result in result.config_results
    }

    assert tested_pairs == {(20, 4), (20, 5), (24, 4), (24, 5)}
    for config_result in result.config_results:
        simulation_result = config_result.simulation_result
        assert config_result.color_effects_enabled is False
        assert config_result.animal_card_effects_enabled is True
        assert config_result.critical_card_effects_enabled is True
        assert config_result.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID
        assert config_result.cards_per_player == 3
        assert simulation_result.color_effects_enabled is False
        assert simulation_result.animal_card_effects_enabled is True
        assert simulation_result.critical_card_effects_enabled is True
        assert simulation_result.critical_deck_profile_id == V05_HUNGER_DECK_PROFILE_ID
        assert simulation_result.cards_per_player == 3


def test_parametric_runner_preserves_animal_lineup_in_all_configurations():
    base_config = replace(
        get_v05_config_for_players(2),
        animal_lineup=(Color.BLUE, Color.YELLOW),
    )

    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=1,
        seed=42,
        initial_lives_values=[10, 12],
        critical_wounds_values=[5, 6],
        color_effects_values=[False],
        strategy_names="v05_animal_aware",
        base_config=base_config,
    )

    assert result.animal_lineup == (Color.BLUE, Color.YELLOW)
    for config_result in result.config_results:
        assert config_result.animal_lineup == (Color.BLUE, Color.YELLOW)
        assert config_result.simulation_result.animal_lineup == (
            Color.BLUE,
            Color.YELLOW,
        )
        assert [
            player.color
            for player in config_result.simulation_result.game_results[0].final_players
        ] == [Color.BLUE, Color.YELLOW]


def test_parametric_runner_without_base_config_keeps_legacy_defaults():
    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=1,
        seed=42,
        initial_lives_values=[18],
        critical_wounds_values=[3],
        color_effects_values=[True],
        strategy_names="random",
    )

    config_result = result.config_results[0]

    assert config_result.animal_card_effects_enabled is False
    assert config_result.critical_card_effects_enabled is False


def test_parametric_runner_without_animal_lineup_keeps_default_player_colors():
    result = ParametricSimulationRunner().run(
        players_count=3,
        games_per_config=1,
        seed=42,
        initial_lives_values=[18],
        critical_wounds_values=[3],
        color_effects_values=[True],
        strategy_names="random",
    )

    final_players = result.config_results[0].simulation_result.game_results[0].final_players
    assert [player.color for player in final_players] == [
        Color.BLUE,
        Color.RED,
        Color.GREEN,
    ]


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


def test_parametric_export_includes_v05_config_fields(tmp_path):
    result = ParametricSimulationRunner().run(
        players_count=4,
        games_per_config=1,
        seed=42,
        initial_lives_values=[20],
        critical_wounds_values=[4],
        color_effects_values=[False],
        strategy_names="v05_animal_aware",
        base_config=get_v05_config_for_players(4),
    )

    exported_files = export_parametric_simulation_result(result, tmp_path)

    with exported_files["parametric_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    config_data = data["config_results"][0]
    assert config_data["animal_card_effects_enabled"] is True
    assert config_data["critical_card_effects_enabled"] is True
    assert config_data["critical_deck_profile_id"] == V05_HUNGER_DECK_PROFILE_ID
    assert config_data["cards_per_player"] == 3

    with exported_files["parametric_summary"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        row = next(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert row["animal_card_effects_enabled"] == "True"
    assert row["critical_card_effects_enabled"] == "True"
    assert row["critical_deck_profile_id"] == V05_HUNGER_DECK_PROFILE_ID
    assert row["cards_per_player"] == "3"


def test_parametric_export_includes_animal_lineup(tmp_path):
    result = ParametricSimulationRunner().run(
        players_count=2,
        games_per_config=1,
        seed=42,
        initial_lives_values=[10],
        critical_wounds_values=[5],
        color_effects_values=[False],
        strategy_names="v05_animal_aware",
        base_config=replace(
            get_v05_config_for_players(2),
            animal_lineup=(Color.BLUE, Color.YELLOW),
        ),
    )

    exported_files = export_parametric_simulation_result(result, tmp_path)

    with exported_files["parametric_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["animal_lineup"] == ["Panda", "Scoiattolo"]
    assert data["config_results"][0]["animal_lineup"] == ["Panda", "Scoiattolo"]

    with exported_files["parametric_summary"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        row = next(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert row["animal_lineup"] == "Panda|Scoiattolo"


def test_cli_parametric_preserves_v05_config_fields(tmp_path):
    command = [
        sys.executable,
        str(PROJECT_ROOT / "run_simulation.py"),
        "--players",
        "4",
        "--games",
        "1",
        "--seed",
        "42",
        "--parametric",
        "--strategy",
        "v05_animal_aware",
        "--lives-values",
        "20",
        "24",
        "--critical-wounds-values",
        "4",
        "5",
        "--color-effects",
        "off",
        "--animal-card-effects",
        "on",
        "--critical-card-effects",
        "on",
        "--export",
        "--output-dir",
        str(tmp_path),
    ]

    subprocess.run(command, check=True, capture_output=True, text=True)

    with (tmp_path / "parametric_stats.json").open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["tested_configs"] == 4
    for config_data in data["config_results"]:
        assert config_data["color_effects_enabled"] is False
        assert config_data["animal_card_effects_enabled"] is True
        assert config_data["critical_card_effects_enabled"] is True
        assert config_data["critical_deck_profile_id"] == V05_HUNGER_DECK_PROFILE_ID
        assert config_data["cards_per_player"] == 3


def test_cli_parametric_accepts_animal_lineup_and_exports_it(tmp_path):
    command = [
        sys.executable,
        str(PROJECT_ROOT / "run_simulation.py"),
        "--players",
        "2",
        "--games",
        "1",
        "--seed",
        "42",
        "--parametric",
        "--strategy",
        "v05_animal_aware",
        "--animal-lineup",
        "Panda",
        "Scoiattolo",
        "--lives-values",
        "10",
        "--critical-wounds-values",
        "5",
        "--color-effects",
        "off",
        "--animal-card-effects",
        "on",
        "--critical-card-effects",
        "on",
        "--export",
        "--output-dir",
        str(tmp_path),
    ]

    subprocess.run(command, check=True, capture_output=True, text=True)

    with (tmp_path / "parametric_stats.json").open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["animal_lineup"] == ["Panda", "Scoiattolo"]
    assert data["config_results"][0]["animal_lineup"] == ["Panda", "Scoiattolo"]
