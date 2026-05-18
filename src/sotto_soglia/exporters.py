"""CSV and JSON exporters for simulation results."""

import csv
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from sotto_soglia import __version__
from sotto_soglia.models import EliminationReason, PlayerState
from sotto_soglia.simulation import SimulationResult


CSV_DELIMITER = ";"


def export_simulation_result(
    simulation_result: SimulationResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write standard export files and return their paths."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    paths = {
        "simulation_config": output_path / "simulation_config.json",
        "aggregate_stats": output_path / "aggregate_stats.json",
        "games_summary": output_path / "games_summary.csv",
        "rounds_summary": output_path / "rounds_summary.csv",
    }

    config_data = {
        "players_count": simulation_result.players_count,
        "games_count": simulation_result.games_count,
        "base_seed": simulation_result.base_seed,
        "generated_files": {
            name: path.name
            for name, path in paths.items()
        },
        "project_version": __version__,
        "note": "Sotto Soglia simulation export",
    }

    write_json(paths["simulation_config"], config_data)
    write_json(paths["aggregate_stats"], simulation_result.aggregate_stats)
    write_games_summary_csv(paths["games_summary"], simulation_result)
    write_rounds_summary_csv(paths["rounds_summary"], simulation_result)

    return paths


def export_strategy_tournament_result(
    tournament_result,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write compact tournament export files and return their paths."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    paths = {
        "strategy_tournament_stats": output_path / "strategy_tournament_stats.json",
        "strategy_tournament_lineups": output_path / "strategy_tournament_lineups.csv",
    }

    stats_data = {
        "players_count": tournament_result.players_count,
        "strategies": tournament_result.strategy_names,
        "games_per_lineup": tournament_result.games_per_lineup,
        "lineups_tested": tournament_result.lineups_tested,
        "total_games": tournament_result.total_games,
        "base_seed": tournament_result.base_seed,
        "aggregate_stats": tournament_result.aggregate_stats,
    }

    write_json(paths["strategy_tournament_stats"], stats_data)
    write_strategy_tournament_lineups_csv(
        paths["strategy_tournament_lineups"],
        tournament_result,
    )

    return paths


def write_json(path: str | Path, data: Any) -> None:
    """Write JSON data with stable formatting."""

    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(to_jsonable(data), file, indent=2, ensure_ascii=False)
        file.write("\n")


def write_games_summary_csv(
    path: str | Path,
    simulation_result: SimulationResult,
) -> None:
    """Write one CSV row per simulated game."""

    fieldnames = [
        "game_id",
        "seed",
        "players_count",
        "rounds_count",
        "winner_ids",
        "is_draw",
        "strategy_names",
        "winner_colors",
        "winner_strategies",
        "final_alive_players",
        "eliminated_by_lives",
        "eliminated_by_critical_wounds",
        "winner_lives",
        "winner_critical_wounds",
    ]

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for game_result in simulation_result.game_results:
            player_by_id = get_player_by_id(game_result.final_players)
            winners = [
                player_by_id[player_id]
                for player_id in game_result.winner_ids
                if player_id in player_by_id
            ]
            writer.writerow(
                {
                    "game_id": game_result.game_id,
                    "seed": game_result.seed,
                    "players_count": simulation_result.players_count,
                    "rounds_count": game_result.rounds_count,
                    "winner_ids": join_ids(game_result.winner_ids),
                    "is_draw": game_result.is_draw,
                    "strategy_names": "|".join(
                        player.strategy_name
                        for player in game_result.final_players
                    ),
                    "winner_colors": "|".join(player.color.name for player in winners),
                    "winner_strategies": "|".join(
                        player.strategy_name
                        for player in winners
                    ),
                    "final_alive_players": join_ids(
                        player.player_id
                        for player in game_result.final_players
                        if player.is_alive
                    ),
                    "eliminated_by_lives": _count_eliminations(
                        game_result.final_players,
                        EliminationReason.LIVES,
                        game_result.winner_ids,
                        game_result.is_draw,
                    ),
                    "eliminated_by_critical_wounds": _count_eliminations(
                        game_result.final_players,
                        EliminationReason.CRITICAL_WOUNDS,
                        game_result.winner_ids,
                        game_result.is_draw,
                    ),
                    "winner_lives": join_ids(player.lives for player in winners),
                    "winner_critical_wounds": join_ids(
                        player.critical_wounds
                        for player in winners
                    ),
                }
            )


def write_strategy_tournament_lineups_csv(
    path: str | Path,
    tournament_result,
) -> None:
    """Write one CSV row per tournament lineup."""

    fieldnames = [
        "lineup_id",
        "lineup_seed",
        "strategies_by_player",
        "games_count",
        "average_rounds",
        "draw_count",
        "wins_by_strategy",
    ]

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for lineup_result in tournament_result.lineup_results:
            stats = lineup_result.aggregate_stats
            writer.writerow(
                {
                    "lineup_id": lineup_result.lineup_id,
                    "lineup_seed": lineup_result.lineup_seed,
                    "strategies_by_player": serialize_strategy_player_map(
                        lineup_result.strategies_by_player
                    ),
                    "games_count": lineup_result.simulation_result.games_count,
                    "average_rounds": f"{stats['average_rounds']:.2f}",
                    "draw_count": stats["draw_count"],
                    "wins_by_strategy": serialize_name_count_map(
                        stats["wins_by_strategy"]
                    ),
                }
            )


def write_rounds_summary_csv(
    path: str | Path,
    simulation_result: SimulationResult,
) -> None:
    """Write one compact CSV row per round."""

    fieldnames = [
        "game_id",
        "seed",
        "round_number",
        "lowest_value",
        "critical_wound_players",
        "eliminated_players",
        "total_damage_by_player",
        "alive_players_after_round",
    ]

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for game_result in simulation_result.game_results:
            alive_player_ids = {
                player.player_id
                for player in game_result.final_players
            }
            for round_result in game_result.round_history:
                alive_player_ids -= set(round_result.eliminated_players)
                writer.writerow(
                    {
                        "game_id": game_result.game_id,
                        "seed": game_result.seed,
                        "round_number": round_result.round_number,
                        "lowest_value": round_result.lowest_value,
                        "critical_wound_players": join_ids(
                            round_result.critical_wound_players
                        ),
                        "eliminated_players": join_ids(round_result.eliminated_players),
                        "total_damage_by_player": serialize_player_damage_map(
                            round_result.total_damage_by_player
                        ),
                        "alive_players_after_round": join_ids(sorted(alive_player_ids)),
                    }
                )


def to_jsonable(value: Any) -> Any:
    """Convert common project objects into JSON-serializable values."""

    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {
            str(to_jsonable(key)): to_jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def join_ids(values) -> str:
    """Serialize ids or numeric values as a pipe-separated string."""

    return "|".join(str(value) for value in values)


def serialize_player_damage_map(damage_by_player: dict[int, int]) -> str:
    """Serialize player damage as 'player:damage' entries."""

    return "|".join(
        f"{player_id}:{damage}"
        for player_id, damage in sorted(damage_by_player.items())
    )


def serialize_strategy_player_map(strategies_by_player: dict[int, str]) -> str:
    """Serialize strategy assignments as 'P1:name' entries."""

    return "|".join(
        f"P{player_id}:{strategy_name}"
        for player_id, strategy_name in sorted(strategies_by_player.items())
    )


def serialize_name_count_map(values: dict[str, int]) -> str:
    """Serialize name/count mappings as 'name:count' entries."""

    return "|".join(
        f"{name}:{count}"
        for name, count in sorted(values.items())
    )


def get_player_by_id(players: list[PlayerState]) -> dict[int, PlayerState]:
    """Return players indexed by player id."""

    return {player.player_id: player for player in players}


def _count_eliminations(
    players: list[PlayerState],
    reason: EliminationReason,
    winner_ids: list[int],
    is_draw: bool,
) -> int:
    """Count final eliminations, excluding non-draw tiebreak winners."""

    winner_id_set = set(winner_ids)
    return sum(
        1
        for player in players
        if player.elimination_reason == reason
        and (is_draw or player.player_id not in winner_id_set)
    )
