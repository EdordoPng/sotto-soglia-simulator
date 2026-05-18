import csv
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.exporters import export_simulation_result
from sotto_soglia.simulation import SimulationRunner


def _small_simulation():
    return SimulationRunner().run(players_count=4, games_count=5, seed=42)


def test_export_creates_expected_files(tmp_path):
    simulation = _small_simulation()

    exported_files = export_simulation_result(simulation, tmp_path)

    assert exported_files["simulation_config"].exists()
    assert exported_files["aggregate_stats"].exists()
    assert exported_files["games_summary"].exists()
    assert exported_files["rounds_summary"].exists()


def test_aggregate_stats_json_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["aggregate_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["games_count"] == 5
    assert "average_rounds" in data
    assert "win_rate_by_color" in data


def test_simulation_config_json_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["simulation_config"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["players_count"] == 4
    assert data["games_count"] == 5
    assert data["base_seed"] == 42
    assert "generated_files" in data
    assert data["generated_files"]["games_summary"] == "games_summary.csv"


def test_games_summary_csv_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["games_summary"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 5
    for column in ["game_id", "seed", "rounds_count", "winner_ids", "is_draw"]:
        assert column in rows[0]


def test_rounds_summary_csv_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["rounds_summary"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows
    for column in [
        "game_id",
        "round_number",
        "lowest_value",
        "critical_wound_players",
        "eliminated_players",
    ]:
        assert column in rows[0]
