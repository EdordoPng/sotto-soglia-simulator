import csv
from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.exporters import CSV_DELIMITER
from sotto_soglia.plots import generate_parametric_plots


def _write_parametric_csv(path: Path) -> None:
    fieldnames = [
        "config_id",
        "is_baseline",
        "seed",
        "players_count",
        "games_count",
        "initial_lives",
        "critical_wounds_limit",
        "color_effects_enabled",
        "average_rounds",
        "min_rounds",
        "max_rounds",
        "draw_count",
        "draw_rate",
        "eliminations_by_lives",
        "eliminations_by_critical_wounds",
        "average_winner_lives",
        "average_winner_critical_wounds",
        "wins_by_strategy",
    ]
    rows = [
        {
            "config_id": 1,
            "is_baseline": False,
            "seed": 42,
            "players_count": 4,
            "games_count": 10,
            "initial_lives": 15,
            "critical_wounds_limit": 2,
            "color_effects_enabled": True,
            "average_rounds": "4.50",
            "min_rounds": 3,
            "max_rounds": 6,
            "draw_count": 1,
            "draw_rate": "0.100000",
            "eliminations_by_lives": 2,
            "eliminations_by_critical_wounds": 28,
            "average_winner_lives": "5.20",
            "average_winner_critical_wounds": "0.90",
            "wins_by_strategy": "random:9",
        },
        {
            "config_id": 2,
            "is_baseline": False,
            "seed": 52,
            "players_count": 4,
            "games_count": 10,
            "initial_lives": 15,
            "critical_wounds_limit": 2,
            "color_effects_enabled": False,
            "average_rounds": "4.70",
            "min_rounds": 3,
            "max_rounds": 7,
            "draw_count": 0,
            "draw_rate": "0.000000",
            "eliminations_by_lives": 1,
            "eliminations_by_critical_wounds": 29,
            "average_winner_lives": "4.80",
            "average_winner_critical_wounds": "1.00",
            "wins_by_strategy": "random:10",
        },
        {
            "config_id": 3,
            "is_baseline": True,
            "seed": 62,
            "players_count": 4,
            "games_count": 10,
            "initial_lives": 18,
            "critical_wounds_limit": 3,
            "color_effects_enabled": True,
            "average_rounds": "6.80",
            "min_rounds": 5,
            "max_rounds": 9,
            "draw_count": 1,
            "draw_rate": "0.100000",
            "eliminations_by_lives": 12,
            "eliminations_by_critical_wounds": 18,
            "average_winner_lives": "2.10",
            "average_winner_critical_wounds": "2.00",
            "wins_by_strategy": "random:9",
        },
        {
            "config_id": 4,
            "is_baseline": False,
            "seed": 72,
            "players_count": 4,
            "games_count": 10,
            "initial_lives": 18,
            "critical_wounds_limit": 3,
            "color_effects_enabled": False,
            "average_rounds": "7.10",
            "min_rounds": 5,
            "max_rounds": 10,
            "draw_count": 2,
            "draw_rate": "0.200000",
            "eliminations_by_lives": 10,
            "eliminations_by_critical_wounds": 22,
            "average_winner_lives": "1.80",
            "average_winner_critical_wounds": "2.10",
            "wins_by_strategy": "random:8",
        },
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()
        writer.writerows(rows)


def test_generate_parametric_plots_creates_expected_png_files(tmp_path):
    csv_path = tmp_path / "parametric_summary.csv"
    output_dir = tmp_path / "plots"
    _write_parametric_csv(csv_path)

    generated_plots = generate_parametric_plots(csv_path, output_dir)

    generated_names = {path.name for path in generated_plots}
    expected_names = {
        "average_rounds_by_config.png",
        "draw_rate_by_config.png",
        "eliminations_by_config.png",
        "winner_status_by_config.png",
        "color_effects_comparison.png",
    }

    assert expected_names <= generated_names
    for plot_path in generated_plots:
        assert plot_path.exists()
        assert plot_path.stat().st_size > 0


def test_generate_parametric_plots_missing_csv_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        generate_parametric_plots(tmp_path / "missing.csv", tmp_path / "plots")
