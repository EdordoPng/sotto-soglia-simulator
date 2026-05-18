"""Parametric simulation runner for balance testing."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from sotto_soglia.config import GameConfig
from sotto_soglia.simulation import SimulationResult, SimulationRunner
from sotto_soglia.strategies import BaseStrategy, create_strategy


BASELINE_CONFIG = {
    "initial_lives": 18,
    "critical_wounds_limit": 3,
    "color_effects_enabled": True,
}


@dataclass
class ParametricConfigResult:
    """Results for one tested rules configuration."""

    config_id: int
    seed: int
    initial_lives: int
    critical_wounds_limit: int
    color_effects_enabled: bool
    simulation_result: SimulationResult
    aggregate_stats: dict
    is_baseline: bool = False


@dataclass
class ParametricSimulationResult:
    """Results for a complete parametric simulation batch."""

    players_count: int
    games_per_config: int
    base_seed: int
    tested_configs: int
    total_games: int
    config_results: list[ParametricConfigResult] = field(default_factory=list)
    baseline_config: dict = field(default_factory=lambda: dict(BASELINE_CONFIG))


class ParametricSimulationRunner:
    """Run simulations across a grid of rules configurations."""

    def run(
        self,
        players_count: int,
        games_per_config: int,
        seed: int,
        initial_lives_values: list[int],
        critical_wounds_values: list[int],
        color_effects_values: list[bool],
        strategy_names: str | Sequence[str] | None = None,
    ) -> ParametricSimulationResult:
        """Run one simulation batch per configuration."""

        if games_per_config <= 0:
            raise ValueError("games_per_config must be greater than 0")
        if not initial_lives_values:
            raise ValueError("initial_lives_values must not be empty")
        if not critical_wounds_values:
            raise ValueError("critical_wounds_values must not be empty")
        if not color_effects_values:
            raise ValueError("color_effects_values must not be empty")

        config_results: list[ParametricConfigResult] = []
        simulation_runner = SimulationRunner()

        for config_index, config in enumerate(
            self._build_configs(
                initial_lives_values,
                critical_wounds_values,
                color_effects_values,
            )
        ):
            config_seed = seed + config_index * games_per_config
            strategies = self._create_strategies(strategy_names)
            simulation_result = simulation_runner.run(
                players_count=players_count,
                games_count=games_per_config,
                seed=config_seed,
                config=config,
                strategies=strategies,
            )
            config_results.append(
                ParametricConfigResult(
                    config_id=config_index + 1,
                    seed=config_seed,
                    initial_lives=config.initial_lives,
                    critical_wounds_limit=config.critical_wounds_limit,
                    color_effects_enabled=config.color_effects_enabled,
                    simulation_result=simulation_result,
                    aggregate_stats=simulation_result.aggregate_stats,
                    is_baseline=self._is_baseline(config),
                )
            )

        tested_configs = len(config_results)
        return ParametricSimulationResult(
            players_count=players_count,
            games_per_config=games_per_config,
            base_seed=seed,
            tested_configs=tested_configs,
            total_games=tested_configs * games_per_config,
            config_results=config_results,
        )

    def _build_configs(
        self,
        initial_lives_values: Sequence[int],
        critical_wounds_values: Sequence[int],
        color_effects_values: Sequence[bool],
    ) -> list[GameConfig]:
        """Build configs in a stable nested-loop order."""

        return [
            GameConfig(
                initial_lives=initial_lives,
                critical_wounds_limit=critical_wounds_limit,
                color_effects_enabled=color_effects_enabled,
            )
            for initial_lives in initial_lives_values
            for critical_wounds_limit in critical_wounds_values
            for color_effects_enabled in color_effects_values
        ]

    def _create_strategies(
        self,
        strategy_names: str | Sequence[str] | None,
    ) -> BaseStrategy | list[BaseStrategy] | None:
        """Create fresh strategy instances for a configuration."""

        if strategy_names is None:
            return None
        if isinstance(strategy_names, str):
            return create_strategy(strategy_names)
        return [create_strategy(name) for name in strategy_names]

    def _is_baseline(self, config: GameConfig) -> bool:
        """Return whether a config matches the standard baseline."""

        return (
            config.initial_lives == BASELINE_CONFIG["initial_lives"]
            and config.critical_wounds_limit == BASELINE_CONFIG["critical_wounds_limit"]
            and config.color_effects_enabled
            is BASELINE_CONFIG["color_effects_enabled"]
        )
