from pathlib import Path
from random import Random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.strategies import (
    AVAILABLE_STRATEGIES,
    AggressiveStrategy,
    AntiCriticalStrategy,
    DefensiveStrategy,
    MixedStrategy,
    PrudentStrategy,
    create_strategy,
)


def _game_state(*players):
    return {"players": list(players)}


def test_create_strategy_builds_all_available_strategies():
    for strategy_name in [
        "random",
        "prudent",
        "defensive",
        "aggressive",
        "anti_critical",
        "mixed",
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
