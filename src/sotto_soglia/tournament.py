"""Counterbalanced strategy tournament runner."""

from dataclasses import dataclass, field
from itertools import permutations

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.simulation import SimulationResult, SimulationRunner
from sotto_soglia.statistics import StatisticAggregator
from sotto_soglia.strategies import create_strategy


@dataclass
class StrategyTournamentLineupResult:
    """Result for one strategy lineup in a tournament."""

    lineup_id: int
    lineup_seed: int
    strategies_by_player: dict[int, str]
    simulation_result: SimulationResult
    aggregate_stats: dict = field(default_factory=dict)


@dataclass
class StrategyTournamentResult:
    """Aggregated result for a counterbalanced strategy tournament."""

    players_count: int
    strategy_names: list[str]
    games_per_lineup: int
    base_seed: int
    lineups_tested: int
    total_games: int
    lineup_results: list[StrategyTournamentLineupResult] = field(default_factory=list)
    aggregate_stats: dict = field(default_factory=dict)


class StrategyTournamentRunner:
    """Run every unique strategy lineup and aggregate all games."""

    def run(
        self,
        players_count: int,
        strategy_names: list[str],
        games_per_lineup: int,
        seed: int,
        config: GameConfig | None = None,
    ) -> StrategyTournamentResult:
        """Run a counterbalanced tournament for the provided strategies."""

        config = config or get_v05_config_for_players(players_count)
        if players_count < config.min_players or players_count > config.max_players:
            raise ValueError(
                f"players_count must be between {config.min_players} and {config.max_players}"
            )
        if len(strategy_names) != players_count:
            raise ValueError("strategy_names length must match players_count")
        if games_per_lineup <= 0:
            raise ValueError("games_per_lineup must be greater than 0")

        canonical_names = [create_strategy(name).name for name in strategy_names]
        lineups = list(dict.fromkeys(permutations(canonical_names)))
        lineup_results: list[StrategyTournamentLineupResult] = []
        all_game_results = []

        for lineup_index, lineup in enumerate(lineups):
            lineup_seed = seed + lineup_index * games_per_lineup
            strategies = [create_strategy(name) for name in lineup]
            simulation_result = SimulationRunner().run(
                players_count=players_count,
                games_count=games_per_lineup,
                seed=lineup_seed,
                config=config,
                strategies=strategies,
            )
            lineup_results.append(
                StrategyTournamentLineupResult(
                    lineup_id=lineup_index + 1,
                    lineup_seed=lineup_seed,
                    strategies_by_player={
                        player_id: strategy_name
                        for player_id, strategy_name in enumerate(lineup, start=1)
                    },
                    simulation_result=simulation_result,
                    aggregate_stats=simulation_result.aggregate_stats,
                )
            )
            all_game_results.extend(simulation_result.game_results)

        aggregate_stats = StatisticAggregator().aggregate(all_game_results)
        aggregate_stats.update(
            {
                "total_games": len(all_game_results),
                "lineups_tested": len(lineups),
                "games_per_lineup": games_per_lineup,
                "appearances_by_strategy_player_id": (
                    self._count_strategy_player_appearances(
                        lineup_results,
                        canonical_names,
                        players_count,
                        games_per_lineup,
                    )
                ),
            }
        )

        return StrategyTournamentResult(
            players_count=players_count,
            strategy_names=canonical_names,
            games_per_lineup=games_per_lineup,
            base_seed=seed,
            lineups_tested=len(lineups),
            total_games=len(all_game_results),
            lineup_results=lineup_results,
            aggregate_stats=aggregate_stats,
        )

    def _count_strategy_player_appearances(
        self,
        lineup_results: list[StrategyTournamentLineupResult],
        strategy_names: list[str],
        players_count: int,
        games_per_lineup: int,
    ) -> dict[str, dict[int, int]]:
        """Count game appearances per strategy and player position."""

        appearances = {
            strategy_name: {
                player_id: 0
                for player_id in range(1, players_count + 1)
            }
            for strategy_name in sorted(set(strategy_names))
        }

        for lineup_result in lineup_results:
            for player_id, strategy_name in lineup_result.strategies_by_player.items():
                appearances[strategy_name][player_id] += games_per_lineup

        return appearances
