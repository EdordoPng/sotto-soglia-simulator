"""Plot generation helpers for exported simulation results."""

import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sotto_soglia.exporters import CSV_DELIMITER


def generate_parametric_plots(csv_path: str | Path, output_dir: str | Path) -> list[Path]:
    """Generate report-ready plots from an exported parametric summary CSV."""

    rows = read_semicolon_csv(csv_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plot_rows = [_normalize_parametric_row(row) for row in rows]
    created_files = [
        _plot_average_rounds(plot_rows, output_path),
        _plot_draw_rate(plot_rows, output_path),
        _plot_eliminations(plot_rows, output_path),
        _plot_winner_status(plot_rows, output_path),
        _plot_color_effects_comparison(plot_rows, output_path),
    ]
    return created_files


def read_semicolon_csv(path: str | Path) -> list[dict[str, str]]:
    """Read a semicolon-delimited CSV file."""

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    if not rows:
        raise ValueError(f"CSV file has no data rows: {csv_path}")
    return rows


def parse_bool(value: Any) -> bool:
    """Parse common CSV boolean spellings."""

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value}")


def config_label(row: dict[str, Any]) -> str:
    """Return a compact rules configuration label."""

    color_effects = "ON" if parse_bool(row["color_effects_enabled"]) else "OFF"
    label = (
        f"{int(row['initial_lives'])}/"
        f"{int(row['critical_wounds_limit'])}/"
        f"{color_effects}"
    )
    if find_baseline(row):
        return f"{label}*"
    return label


def find_baseline(row: dict[str, Any]) -> bool:
    """Return whether a CSV row represents the standard baseline config."""

    if "is_baseline" in row and str(row["is_baseline"]).strip():
        return parse_bool(row["is_baseline"])
    return (
        int(row["initial_lives"]) == 18
        and int(row["critical_wounds_limit"]) == 3
        and parse_bool(row["color_effects_enabled"])
    )


def _normalize_parametric_row(row: dict[str, str]) -> dict[str, Any]:
    """Convert CSV strings to plotting-friendly values."""

    required_columns = [
        "initial_lives",
        "critical_wounds_limit",
        "color_effects_enabled",
        "average_rounds",
        "draw_rate",
        "eliminations_by_lives",
        "eliminations_by_critical_wounds",
        "average_winner_lives",
        "average_winner_critical_wounds",
    ]
    missing_columns = [column for column in required_columns if column not in row]
    if missing_columns:
        raise ValueError(f"Missing required CSV columns: {', '.join(missing_columns)}")

    normalized = {
        "initial_lives": int(row["initial_lives"]),
        "critical_wounds_limit": int(row["critical_wounds_limit"]),
        "color_effects_enabled": parse_bool(row["color_effects_enabled"]),
        "average_rounds": float(row["average_rounds"]),
        "draw_rate": float(row["draw_rate"]),
        "eliminations_by_lives": int(row["eliminations_by_lives"]),
        "eliminations_by_critical_wounds": int(
            row["eliminations_by_critical_wounds"]
        ),
        "average_winner_lives": float(row["average_winner_lives"]),
        "average_winner_critical_wounds": float(
            row["average_winner_critical_wounds"]
        ),
    }
    normalized["is_baseline"] = find_baseline(row)
    normalized["label"] = config_label(normalized)
    return normalized


def _plot_average_rounds(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [row["label"] for row in rows]
    values = [row["average_rounds"] for row in rows]
    colors = [_bar_color(row) for row in rows]

    ax.bar(labels, values, color=colors)
    ax.set_title("Average Rounds by Configuration")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Average rounds")
    _finish_x_axis(ax)
    return _save_plot(fig, output_dir / "average_rounds_by_config.png")


def _plot_draw_rate(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [row["label"] for row in rows]
    values = [row["draw_rate"] * 100 for row in rows]
    colors = [_bar_color(row) for row in rows]

    ax.bar(labels, values, color=colors)
    ax.set_title("Draw Rate by Configuration")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Draw rate (%)")
    _finish_x_axis(ax)
    return _save_plot(fig, output_dir / "draw_rate_by_config.png")


def _plot_eliminations(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [row["label"] for row in rows]
    x_positions = list(range(len(rows)))
    width = 0.38

    ax.bar(
        [position - width / 2 for position in x_positions],
        [row["eliminations_by_lives"] for row in rows],
        width=width,
        label="Lives",
        color="#4C78A8",
    )
    ax.bar(
        [position + width / 2 for position in x_positions],
        [row["eliminations_by_critical_wounds"] for row in rows],
        width=width,
        label="Critical wounds",
        color="#F58518",
    )
    ax.set_title("Eliminations by Configuration")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Eliminations")
    ax.set_xticks(x_positions, labels)
    ax.legend()
    _finish_x_axis(ax)
    return _save_plot(fig, output_dir / "eliminations_by_config.png")


def _plot_winner_status(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [row["label"] for row in rows]
    x_positions = list(range(len(rows)))

    ax.plot(
        x_positions,
        [row["average_winner_lives"] for row in rows],
        marker="o",
        label="Average winner lives",
        color="#4C78A8",
    )
    ax.plot(
        x_positions,
        [row["average_winner_critical_wounds"] for row in rows],
        marker="o",
        label="Average winner critical wounds",
        color="#F58518",
    )
    ax.set_title("Winner Final Status by Configuration")
    ax.set_xlabel("Configuration")
    ax.set_ylabel("Average final status")
    ax.set_xticks(x_positions, labels)
    ax.legend()
    _finish_x_axis(ax)
    return _save_plot(fig, output_dir / "winner_status_by_config.png")


def _plot_color_effects_comparison(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    grouped: dict[tuple[int, int], dict[bool, float]] = {}
    for row in rows:
        key = (row["initial_lives"], row["critical_wounds_limit"])
        grouped.setdefault(key, {})[row["color_effects_enabled"]] = row[
            "average_rounds"
        ]

    labels = [f"{lives}/{critical_wounds}" for lives, critical_wounds in grouped]
    x_positions = list(range(len(labels)))
    width = 0.38

    ax.bar(
        [position - width / 2 for position in x_positions],
        [grouped[key].get(True, 0.0) for key in grouped],
        width=width,
        label="Color effects ON",
        color="#4C78A8",
    )
    ax.bar(
        [position + width / 2 for position in x_positions],
        [grouped[key].get(False, 0.0) for key in grouped],
        width=width,
        label="Color effects OFF",
        color="#F58518",
    )
    ax.set_title("Color Effects Comparison")
    ax.set_xlabel("Lives / Critical wounds")
    ax.set_ylabel("Average rounds")
    ax.set_xticks(x_positions, labels)
    ax.legend()
    _finish_x_axis(ax)
    return _save_plot(fig, output_dir / "color_effects_comparison.png")


def _bar_color(row: dict[str, Any]) -> str:
    """Return a distinct color for baseline bars."""

    if row["is_baseline"]:
        return "#E45756"
    return "#4C78A8"


def _finish_x_axis(ax) -> None:
    """Apply common x-axis label formatting."""

    ax.tick_params(axis="x", labelrotation=45)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")


def _save_plot(fig, path: Path) -> Path:
    """Save and close a matplotlib figure."""

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path
