"""CSV and JSON exporters for simulation results."""

import csv
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from sotto_soglia import __version__
from sotto_soglia.models import EliminationReason, PlayerState
from sotto_soglia.parametric import ParametricSimulationResult
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
    if simulation_result.critical_card_effects_enabled:
        paths.update(
            {
                "critical_events": output_path / "critical_events.csv",
                "critical_deck_orders": output_path / "critical_deck_orders.csv",
                "critical_card_stats": output_path / "critical_card_stats.csv",
            }
        )

    config_data = {
        "players_count": simulation_result.players_count,
        "games_count": simulation_result.games_count,
        "base_seed": simulation_result.base_seed,
        "initial_lives": simulation_result.initial_lives,
        "critical_wounds_limit": simulation_result.critical_wounds_limit,
        "color_effects_enabled": simulation_result.color_effects_enabled,
        "critical_card_effects_enabled": simulation_result.critical_card_effects_enabled,
        "animal_card_effects_enabled": simulation_result.animal_card_effects_enabled,
        "critical_deck_profile_id": simulation_result.critical_deck_profile_id,
        "critical_deck_seed": simulation_result.critical_deck_seed,
        "critical_deck_order": simulation_result.critical_deck_order,
        "sono_ancora_qui_variant": simulation_result.sono_ancora_qui_variant,
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
    if simulation_result.critical_card_effects_enabled:
        write_critical_events_csv(paths["critical_events"], simulation_result)
        write_critical_deck_orders_csv(paths["critical_deck_orders"], simulation_result)
        write_critical_card_stats_csv(paths["critical_card_stats"], simulation_result)

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


def export_parametric_simulation_result(
    parametric_result: ParametricSimulationResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write compact parametric export files and return their paths."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    paths = {
        "parametric_stats": output_path / "parametric_stats.json",
        "parametric_summary": output_path / "parametric_summary.csv",
    }

    stats_data = {
        "players_count": parametric_result.players_count,
        "games_per_config": parametric_result.games_per_config,
        "tested_configs": parametric_result.tested_configs,
        "total_games": parametric_result.total_games,
        "base_seed": parametric_result.base_seed,
        "baseline_config": parametric_result.baseline_config,
        "config_results": [
            {
                "config_id": config_result.config_id,
                "seed": config_result.seed,
                "initial_lives": config_result.initial_lives,
                "critical_wounds_limit": config_result.critical_wounds_limit,
                "color_effects_enabled": config_result.color_effects_enabled,
                "is_baseline": config_result.is_baseline,
                "aggregate_stats": config_result.aggregate_stats,
            }
            for config_result in parametric_result.config_results
        ],
    }

    write_json(paths["parametric_stats"], stats_data)
    write_parametric_summary_csv(paths["parametric_summary"], parametric_result)

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


def write_parametric_summary_csv(
    path: str | Path,
    parametric_result: ParametricSimulationResult,
) -> None:
    """Write one CSV row per tested parametric configuration."""

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

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for config_result in parametric_result.config_results:
            stats = config_result.aggregate_stats
            writer.writerow(
                {
                    "config_id": config_result.config_id,
                    "is_baseline": config_result.is_baseline,
                    "seed": config_result.seed,
                    "players_count": parametric_result.players_count,
                    "games_count": parametric_result.games_per_config,
                    "initial_lives": config_result.initial_lives,
                    "critical_wounds_limit": config_result.critical_wounds_limit,
                    "color_effects_enabled": config_result.color_effects_enabled,
                    "average_rounds": f"{stats['average_rounds']:.2f}",
                    "min_rounds": stats["min_rounds"],
                    "max_rounds": stats["max_rounds"],
                    "draw_count": stats["draw_count"],
                    "draw_rate": f"{stats['draw_rate']:.6f}",
                    "eliminations_by_lives": stats["eliminations_by_lives"],
                    "eliminations_by_critical_wounds": stats[
                        "eliminations_by_critical_wounds"
                    ],
                    "average_winner_lives": f"{stats['average_winner_lives']:.2f}",
                    "average_winner_critical_wounds": (
                        f"{stats['average_winner_critical_wounds']:.2f}"
                    ),
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


def write_critical_deck_orders_csv(
    path: str | Path,
    simulation_result: SimulationResult,
) -> None:
    """Write one initial critical deck order row per game."""

    fieldnames = ["game_id", "critical_deck_order"]

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for game_result in simulation_result.game_results:
            writer.writerow(
                {
                    "game_id": game_result.game_id,
                    "critical_deck_order": ",".join(game_result.initial_critical_deck_order),
                }
            )


def write_critical_events_csv(
    path: str | Path,
    simulation_result: SimulationResult,
) -> None:
    """Write one row per critical card event."""

    fieldnames = [
        "game_id",
        "round_number",
        "draw_order",
        "player_id",
        "critical_card_id",
        "critical_card_name",
        "timing",
        "effect_triggered",
        "target_player_id",
        "life_delta_player",
        "life_delta_targets",
        "prevented_damage",
        "deck_position",
        "player_lives_after",
        "player_critical_wounds_after",
    ]

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for game_result in simulation_result.game_results:
            for event in game_result.critical_events:
                writer.writerow(
                    {
                        "game_id": event.game_id,
                        "round_number": event.round_number,
                        "draw_order": event.draw_order if event.draw_order is not None else "",
                        "player_id": event.player_id,
                        "critical_card_id": event.critical_card_id,
                        "critical_card_name": event.critical_card_name,
                        "timing": event.timing,
                        "effect_triggered": event.effect_triggered,
                        "target_player_id": (
                            event.target_player_id
                            if event.target_player_id is not None
                            else ""
                        ),
                        "life_delta_player": event.life_delta_player,
                        "life_delta_targets": serialize_player_damage_map(
                            event.life_delta_targets
                        ),
                        "prevented_damage": event.prevented_damage,
                        "deck_position": (
                            event.deck_position if event.deck_position is not None else ""
                        ),
                        "player_lives_after": event.player_lives_after,
                        "player_critical_wounds_after": (
                            event.player_critical_wounds_after
                        ),
                    }
                )


def write_critical_card_stats_csv(
    path: str | Path,
    simulation_result: SimulationResult,
) -> None:
    """Write aggregate critical-card stats by card id."""

    fieldnames = [
        "card_id",
        "draw_count",
        "activation_count",
        "total_life_delta",
        "average_life_delta",
        "win_count_after_draw",
        "elimination_count_after_draw",
    ]
    card_stats = simulation_result.aggregate_stats.get("critical_card_stats", {})

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
        writer.writeheader()

        for card_id, values in sorted(card_stats.items()):
            writer.writerow(
                {
                    "card_id": card_id,
                    "draw_count": values.get("draw_count", 0),
                    "activation_count": values.get("activation_count", 0),
                    "total_life_delta": values.get("total_life_delta", 0),
                    "average_life_delta": f"{values.get('average_life_delta', 0.0):.6f}",
                    "win_count_after_draw": values.get("win_count_after_draw", 0),
                    "elimination_count_after_draw": values.get(
                        "elimination_count_after_draw",
                        0,
                    ),
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
