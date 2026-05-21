from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig
from sotto_soglia.critical import V05_HUNGER_CARD_IDS
import sotto_soglia.game as game_module
from sotto_soglia.game import GameResult, play_game
from sotto_soglia.animal_effects import CONIGLIO_SCATTO_IMPROVVISO
from sotto_soglia.models import Card, Color
from sotto_soglia.round import RoundResult
from sotto_soglia.strategies import create_strategy


def _assert_valid_result(result: GameResult) -> None:
    assert result.rounds_count > 0
    assert result.winner_ids
    assert len(result.round_history) == result.rounds_count
    assert all(isinstance(round_result, RoundResult) for round_result in result.round_history)
    assert len(result.final_players) >= 2


def _assert_valid_strategy_decision_event(event, candidates_count):
    assert event.game_index == 1
    assert event.round_number >= 1
    assert event.player_id in {1, 2}
    assert event.technical_color in {"BLUE", "RED"}
    assert event.animal in {"Panda", "Coniglio"}
    assert event.display_color in {"green", "orange"}
    assert event.strategy_name in {"v05_basic", "v05_balanced"}
    assert event.lives >= 0
    assert event.critical_wounds >= 0
    assert event.critical_wounds_limit > 0
    assert event.alive_players_count == 2
    assert len(event.candidates) == candidates_count

    chosen = [candidate for candidate in event.candidates if candidate.chosen]
    assert len(chosen) == 1
    assert chosen[0].choice_rank == 1
    assert sorted(candidate.choice_rank for candidate in event.candidates) == list(
        range(1, candidates_count + 1)
    )
    for candidate in event.candidates:
        assert candidate.candidate_card_color in {"BLUE", "RED"}
        assert candidate.candidate_card_display_color in {"green", "orange"}
        assert candidate.candidate_card_animal in {"Panda", "Coniglio"}
        assert candidate.candidate_card_value in {1, 2}
        assert candidate.effective_comparison >= 1
        assert candidate.effective_consumption >= 1
        assert isinstance(candidate.score, int | float)
        assert isinstance(candidate.reason_flags, tuple)


def _controlled_two_card_hands(players, rng, config, hand_sizes_by_player=None):
    return {
        1: [Card(Color.BLUE, 1), Card(Color.RED, 2)],
        2: [Card(Color.RED, 1), Card(Color.BLUE, 2)],
    }


def test_play_game_with_two_players_returns_valid_result():
    result = play_game(game_id=1, players_count=2, seed=42)

    _assert_valid_result(result)


def test_play_game_with_three_players_returns_valid_result():
    result = play_game(game_id=1, players_count=3, seed=42)

    _assert_valid_result(result)


def test_play_game_with_four_players_returns_valid_result():
    result = play_game(game_id=1, players_count=4, seed=42)

    _assert_valid_result(result)
    assert Counter(result.initial_critical_deck_order) == {
        card_id: 3 for card_id in V05_HUNGER_CARD_IDS
    }


def test_play_game_collects_strategy_decision_events_for_v05_balanced(monkeypatch):
    monkeypatch.setattr(game_module, "_deal_hands", _controlled_two_card_hands)

    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(
            initial_lives=1,
            critical_wounds_limit=5,
            cards_per_player=2,
            color_effects_enabled=False,
            animal_card_effects_enabled=True,
            critical_card_effects_enabled=False,
        ),
        strategies=create_strategy("v05_balanced"),
    )

    assert result.strategy_decision_events
    for event in result.strategy_decision_events:
        _assert_valid_strategy_decision_event(event, candidates_count=2)


def test_play_game_collects_strategy_decision_events_for_v05_basic(monkeypatch):
    monkeypatch.setattr(game_module, "_deal_hands", _controlled_two_card_hands)

    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(
            initial_lives=1,
            critical_wounds_limit=5,
            cards_per_player=2,
            color_effects_enabled=False,
            animal_card_effects_enabled=True,
            critical_card_effects_enabled=False,
        ),
        strategies=create_strategy("v05_basic"),
    )

    assert result.strategy_decision_events
    for event in result.strategy_decision_events:
        _assert_valid_strategy_decision_event(event, candidates_count=2)


def test_play_game_has_empty_strategy_decision_events_for_random(monkeypatch):
    monkeypatch.setattr(game_module, "_deal_hands", _controlled_two_card_hands)

    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(
            initial_lives=1,
            critical_wounds_limit=5,
            cards_per_player=2,
            color_effects_enabled=False,
            animal_card_effects_enabled=True,
            critical_card_effects_enabled=False,
        ),
        strategies=create_strategy("random"),
    )

    assert result.strategy_decision_events == []


def test_play_game_rejects_too_few_players():
    try:
        play_game(players_count=1, seed=42)
    except ValueError:
        return

    assert False, "Expected ValueError for players_count < 2"


def test_play_game_rejects_too_many_players():
    try:
        play_game(players_count=5, seed=42)
    except ValueError:
        return

    assert False, "Expected ValueError for players_count > 4"


def test_play_game_raises_when_max_rounds_is_exceeded():
    try:
        play_game(players_count=2, seed=42, max_rounds=0)
    except RuntimeError:
        return

    assert False, "Expected RuntimeError when max_rounds is exceeded"


def test_round_history_and_elimination_order_are_populated():
    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(initial_lives=1),
    )

    assert result.round_history
    assert all(isinstance(round_result, RoundResult) for round_result in result.round_history)
    assert result.elimination_order


def test_play_game_aggregates_scatto_improvviso_animal_events(monkeypatch):
    def controlled_hands(players, rng, config, hand_sizes_by_player=None):
        return {
            1: [Card(Color.BLUE, 2)],
            2: [Card(Color.RED, 1)],
        }

    monkeypatch.setattr(game_module, "_deal_hands", controlled_hands)

    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(
            initial_lives=1,
            critical_wounds_limit=1,
            cards_per_player=1,
            color_effects_enabled=False,
            animal_card_effects_enabled=True,
            critical_card_effects_enabled=False,
        ),
    )

    scatto_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_SCATTO_IMPROVVISO
    ]
    assert len(scatto_events) == 1
    event = scatto_events[0]
    assert event.effect_id == CONIGLIO_SCATTO_IMPROVVISO
    assert event.effect_name == "Scatto Improvviso"
    assert event.player_id == 2
    assert event.timing == "comparison"
    assert event.status == "applied"
    assert event.value_before == 1
    assert event.value_after == 2


def test_play_game_has_empty_animal_events_without_tracked_effects(monkeypatch):
    def controlled_hands(players, rng, config, hand_sizes_by_player=None):
        return {
            1: [Card(Color.BLUE, 2)],
            2: [Card(Color.RED, 3)],
        }

    monkeypatch.setattr(game_module, "_deal_hands", controlled_hands)

    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(
            initial_lives=1,
            critical_wounds_limit=5,
            cards_per_player=1,
            color_effects_enabled=False,
            animal_card_effects_enabled=True,
            critical_card_effects_enabled=False,
        ),
    )

    assert result.animal_events == []


def test_play_game_aggregates_animal_events_from_multiple_rounds(monkeypatch):
    def controlled_hands(players, rng, config, hand_sizes_by_player=None):
        return {
            1: [Card(Color.BLUE, 2)],
            2: [Card(Color.RED, 1)],
        }

    monkeypatch.setattr(game_module, "_deal_hands", controlled_hands)

    result = play_game(
        game_id=1,
        players_count=2,
        seed=42,
        config=GameConfig(
            initial_lives=12,
            critical_wounds_limit=2,
            cards_per_player=1,
            color_effects_enabled=False,
            animal_card_effects_enabled=True,
            critical_card_effects_enabled=False,
        ),
    )

    round_event_count = sum(
        len(round_result.animal_events)
        for round_result in result.round_history
    )
    scatto_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_SCATTO_IMPROVVISO
    ]
    assert result.rounds_count == 2
    assert len(result.animal_events) == round_event_count
    assert len(scatto_events) == 2
