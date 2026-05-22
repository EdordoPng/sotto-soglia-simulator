"""Parametric simulation runner for balance testing."""

from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from sotto_soglia.config import GameConfig
from sotto_soglia.models import Color
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
    animal_card_effects_enabled: bool
    critical_card_effects_enabled: bool
    critical_deck_profile_id: str
    cards_per_player: int
    animal_lineup: tuple[Color, ...] | None
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
    animal_lineup: tuple[Color, ...] | None = None


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
        critical_card_effects_enabled: bool = False,
        critical_deck_seed: int | None = None,
        critical_deck_order: tuple[str, ...] | None = None,
        sono_ancora_qui_variant: str = "single_2",
        base_config: GameConfig | None = None,
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
                critical_card_effects_enabled,
                critical_deck_seed,
                critical_deck_order,
                sono_ancora_qui_variant,
                base_config,
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
                    animal_card_effects_enabled=config.animal_card_effects_enabled,
                    critical_card_effects_enabled=config.critical_card_effects_enabled,
                    critical_deck_profile_id=config.critical_deck_profile_id,
                    cards_per_player=config.cards_per_player,
                    animal_lineup=config.animal_lineup,
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
            animal_lineup=base_config.animal_lineup if base_config else None,
        )

    def _build_configs(
        self,
        initial_lives_values: Sequence[int],
        critical_wounds_values: Sequence[int],
        color_effects_values: Sequence[bool],
        critical_card_effects_enabled: bool = False,
        critical_deck_seed: int | None = None,
        critical_deck_order: tuple[str, ...] | None = None,
        sono_ancora_qui_variant: str = "single_2",
        base_config: GameConfig | None = None,
    ) -> list[GameConfig]:
        """Build configs in a stable nested-loop order."""

        config_template = base_config or GameConfig(
            critical_card_effects_enabled=critical_card_effects_enabled,
            critical_deck_seed=critical_deck_seed,
            critical_deck_order=critical_deck_order,
            sono_ancora_qui_variant=sono_ancora_qui_variant,
        )

        return [
            replace(
                config_template,
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
