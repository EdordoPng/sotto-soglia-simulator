"""Simulation runner for repeated Sotto Soglia games."""

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.game import GameResult, play_game
from sotto_soglia.statistics import StatisticAggregator
from sotto_soglia.strategies import BaseStrategy


@dataclass
class SimulationResult:
    """Results and aggregate statistics for a simulation batch."""

    players_count: int
    games_count: int
    base_seed: int
    game_results: list[GameResult] = field(default_factory=list)
    aggregate_stats: dict = field(default_factory=dict)
    initial_lives: int = 18
    critical_wounds_limit: int = 3
    color_effects_enabled: bool = True
    critical_card_effects_enabled: bool = False
    animal_card_effects_enabled: bool = False
    critical_deck_profile_id: str = "legacy"
    critical_deck_seed: int | None = None
    critical_deck_order: tuple[str, ...] | None = None
    sono_ancora_qui_variant: str = "single_2"


class SimulationRunner:
    """Run repeated games and aggregate base statistics."""

    def run(
        self,
        players_count: int,
        games_count: int,
        seed: int = 0,
        config: GameConfig | None = None,
        strategies: (
            BaseStrategy | Sequence[BaseStrategy] | Mapping[int, BaseStrategy] | None
        ) = None,
    ) -> SimulationResult:
        """Run many games using incrementing deterministic seeds."""

        config = config or get_v05_config_for_players(players_count)
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
                strategies=strategies,
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
            initial_lives=config.initial_lives,
            critical_wounds_limit=config.critical_wounds_limit,
            color_effects_enabled=config.color_effects_enabled,
            critical_card_effects_enabled=config.critical_card_effects_enabled,
            animal_card_effects_enabled=config.animal_card_effects_enabled,
            critical_deck_profile_id=config.critical_deck_profile_id,
            critical_deck_seed=config.critical_deck_seed,
            critical_deck_order=config.critical_deck_order,
            sono_ancora_qui_variant=config.sono_ancora_qui_variant,
        )
