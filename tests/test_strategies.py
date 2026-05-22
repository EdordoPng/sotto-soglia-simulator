import subprocess
import sys
from pathlib import Path
from random import Random


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.animal_effects import CONIGLIO_GRANDE_BALZO_DEBT
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
    V05AnimalAwareStrategy,
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


def _candidate_card_tuple(candidate):
    return (
        candidate.candidate_card_color,
        candidate.candidate_card_value,
    )


def _card_tuple(card):
    return (
        card.color.name,
        card.value,
    )


def _candidate_by_card(candidates, card):
    return next(
        candidate
        for candidate in candidates
        if _candidate_card_tuple(candidate) == _card_tuple(card)
    )


def _assert_single_chosen_with_consecutive_ranks(candidates):
    chosen = [candidate for candidate in candidates if candidate.chosen]

    assert len(chosen) == 1
    assert chosen[0].choice_rank == 1
    assert sorted(candidate.choice_rank for candidate in candidates) == list(
        range(1, len(candidates) + 1)
    )


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
        "v05_animal_aware",
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


def test_v05_basic_evaluate_candidates_returns_one_candidate_per_card():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    candidates = V05BasicStrategy().evaluate_candidates(
        player,
        hand,
        _v05_game_state(player, opponent),
    )

    assert len(candidates) == len(hand)
    assert {_candidate_card_tuple(candidate) for candidate in candidates} == {
        _card_tuple(card)
        for card in hand
    }
    _assert_single_chosen_with_consecutive_ranks(candidates)


def test_v05_basic_evaluate_candidates_chosen_matches_choose_card():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]
    strategy = V05BasicStrategy()

    selected = strategy.choose_card(player, hand, _v05_game_state(player, opponent), Random(1))
    candidates = strategy.evaluate_candidates(player, hand, _v05_game_state(player, opponent))
    chosen = next(candidate for candidate in candidates if candidate.chosen)

    assert _candidate_card_tuple(chosen) == _card_tuple(selected)


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


def test_v05_basic_candidate_uses_effective_comparison_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)

    candidates = V05BasicStrategy().evaluate_candidates(
        player,
        [Card(Color.RED, 1), Card(Color.BLUE, 1)],
        _v05_game_state(player, opponent, config=config),
    )
    by_card = {
        _candidate_card_tuple(candidate): candidate
        for candidate in candidates
    }

    assert by_card[("RED", 1)].effective_comparison == 2


def test_v05_basic_uses_pre_reveal_coniglio_two_consumption_value():
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

    assert selected in hand


def test_v05_basic_candidate_uses_effective_consumption_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)

    candidates = V05BasicStrategy().evaluate_candidates(
        player,
        [Card(Color.RED, 2), Card(Color.BLUE, 2)],
        _v05_game_state(player, opponent, config=config),
    )
    by_card = {
        _candidate_card_tuple(candidate): candidate
        for candidate in candidates
    }

    assert by_card[("RED", 2)].effective_consumption == 2


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


def test_v05_balanced_evaluate_candidates_returns_one_candidate_per_card():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    candidates = V05BalancedStrategy().evaluate_candidates(
        player,
        hand,
        _v05_game_state(player, opponent),
    )

    assert len(candidates) == len(hand)
    assert {_candidate_card_tuple(candidate) for candidate in candidates} == {
        _card_tuple(card)
        for card in hand
    }
    _assert_single_chosen_with_consecutive_ranks(candidates)


def test_v05_balanced_evaluate_candidates_chosen_matches_choose_card():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]
    strategy = V05BalancedStrategy()

    selected = strategy.choose_card(player, hand, _v05_game_state(player, opponent), Random(1))
    candidates = strategy.evaluate_candidates(player, hand, _v05_game_state(player, opponent))
    chosen = next(candidate for candidate in candidates if candidate.chosen)

    assert _candidate_card_tuple(chosen) == _card_tuple(selected)


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


def test_v05_balanced_candidate_uses_effective_comparison_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)

    candidates = V05BalancedStrategy().evaluate_candidates(
        player,
        [Card(Color.RED, 1), Card(Color.BLUE, 1)],
        _v05_game_state(player, opponent, config=config),
    )
    by_card = {
        _candidate_card_tuple(candidate): candidate
        for candidate in candidates
    }

    assert by_card[("RED", 1)].effective_comparison == 2


def test_v05_balanced_uses_pre_reveal_coniglio_two_consumption_value():
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

    assert selected in [printed_two, passo_leggero]


def test_v05_balanced_candidate_uses_effective_consumption_value():
    config = GameConfig(
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)

    candidates = V05BalancedStrategy().evaluate_candidates(
        player,
        [Card(Color.RED, 2), Card(Color.BLUE, 2)],
        _v05_game_state(player, opponent, config=config),
    )
    by_card = {
        _candidate_card_tuple(candidate): candidate
        for candidate in candidates
    }

    assert by_card[("RED", 2)].effective_consumption == 2


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


def test_v05_balanced_is_not_too_passive_on_affamato_near_limit():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=8,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    low_consumption_risky = Card(Color.RED, 1)
    sustainable_safer = Card(Color.GREEN, 4)

    selected = V05BalancedStrategy().choose_card(
        player,
        [low_consumption_risky, sustainable_safer],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == sustainable_safer


def test_v05_candidate_display_colors_and_animals_are_correct():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.BLUE, 2),
        Card(Color.RED, 2),
        Card(Color.GREEN, 2),
        Card(Color.YELLOW, 2),
    ]

    candidates = V05BalancedStrategy().evaluate_candidates(
        player,
        hand,
        _v05_game_state(player, opponent),
    )
    by_color = {
        candidate.candidate_card_color: candidate
        for candidate in candidates
    }

    assert by_color["BLUE"].candidate_card_display_color == "green"
    assert by_color["BLUE"].candidate_card_animal == "Panda"
    assert by_color["RED"].candidate_card_display_color == "orange"
    assert by_color["RED"].candidate_card_animal == "Coniglio"
    assert by_color["GREEN"].candidate_card_display_color == "yellow"
    assert by_color["GREEN"].candidate_card_animal == "Scimmia"
    assert by_color["YELLOW"].candidate_card_display_color == "brown"
    assert by_color["YELLOW"].candidate_card_animal == "Scoiattolo"


def test_v05_candidate_reason_flags_include_clear_audit_flags():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=2,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.GREEN, 3),
    ]

    candidates = V05BalancedStrategy().evaluate_candidates(
        player,
        hand,
        _v05_game_state(player, opponent, config=config),
    )
    by_card = {
        _candidate_card_tuple(candidate): candidate
        for candidate in candidates
    }

    low_card_flags = set(by_card[("RED", 1)].reason_flags)
    lethal_card_flags = set(by_card[("GREEN", 3)].reason_flags)
    assert "lowest_comparison" in low_card_flags
    assert "near_abandonment" in low_card_flags
    assert "remaining_lives_1" in low_card_flags
    assert "low_consumption" in low_card_flags
    assert "lethal_consumption" in lethal_card_flags
    assert "near_abandonment" in lethal_card_flags


def test_v05_candidate_scores_are_deterministic():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.YELLOW, 3),
        Card(Color.GREEN, 3),
    ]
    strategy = V05BalancedStrategy()
    game_state = _v05_game_state(player, opponent)

    first = strategy.evaluate_candidates(player, hand, game_state)
    second = strategy.evaluate_candidates(player, hand, game_state)

    assert [
        (
            candidate.candidate_card_color,
            candidate.candidate_card_value,
            candidate.score,
            candidate.choice_rank,
            candidate.chosen,
        )
        for candidate in first
    ] == [
        (
            candidate.candidate_card_color,
            candidate.candidate_card_value,
            candidate.score,
            candidate.choice_rank,
            candidate.chosen,
        )
        for candidate in second
    ]


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


def test_legacy_strategies_keep_default_empty_candidate_evaluation():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
    ]

    for strategy_name in [
        "random",
        "prudent",
        "defensive",
        "aggressive",
        "anti_critical",
        "mixed",
        "adaptive_pressure",
        "critical_adaptive",
    ]:
        strategy = create_strategy(strategy_name)

        assert strategy.evaluate_candidates(player, hand, None) == []


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


def test_create_strategy_builds_v05_animal_aware_strategy():
    strategy = create_strategy("v05_animal_aware")

    assert isinstance(strategy, V05AnimalAwareStrategy)
    assert "v05_animal_aware" in AVAILABLE_STRATEGIES


def test_v05_animal_aware_strategy_returns_card_from_hand():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=18)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        hand,
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected in hand


def test_v05_animal_aware_evaluate_candidates_returns_one_candidate_per_card():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]

    candidates = V05AnimalAwareStrategy().evaluate_candidates(
        player,
        hand,
        _v05_game_state(player, opponent),
    )

    assert len(candidates) == len(hand)
    assert {_candidate_card_tuple(candidate) for candidate in candidates} == {
        _card_tuple(card)
        for card in hand
    }
    _assert_single_chosen_with_consecutive_ranks(candidates)


def test_v05_animal_aware_evaluate_candidates_chosen_matches_choose_card():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.RED, 1),
        Card(Color.BLUE, 3),
        Card(Color.GREEN, 5),
    ]
    strategy = V05AnimalAwareStrategy()
    game_state = _v05_game_state(player, opponent)

    selected = strategy.choose_card(player, hand, game_state, Random(1))
    candidates = strategy.evaluate_candidates(player, hand, game_state)
    chosen = next(candidate for candidate in candidates if candidate.chosen)

    assert _candidate_card_tuple(chosen) == _card_tuple(selected)


def test_v05_animal_aware_scores_are_deterministic():
    player = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.YELLOW, 3),
        Card(Color.GREEN, 3),
        Card(Color.BLUE, 3),
    ]
    strategy = V05AnimalAwareStrategy()
    game_state = _v05_game_state(player, opponent)

    first = strategy.evaluate_candidates(player, hand, game_state)
    second = strategy.evaluate_candidates(player, hand, game_state)

    assert [
        (
            candidate.candidate_card_color,
            candidate.candidate_card_value,
            candidate.score,
            candidate.choice_rank,
            candidate.chosen,
        )
        for candidate in first
    ] == [
        (
            candidate.candidate_card_color,
            candidate.candidate_card_value,
            candidate.score,
            candidate.choice_rank,
            candidate.chosen,
        )
        for candidate in second
    ]


def test_v05_animal_aware_prefers_own_card_when_base_scores_are_close():
    player = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    hand = [
        Card(Color.YELLOW, 3),
        Card(Color.GREEN, 3),
    ]
    game_state = _v05_game_state(player, opponent)

    balanced_selected = V05BalancedStrategy().choose_card(
        player,
        hand,
        game_state,
        Random(1),
    )
    animal_aware_selected = V05AnimalAwareStrategy().choose_card(
        player,
        hand,
        game_state,
        Random(1),
    )

    assert balanced_selected == Card(Color.GREEN, 3)
    assert animal_aware_selected == Card(Color.YELLOW, 3)


def test_v05_animal_aware_keeps_only_own_bonus_for_coniglio_red_2_without_risk_pressure():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    red_2 = Card(Color.RED, 2)
    hand = [red_2, Card(Color.GREEN, 4)]
    game_state = _v05_game_state(player, opponent)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        red_2,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        red_2,
    )

    assert animal_aware.score - balanced.score == 1.0


def test_v05_animal_aware_has_no_special_coniglio_red_1_near_abandonment_bonus():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.RED,
        lives=12,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    red_1 = Card(Color.RED, 1)
    hand = [red_1, Card(Color.BLUE, 3)]
    game_state = _v05_game_state(player, opponent, config=config)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        red_1,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        red_1,
    )

    assert round(animal_aware.score - balanced.score, 6) == -1.6
    assert "near_abandonment" in animal_aware.reason_flags


def test_v05_animal_aware_has_no_special_coniglio_red_4_near_abandonment_bonus():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.RED,
        lives=12,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    red_4 = Card(Color.RED, 4)
    hand = [red_4, Card(Color.BLUE, 3, custom_consumption_value=2)]
    game_state = _v05_game_state(player, opponent, config=config)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        red_4,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        red_4,
    )

    assert animal_aware.choice_rank == 1
    assert animal_aware.score > balanced.score
    assert animal_aware.score - balanced.score == 2.0
    assert "near_abandonment" in animal_aware.reason_flags


def test_v05_animal_aware_near_abandonment_red_2_has_no_old_special_bonus():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.RED,
        lives=12,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    red_2 = Card(Color.RED, 2)
    hand = [red_2, Card(Color.BLUE, 3, custom_consumption_value=2)]
    game_state = _v05_game_state(player, opponent, config=config)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        red_2,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        red_2,
    )

    assert round(animal_aware.score - balanced.score, 6) == -1.6


def test_v05_animal_aware_non_panda_blue_3_has_no_special_penalty():
    player = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    blue_3 = Card(Color.BLUE, 3, custom_consumption_value=2)
    hand = [blue_3, Card(Color.GREEN, 4)]
    game_state = _v05_game_state(player, opponent)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        blue_3,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        blue_3,
    )

    assert animal_aware.score == balanced.score


def test_v05_animal_aware_with_grande_balzo_debt_prefers_low_consumption_card():
    player = PlayerState(
        player_id=1,
        color=Color.RED,
        lives=12,
        active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
    )
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    low_consumption = Card(Color.RED, 1)
    high_consumption = Card(Color.RED, 4)
    game_state = _v05_game_state(player, opponent)

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        [high_consumption, low_consumption],
        game_state,
        Random(1),
    )
    candidates = V05AnimalAwareStrategy().evaluate_candidates(
        player,
        [high_consumption, low_consumption],
        game_state,
    )

    assert selected == low_consumption
    low_candidate = _candidate_by_card(candidates, low_consumption)
    high_candidate = _candidate_by_card(candidates, high_consumption)
    assert low_candidate.effective_consumption == 3
    assert high_candidate.effective_consumption == 12
    assert low_candidate.chosen is True
    assert high_candidate.chosen is False


def test_v05_basic_and_balanced_do_not_apply_grande_balzo_debt_strategy_consumption():
    player = PlayerState(
        player_id=1,
        color=Color.RED,
        lives=12,
        active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
    )
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    red_4 = Card(Color.RED, 4)
    game_state = _v05_game_state(player, opponent)

    basic = _candidate_by_card(
        V05BasicStrategy().evaluate_candidates(player, [red_4], game_state),
        red_4,
    )
    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, [red_4], game_state),
        red_4,
    )

    assert basic.effective_consumption == 4
    assert balanced.effective_consumption == 4


def test_v05_animal_aware_panda_can_still_choose_blue_3_when_sensible():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    blue_3 = Card(Color.BLUE, 3)
    low_non_own = Card(Color.RED, 2)

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        [blue_3, low_non_own],
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected == blue_3


def test_v05_animal_aware_scimmia_own_card_bonus_is_one():
    player = PlayerState(player_id=1, color=Color.GREEN, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    own_card = Card(Color.GREEN, 3)
    hand = [own_card, Card(Color.YELLOW, 3)]
    game_state = _v05_game_state(player, opponent)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        own_card,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        own_card,
    )

    assert animal_aware.score - balanced.score == 1.0


def test_v05_animal_aware_scimmia_bonus_does_not_override_clear_safety():
    player = PlayerState(player_id=1, color=Color.GREEN, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    expensive_own = Card(Color.GREEN, 5)
    safer_non_own = Card(Color.BLUE, 3, custom_consumption_value=2)

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        [expensive_own, safer_non_own],
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected == safer_non_own


def test_v05_animal_aware_scoiattolo_preparation_bonus_does_not_override_lethal_risk():
    player = PlayerState(player_id=1, color=Color.YELLOW, lives=4)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    lethal_preparation = Card(Color.YELLOW, 4)
    survivable = Card(Color.RED, 1)

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        [lethal_preparation, survivable],
        _v05_game_state(player, opponent),
        Random(1),
    )

    assert selected == survivable


def test_v05_animal_aware_scoiattolo_preparation_keeps_only_own_card_bonus():
    player = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    opponent = PlayerState(player_id=2, color=Color.RED, lives=12)
    preparation = Card(Color.YELLOW, 3)
    hand = [preparation, Card(Color.GREEN, 3)]
    game_state = _v05_game_state(player, opponent)

    balanced = _candidate_by_card(
        V05BalancedStrategy().evaluate_candidates(player, hand, game_state),
        preparation,
    )
    animal_aware = _candidate_by_card(
        V05AnimalAwareStrategy().evaluate_candidates(player, hand, game_state),
        preparation,
    )

    assert animal_aware.score - balanced.score == 1.0
    assert animal_aware.chosen


def test_v05_animal_aware_near_affamato_prefers_safer_comparison_when_consumption_survives():
    config = get_v05_config_for_players(2)
    player = PlayerState(
        player_id=1,
        color=Color.RED,
        lives=10,
        critical_wounds=config.critical_wounds_limit - 1,
    )
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    low_consumption_risky = Card(Color.RED, 2)
    safer_comparison = Card(Color.GREEN, 4)

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        [low_consumption_risky, safer_comparison],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == safer_comparison


def test_v05_animal_aware_low_scorte_prefers_avoiding_near_lethal_consumption():
    config = get_v05_config_for_players(2)
    player = PlayerState(player_id=1, color=Color.RED, lives=5)
    opponent = PlayerState(player_id=2, color=Color.BLUE, lives=12)
    costly_safe_comparison = Card(Color.GREEN, 4)
    cheap_risky_comparison = Card(Color.RED, 2)

    selected = V05AnimalAwareStrategy().choose_card(
        player,
        [costly_safe_comparison, cheap_risky_comparison],
        _v05_game_state(player, opponent, config=config),
        Random(1),
    )

    assert selected == cheap_risky_comparison


def test_simulation_runner_smoke_with_v05_animal_aware_strategy():
    result = SimulationRunner().run(
        players_count=4,
        games_count=3,
        seed=42,
        strategies=create_strategy("v05_animal_aware"),
    )

    assert len(result.game_results) == 3
    assert {
        player.strategy_name
        for player in result.game_results[0].final_players
    } == {"v05_animal_aware"}


def test_tournament_runner_accepts_v05_animal_aware_strategy():
    result = StrategyTournamentRunner().run(
        players_count=2,
        strategy_names=["v05_animal_aware", "random"],
        games_per_lineup=1,
        seed=42,
    )

    assert result.lineups_tested == 2
    assert "v05_animal_aware" in result.aggregate_stats["win_rate_by_strategy"]


def test_cli_accepts_v05_animal_aware_strategy():
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
            "v05_animal_aware",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Win rate by strategy:" in result.stdout
    assert "- v05_animal_aware:" in result.stdout


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
