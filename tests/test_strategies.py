import subprocess
import sys
from pathlib import Path
from random import Random


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.simulation import SimulationRunner
from sotto_soglia.strategies import (
    AVAILABLE_STRATEGIES,
    AdaptivePressureStrategy,
    AggressiveStrategy,
    AntiCriticalStrategy,
    DefensiveStrategy,
    MixedStrategy,
    PrudentStrategy,
    V05BalancedStrategy,
    V05BasicStrategy,
    create_strategy,
)
from sotto_soglia.tournament import StrategyTournamentRunner


def _game_state(*players):
    return {"players": list(players)}


def _v05_game_state(*players, config=None):
    return {
        "players": list(players),
        "config": config or get_v05_config_for_players(len(players)),
    }


def test_create_strategy_builds_all_available_strategies():
    for strategy_name in [
        "random",
        "prudent",
        "defensive",
        "aggressive",
        "anti_critical",
        "mixed",
        "v05_basic",
        "v05_balanced",
        "adaptive_pressure",
    ]:
        strategy = create_strategy(strategy_name)

        assert strategy.name == strategy_name
        assert strategy_name in AVAILABLE_STRATEGIES


def test_create_strategy_rejects_unknown_strategy():
    try:
        create_strategy("unknown")
    except ValueError:
        return

    assert False, "Expected ValueError for unknown strategy"


def test_prudent_strategy_chooses_lowest_value():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    hand = [
        Card(Color.RED, 5),
        Card(Color.GREEN, 2),
        Card(Color.YELLOW, 4),
    ]

    selected = PrudentStrategy().choose_card(player, hand, None, Random(1))

    assert selected == Card(Color.GREEN, 2)


def test_defensive_strategy_prefers_own_color():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 4),
        Card(Color.GREEN, 2),
    ]

    selected = DefensiveStrategy().choose_card(player, hand, None, Random(1))

    assert selected == Card(Color.BLUE, 4)


def test_aggressive_strategy_prefers_alive_opponent_color():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.BLUE, 1),
        Card(Color.GREEN, 2),
        Card(Color.RED, 4),
    ]

    selected = AggressiveStrategy().choose_card(
        player,
        hand,
        _game_state(player, opponent),
        Random(1),
    )

    assert selected == Card(Color.RED, 4)


def test_anti_critical_strategy_avoids_lowest_value_when_possible():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    selected = AntiCriticalStrategy().choose_card(player, hand, None, Random(1))

    assert selected.value != 1


def test_mixed_strategy_returns_card_from_hand():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    selected = MixedStrategy().choose_card(
        player,
        hand,
        _game_state(player, opponent),
        Random(1),
    )

    assert selected in hand


def test_create_strategy_builds_v05_basic_strategy():
    strategy = create_strategy("v05_basic")

    assert isinstance(strategy, V05BasicStrategy)
    assert "v05_basic" in AVAILABLE_STRATEGIES


def test_v05_basic_strategy_returns_card_from_hand():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    selected = V05BasicStrategy().choose_card(
        player,
        hand,
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected in hand


def test_v05_basic_uses_effective_comparison_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    scatto = Card(Color.RED, 1)
    printed_one = Card(Color.BLUE, 1)
    hand = [printed_one, scatto]

    selected = V05BasicStrategy().choose_card(
        player,
        hand,
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == scatto


def test_v05_basic_uses_effective_consumption_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    passo_leggero = Card(Color.RED, 2)
    printed_two = Card(Color.BLUE, 2)
    hand = [printed_two, passo_leggero]

    selected = V05BasicStrategy().choose_card(
        player,
        hand,
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == passo_leggero


def test_v05_basic_avoids_lethal_consumption_when_possible():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=2)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    lethal = Card(Color.GREEN, 3)
    survivable = Card(Color.RED, 1)

    selected = V05BasicStrategy().choose_card(
        player,
        [lethal, survivable],
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected == survivable


def test_v05_basic_penalizes_affamato_risk_near_limit():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    risky = Card(Color.RED, 1)
    safer = Card(Color.GREEN, 3)

    selected = V05BasicStrategy().choose_card(
        player,
        [risky, safer],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == safer


def test_v05_basic_tie_break_is_deterministic():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.YELLOW, 3),
        Card(Color.GREEN, 3),
    ]
    strategy = V05BasicStrategy()

    selected_cards = [
        strategy.choose_card(
            player,
            hand,
            _v05_game_state(player, opponent),
            Random(seed),
        )
        for seed in range(5)
    ]

    assert selected_cards == [Card(Color.GREEN, 3)] * 5


def test_simulation_runner_smoke_with_v05_basic_strategy():
    result = SimulationRunner().run(
        players_count=4,
        games_count=3,
        seed=42,
        strategies=create_strategy("v05_basic"),
    )

    assert len(result.game_results) == 3
    assert {
        player.strategy_name
        for player in result.game_results[0].final_players
    } == {"v05_basic"}


def test_tournament_runner_accepts_v05_basic_strategy():
    result = StrategyTournamentRunner().run(
        players_count=2,
        strategy_names=["v05_basic", "random"],
        games_per_lineup=1,
        seed=42,
    )

    assert result.lineups_tested == 2
    assert "v05_basic" in result.aggregate_stats["win_rate_by_strategy"]


def test_cli_accepts_v05_basic_strategy():
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "5",
            "--seed",
            "42",
            "--strategy",
            "v05_basic",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Win rate by strategy:" in result.stdout
    assert "- v05_basic:" in result.stdout


def test_create_strategy_builds_v05_balanced_strategy():
    strategy = create_strategy("v05_balanced")

    assert isinstance(strategy, V05BalancedStrategy)
    assert "v05_balanced" in AVAILABLE_STRATEGIES


def test_v05_balanced_strategy_returns_card_from_hand():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    selected = V05BalancedStrategy().choose_card(
        player,
        hand,
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected in hand


def test_v05_balanced_uses_effective_comparison_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    scatto = Card(Color.RED, 1)
    printed_one = Card(Color.BLUE, 1)

    selected = V05BalancedStrategy().choose_card(
        player,
        [printed_one, scatto],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == scatto


def test_v05_balanced_uses_effective_consumption_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    passo_leggero = Card(Color.RED, 2)
    printed_two = Card(Color.BLUE, 2)

    selected = V05BalancedStrategy().choose_card(
        player,
        [printed_two, passo_leggero],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == passo_leggero


def test_v05_balanced_avoids_lethal_consumption_when_possible():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=2)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    lethal = Card(Color.GREEN, 3)
    survivable = Card(Color.RED, 1)

    selected = V05BalancedStrategy().choose_card(
        player,
        [lethal, survivable],
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected == survivable


def test_v05_balanced_is_more_scorte_prudent_than_v05_basic():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=8)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    high_comparison_expensive = Card(Color.GREEN, 5)
    medium_comparison_cheap = Card(Color.RED, 2)
    hand = [high_comparison_expensive, medium_comparison_cheap]
    game_state = _v05_game_state(player, opponent)

    basic_selected = V05BasicStrategy().choose_card(
        player,
        hand,
        game_state,
        Random(1),
    )
    balanced_selected = V05BalancedStrategy().choose_card(
        player,
        hand,
        game_state,
        Random(1),
    )

    assert basic_selected == high_comparison_expensive
    assert balanced_selected == medium_comparison_cheap


def test_v05_balanced_penalizes_affamato_risk_near_limit():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    risky = Card(Color.RED, 1)
    safer = Card(Color.GREEN, 3)

    selected = V05BalancedStrategy().choose_card(
        player,
        [risky, safer],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == safer


def test_v05_balanced_tie_break_is_deterministic():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.YELLOW, 3),
        Card(Color.GREEN, 3),
    ]
    strategy = V05BalancedStrategy()

    selected_cards = [
        strategy.choose_card(
            player,
            hand,
            _v05_game_state(player, opponent),
            Random(seed),
        )
        for seed in range(5)
    ]

    assert selected_cards == [Card(Color.GREEN, 3)] * 5


def test_simulation_runner_smoke_with_v05_balanced_strategy():
    result = SimulationRunner().run(
        players_count=4,
        games_count=3,
        seed=42,
        strategies=create_strategy("v05_balanced"),
    )

    assert len(result.game_results) == 3
    assert {
        player.strategy_name
        for player in result.game_results[0].final_players
    } == {"v05_balanced"}


def test_tournament_runner_accepts_v05_balanced_strategy():
    result = StrategyTournamentRunner().run(
        players_count=2,
        strategy_names=["v05_balanced", "random"],
        games_per_lineup=1,
        seed=42,
    )

    assert result.lineups_tested == 2
    assert "v05_balanced" in result.aggregate_stats["win_rate_by_strategy"]


def test_cli_accepts_v05_balanced_strategy():
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "5",
            "--seed",
            "42",
            "--strategy",
            "v05_balanced",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Win rate by strategy:" in result.stdout
    assert "- v05_balanced:" in result.stdout


def test_create_strategy_builds_adaptive_pressure_strategy():
    strategy = create_strategy("adaptive_pressure")

    assert isinstance(strategy, AdaptivePressureStrategy)


def test_adaptive_pressure_strategy_returns_card_from_hand():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    selected = AdaptivePressureStrategy().choose_card(
        player,
        hand,
        _game_state(player, opponent),
        Random(1),
    )

    assert selected in hand


def test_adaptive_pressure_avoids_low_cards_with_two_critical_wounds():
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=18,
        critical_wounds=2,
    )
    hand = [
        Card(Color.RED, 1),
        Card(Color.GREEN, 2),
        Card(Color.YELLOW, 4),
    ]

    selected = AdaptivePressureStrategy().choose_card(player, hand, None, Random(1))

    assert selected == Card(Color.YELLOW, 4)


def test_adaptive_pressure_can_choose_low_card_when_lives_are_low():
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=3,
        critical_wounds=1,
    )
    hand = [
        Card(Color.RED, 1),
        Card(Color.GREEN, 5),
    ]

    selected = AdaptivePressureStrategy().choose_card(player, hand, None, Random(1))

    assert selected == Card(Color.RED, 1)


def test_adaptive_pressure_targets_vulnerable_opponent_color():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    vulnerable_opponent = PlayerState(player_id=2, color=Color.RED, lives=3)
    healthy_opponent = PlayerState(player_id=3, color=Color.GREEN, lives=18)
    hand = [
        Card(Color.GREEN, 3),
        Card(Color.RED, 3),
        Card(Color.YELLOW, 4),
    ]

    selected = AdaptivePressureStrategy().choose_card(
        player,
        hand,
        _game_state(player, vulnerable_opponent, healthy_opponent),
        Random(1),
    )

    assert selected == Card(Color.RED, 3)


def test_adaptive_pressure_values_own_color_when_lives_are_low():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=3)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.RED, 2),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 4),
    ]

    selected = AdaptivePressureStrategy().choose_card(
        player,
        hand,
        _game_state(player, opponent),
        Random(1),
    )

    assert selected == Card(Color.BLUE, 3)


def test_cli_accepts_adaptive_pressure_strategy():
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "5",
            "--seed",
            "42",
            "--strategy",
            "adaptive_pressure",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Win rate by strategy:" in result.stdout
    assert "- adaptive_pressure:" in result.stdout


def test_cli_accepts_adaptive_pressure_in_strategy_list():
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "5",
            "--seed",
            "42",
            "--strategies",
            "adaptive_pressure",
            "random",
            "defensive",
            "aggressive",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Win rate by strategy:" in result.stdout
    assert "- adaptive_pressure:" in result.stdout
