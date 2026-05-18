"""Simulation runner for repeated Sotto Soglia games."""

from dataclasses import dataclass, field

from sotto_soglia.config import GameConfig
from sotto_soglia.game import GameResult, play_game
from sotto_soglia.statistics import StatisticAggregator


@dataclass
class SimulationResult:
    """Results and aggregate statistics for a simulation batch."""

    players_count: int
    games_count: int
    base_seed: int
    game_results: list[GameResult] = field(default_factory=list)
    aggregate_stats: dict = field(default_factory=dict)


class SimulationRunner:
    """Run repeated games and aggregate base statistics."""

    def run(
        self,
        players_count: int,
        games_count: int,
        seed: int = 0,
        config: GameConfig | None = None,
    ) -> SimulationResult:
        """Run many games using incrementing deterministic seeds."""

        config = config or GameConfig()
        if players_count < config.min_players or players_count > config.max_players:
            raise ValueError(
                f"players_count must be between {config.min_players} and {config.max_players}"
            )
        if games_count <= 0:
            raise ValueError("games_count must be greater than 0")

        game_results = [
            play_game(
                game_id=game_index + 1,
                players_count=players_count,
                seed=seed + game_index,
                config=config,
            )
            for game_index in range(games_count)
        ]
        aggregate_stats = StatisticAggregator().aggregate(game_results)

        return SimulationResult(
            players_count=players_count,
            games_count=games_count,
            base_seed=seed,
            game_results=game_results,
            aggregate_stats=aggregate_stats,
        )
