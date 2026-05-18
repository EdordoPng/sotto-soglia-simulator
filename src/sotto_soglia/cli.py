"""Command-line interface for the Sotto Soglia simulator."""

import argparse

from sotto_soglia.exporters import export_simulation_result
from sotto_soglia.models import Color
from sotto_soglia.simulation import SimulationRunner, SimulationResult
from sotto_soglia.strategies import AVAILABLE_STRATEGIES, create_strategy


def format_simulation_summary(result: SimulationResult) -> str:
    """Format aggregate simulation stats for terminal output."""

    stats = result.aggregate_stats
    lines = [
        "Sotto Soglia Simulation",
        f"Players: {result.players_count}",
        f"Games: {result.games_count}",
        f"Base seed: {result.base_seed}",
        "",
        "Results:",
        f"- Average rounds: {stats['average_rounds']:.2f}",
        f"- Min rounds: {stats['min_rounds']}",
        f"- Max rounds: {stats['max_rounds']}",
        f"- Draws: {stats['draw_count']} ({stats['draw_rate'] * 100:.2f}%)",
        f"- Eliminations by lives: {stats['eliminations_by_lives']}",
        (
            "- Eliminations by critical wounds: "
            f"{stats['eliminations_by_critical_wounds']}"
        ),
        f"- Average winner lives: {stats['average_winner_lives']:.2f}",
        (
            "- Average winner critical wounds: "
            f"{stats['average_winner_critical_wounds']:.2f}"
        ),
        "",
        "Win rate by player:",
    ]

    for player_id in range(1, result.players_count + 1):
        wins = stats["wins_by_player_id"].get(player_id, 0)
        rate = stats["win_rate_by_player_id"].get(player_id, 0.0)
        lines.append(f"- Player {player_id}: {wins} wins ({rate * 100:.2f}%)")

    lines.extend(["", "Win rate by color:"])
    for color in list(Color)[: result.players_count]:
        wins = stats["wins_by_color"].get(color.name, 0)
        rate = stats["win_rate_by_color"].get(color.name, 0.0)
        lines.append(f"- {color.name}: {wins} wins ({rate * 100:.2f}%)")

    lines.extend(["", "Win rate by strategy:"])
    for strategy_name in sorted(stats["wins_by_strategy"]):
        wins = stats["wins_by_strategy"].get(strategy_name, 0)
        rate = stats["win_rate_by_strategy"].get(strategy_name, 0.0)
        lines.append(f"- {strategy_name}: {wins} wins ({rate * 100:.2f}%)")

    return "\n".join(lines)


def build_strategies_from_args(args: argparse.Namespace):
    """Create strategy instances from parsed CLI arguments."""

    if args.strategy and args.strategies:
        raise ValueError("Use either --strategy or --strategies, not both")

    if args.strategies:
        if len(args.strategies) != args.players:
            raise ValueError("--strategies must provide one strategy per player")
        return [create_strategy(name) for name in args.strategies]

    return create_strategy(args.strategy or "random")


def main() -> None:
    """Parse CLI arguments and run aggregate simulations."""

    parser = argparse.ArgumentParser(description="Sotto Soglia simulation runner.")
    parser.add_argument("--players", type=int, default=4, help="Number of players.")
    parser.add_argument("--games", type=int, default=1, help="Number of games to simulate.")
    parser.add_argument("--seed", type=int, default=0, help="Base random seed.")
    parser.add_argument(
        "--strategy",
        choices=sorted(AVAILABLE_STRATEGIES),
        help="Strategy used by all players.",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=sorted(AVAILABLE_STRATEGIES),
        help="One strategy per player, in player id order.",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export simulation results to CSV and JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Output directory for exported files.",
    )

    args = parser.parse_args()
    try:
        strategies = build_strategies_from_args(args)
    except ValueError as error:
        parser.error(str(error))

    result = SimulationRunner().run(
        players_count=args.players,
        games_count=args.games,
        seed=args.seed,
        strategies=strategies,
    )
    print(format_simulation_summary(result))

    if args.export:
        exported_files = export_simulation_result(result, args.output_dir)
        print("")
        print("Exported files:")
        for path in exported_files.values():
            print(f"- {path}")
