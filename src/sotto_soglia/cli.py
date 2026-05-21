"""Command-line interface for the Sotto Soglia simulator."""

import argparse
from dataclasses import replace

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import (
    LEGACY_CRITICAL_DECK_PROFILE_ID,
    SONO_ANCORA_QUI_VARIANTS,
    validate_critical_deck_order,
)
from sotto_soglia.exporters import (
    export_parametric_simulation_result,
    export_simulation_result,
    export_strategy_tournament_result,
)
from sotto_soglia.models import Color
from sotto_soglia.parametric import (
    ParametricSimulationResult,
    ParametricSimulationRunner,
)
from sotto_soglia.simulation import SimulationRunner, SimulationResult
from sotto_soglia.strategies import AVAILABLE_STRATEGIES, create_strategy
from sotto_soglia.tournament import StrategyTournamentResult, StrategyTournamentRunner


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


def format_parametric_summary(
    result: ParametricSimulationResult,
    strategy_setup: str,
) -> str:
    """Format parametric simulation stats for terminal output."""

    lines = [
        "Sotto Soglia Parametric Simulation",
        f"Players: {result.players_count}",
        f"Games per config: {result.games_per_config}",
        f"Tested configs: {result.tested_configs}",
        f"Total games: {result.total_games}",
        f"Base seed: {result.base_seed}",
        f"Strategy setup: {strategy_setup}",
        "",
        "Results by configuration:",
        (
            "ID | Lives | Critical Wounds | Color Effects | Avg Rounds | Draw % | "
            "Life Eliminations | Critical Eliminations | Avg Winner Lives | "
            "Avg Winner CW"
        ),
    ]

    for config_result in result.config_results:
        stats = config_result.aggregate_stats
        marker = "* " if config_result.is_baseline else "  "
        color_effects = "ON" if config_result.color_effects_enabled else "OFF"
        lines.append(
            (
                f"{marker}{config_result.config_id:02d} | "
                f"{config_result.initial_lives} | "
                f"{config_result.critical_wounds_limit} | "
                f"{color_effects} | "
                f"{stats['average_rounds']:.2f} | "
                f"{stats['draw_rate'] * 100:.2f}% | "
                f"{stats['eliminations_by_lives']} | "
                f"{stats['eliminations_by_critical_wounds']} | "
                f"{stats['average_winner_lives']:.2f} | "
                f"{stats['average_winner_critical_wounds']:.2f}"
            )
        )

    lines.append("")
    lines.append("* baseline = 18 lives / 3 critical wounds / color effects ON")
    return "\n".join(lines)


def format_tournament_summary(result: StrategyTournamentResult) -> str:
    """Format counterbalanced strategy tournament stats for terminal output."""

    stats = result.aggregate_stats
    strategy_names = ", ".join(result.strategy_names)
    lines = [
        "Sotto Soglia Strategy Tournament",
        f"Players: {result.players_count}",
        f"Strategies: {strategy_names}",
        f"Lineups tested: {result.lineups_tested}",
        f"Games per lineup: {result.games_per_lineup}",
        f"Total games: {result.total_games}",
        f"Base seed: {result.base_seed}",
        "",
        "Results:",
        f"- Average rounds: {stats['average_rounds']:.2f}",
        f"- Draws: {stats['draw_count']} ({stats['draw_rate'] * 100:.2f}%)",
        f"- Eliminations by lives: {stats['eliminations_by_lives']}",
        (
            "- Eliminations by critical wounds: "
            f"{stats['eliminations_by_critical_wounds']}"
        ),
        "",
        "Win rate by strategy:",
    ]

    for strategy_name in sorted(stats["wins_by_strategy"]):
        wins = stats["wins_by_strategy"].get(strategy_name, 0)
        rate = stats["win_rate_by_strategy"].get(strategy_name, 0.0)
        lines.append(f"- {strategy_name}: {wins} wins ({rate * 100:.2f}%)")

    lines.extend(["", "Appearances by strategy/player:"])
    appearances = stats["appearances_by_strategy_player_id"]
    for strategy_name in sorted(appearances):
        player_counts = ", ".join(
            f"P{player_id}={count}"
            for player_id, count in sorted(appearances[strategy_name].items())
        )
        lines.append(f"- {strategy_name}: {player_counts}")

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


def build_strategy_names_from_args(args: argparse.Namespace) -> str | list[str]:
    """Return strategy names from parsed CLI arguments."""

    if args.strategy and args.strategies:
        raise ValueError("Use either --strategy or --strategies, not both")

    if args.strategies:
        if len(args.strategies) != args.players:
            raise ValueError("--strategies must provide one strategy per player")
        return list(args.strategies)

    return args.strategy or "random"


def parse_color_effects_values(value: str) -> list[bool]:
    """Parse the parametric color-effects option."""

    if value == "both":
        return [True, False]
    if value == "on":
        return [True]
    if value == "off":
        return [False]
    raise ValueError("--color-effects must be one of: both, on, off")


def parse_on_off(value: str, option_name: str) -> bool:
    """Parse an on/off CLI flag."""

    if value == "on":
        return True
    if value == "off":
        return False
    raise ValueError(f"{option_name} must be one of: on, off")


def format_strategy_setup(strategy_names: str | list[str]) -> str:
    """Format strategy settings for terminal output."""

    if isinstance(strategy_names, str):
        return strategy_names
    return ", ".join(strategy_names)


def build_game_config_from_args(args: argparse.Namespace) -> GameConfig:
    """Create game config values shared by normal, parametric and tournament runs."""

    critical_deck_order = (
        validate_critical_deck_order(args.critical_deck_order)
        if args.critical_deck_order
        else None
    )
    config = get_v05_config_for_players(args.players)
    config_values = {
        "critical_deck_seed": args.critical_deck_seed,
        "critical_deck_order": critical_deck_order,
        "sono_ancora_qui_variant": args.sono_ancora_qui_variant,
    }
    if args.critical_card_effects != "auto":
        config_values["critical_card_effects_enabled"] = parse_on_off(
            args.critical_card_effects,
            "--critical-card-effects",
        )
    if args.animal_card_effects != "auto":
        config_values["animal_card_effects_enabled"] = parse_on_off(
            args.animal_card_effects,
            "--animal-card-effects",
        )
    if critical_deck_order is not None:
        config_values["critical_deck_profile_id"] = LEGACY_CRITICAL_DECK_PROFILE_ID
    if args.initial_lives is not None:
        if args.initial_lives <= 0:
            raise ValueError("--initial-lives must be greater than 0")
        config_values["initial_lives"] = args.initial_lives
    if args.critical_wounds_max is not None:
        if args.critical_wounds_max <= 0:
            raise ValueError("--critical-wounds-max must be greater than 0")
        config_values["critical_wounds_limit"] = args.critical_wounds_max

    return replace(config, **config_values)


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
        "--tournament-strategies",
        nargs="+",
        choices=sorted(AVAILABLE_STRATEGIES),
        help="Counterbalanced tournament strategies, one per player.",
    )
    parser.add_argument(
        "--parametric",
        action="store_true",
        help="Run a parametric balance simulation grid.",
    )
    parser.add_argument(
        "--lives-values",
        nargs="+",
        type=int,
        default=[15, 18, 20],
        help="Initial lives values tested in parametric mode.",
    )
    parser.add_argument(
        "--critical-wounds-values",
        nargs="+",
        type=int,
        default=[2, 3, 4],
        help="Critical wound limits tested in parametric mode.",
    )
    parser.add_argument(
        "--color-effects",
        choices=["both", "on", "off"],
        default="both",
        help="Color effects values tested in parametric mode.",
    )
    parser.add_argument(
        "--plot-parametric",
        metavar="PATH",
        help="Generate plots from an exported parametric_summary.csv file.",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export simulation results to CSV and JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for exported or generated files.",
    )
    parser.add_argument(
        "--initial-lives",
        type=int,
        default=None,
        help="Override initial lives for a standard simulation run.",
    )
    parser.add_argument(
        "--critical-wounds-max",
        type=int,
        default=None,
        help="Override the critical wound elimination threshold.",
    )
    parser.add_argument(
        "--critical-card-effects",
        choices=["auto", "off", "on"],
        default="auto",
        help=(
            "Critical wound/Affamato card effects: auto keeps the selected "
            "preset value, on/off force an override."
        ),
    )
    parser.add_argument(
        "--animal-card-effects",
        choices=["auto", "off", "on"],
        default="auto",
        help=(
            "Animal card effects: auto keeps the selected preset value, "
            "on/off force an override."
        ),
    )
    parser.add_argument(
        "--critical-deck-seed",
        type=int,
        default=None,
        help="Optional seed dedicated to critical wound deck order generation.",
    )
    parser.add_argument(
        "--critical-deck-order",
        default=None,
        help="Fixed comma-separated 16-card critical wound deck order.",
    )
    parser.add_argument(
        "--sono-ancora-qui-variant",
        choices=SONO_ANCORA_QUI_VARIANTS,
        default="single_2",
        help="Experimental Sono ancora qui variant used when critical-card-effects is on (default: single_2).",
    )

    args = parser.parse_args()
    if args.plot_parametric:
        if args.parametric:
            parser.error("Use --plot-parametric without --parametric")
        if args.tournament_strategies:
            parser.error("Use --plot-parametric without --tournament-strategies")
        if args.export:
            parser.error("Use --plot-parametric without --export")
        if args.strategy or args.strategies:
            parser.error("Use --plot-parametric without --strategy or --strategies")

        try:
            from sotto_soglia.plots import generate_parametric_plots
        except ModuleNotFoundError as error:
            if error.name == "matplotlib":
                parser.error(
                    "matplotlib is required for --plot-parametric. "
                    "Install project requirements first."
                )
            raise

        try:
            generated_plots = generate_parametric_plots(
                args.plot_parametric,
                args.output_dir or "results/plots",
            )
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))

        print("Generated plots:")
        for path in generated_plots:
            print(f"- {path}")
        return

    if args.parametric:
        if args.tournament_strategies:
            parser.error("Parametric tournament is not implemented yet.")

        try:
            strategy_names = build_strategy_names_from_args(args)
            critical_config = build_game_config_from_args(args)
            result = ParametricSimulationRunner().run(
                players_count=args.players,
                games_per_config=args.games,
                seed=args.seed,
                initial_lives_values=args.lives_values,
                critical_wounds_values=args.critical_wounds_values,
                color_effects_values=parse_color_effects_values(args.color_effects),
                strategy_names=strategy_names,
                critical_card_effects_enabled=(
                    critical_config.critical_card_effects_enabled
                ),
                critical_deck_seed=critical_config.critical_deck_seed,
                critical_deck_order=critical_config.critical_deck_order,
                sono_ancora_qui_variant=critical_config.sono_ancora_qui_variant,
            )
        except ValueError as error:
            parser.error(str(error))

        print(format_parametric_summary(result, format_strategy_setup(strategy_names)))

        if args.export:
            exported_files = export_parametric_simulation_result(
                result,
                args.output_dir or "results",
            )
            print("")
            print("Exported files:")
            for path in exported_files.values():
                print(f"- {path}")
        return

    if args.tournament_strategies:
        if args.strategy or args.strategies:
            parser.error(
                "Use --tournament-strategies without --strategy or --strategies"
            )
        try:
            critical_config = build_game_config_from_args(args)
            result = StrategyTournamentRunner().run(
                players_count=args.players,
                strategy_names=args.tournament_strategies,
                games_per_lineup=args.games,
                seed=args.seed,
                config=critical_config,
            )
        except ValueError as error:
            parser.error(str(error))

        print(format_tournament_summary(result))

        if args.export:
            exported_files = export_strategy_tournament_result(
                result,
                args.output_dir or "results",
            )
            print("")
            print("Exported files:")
            for path in exported_files.values():
                print(f"- {path}")
        return

    try:
        strategies = build_strategies_from_args(args)
        config = build_game_config_from_args(args)
    except ValueError as error:
        parser.error(str(error))

    result = SimulationRunner().run(
        players_count=args.players,
        games_count=args.games,
        seed=args.seed,
        strategies=strategies,
        config=config,
    )
    print(format_simulation_summary(result))

    if args.export:
        exported_files = export_simulation_result(result, args.output_dir or "results")
        print("")
        print("Exported files:")
        for path in exported_files.values():
            print(f"- {path}")
