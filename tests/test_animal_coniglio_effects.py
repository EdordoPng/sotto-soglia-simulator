from dataclasses import replace
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import BRICIOLA_NASCOSTA, V05_HUNGER_DECK_PROFILE_ID
from sotto_soglia.animal_effects import (
    CONIGLIO_GRANDE_BALZO,
    CONIGLIO_GRANDE_BALZO_DEBT,
    CONIGLIO_PASSO_LEGGERO,
    CONIGLIO_SCATTO_IMPROVVISO,
)
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.round import resolve_round
from sotto_soglia.rules import (
    get_effective_comparison_value,
    get_effective_consumption_value,
)


def _animal_config(**overrides) -> GameConfig:
    defaults = dict(
        initial_lives=12,
        critical_wounds_limit=5,
        color_effects_enabled=False,
        animal_card_effects_enabled=True,
    )
    defaults.update(overrides)
    return GameConfig(**defaults)


def test_game_config_disables_animal_card_effects_by_default():
    assert GameConfig().animal_card_effects_enabled is False


def test_v05_presets_enable_animal_card_effects():
    assert get_v05_config_for_players(2).animal_card_effects_enabled is True
    assert get_v05_config_for_players(3).animal_card_effects_enabled is True
    assert get_v05_config_for_players(4).animal_card_effects_enabled is True


def test_scatto_improvviso_sets_own_coniglio_one_effective_comparison_to_two():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    card = Card(Color.RED, 1)

    assert card.value == 1
    assert card.consumption_value == 1
    assert card.comparison_value == 1
    assert get_effective_comparison_value(player, card, _animal_config()) == 2


def test_scatto_improvviso_is_inactive_when_animal_effects_are_disabled():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    card = Card(Color.RED, 1)

    assert get_effective_comparison_value(player, card, GameConfig()) == 1


def test_scatto_improvviso_is_inactive_when_other_animal_plays_coniglio_one():
    card = Card(Color.RED, 1)

    for color in (Color.BLUE, Color.GREEN, Color.YELLOW):
        player = PlayerState(player_id=1, color=color, lives=12)

        assert get_effective_comparison_value(player, card, _animal_config()) == 1


def test_passo_leggero_has_no_context_free_effective_value_change():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    card = Card(Color.RED, 2)

    assert card.value == 2
    assert card.consumption_value == 2
    assert card.comparison_value == 2
    assert get_effective_consumption_value(player, card, _animal_config()) == 2
    assert get_effective_comparison_value(player, card, _animal_config()) == 2


def test_passo_leggero_is_inactive_when_animal_effects_are_disabled():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    card = Card(Color.RED, 2)

    assert get_effective_consumption_value(player, card, GameConfig()) == 2


def test_passo_leggero_is_inactive_when_other_animal_plays_coniglio_two():
    card = Card(Color.RED, 2)

    for color in (Color.BLUE, Color.GREEN, Color.YELLOW):
        player = PlayerState(player_id=1, color=color, lives=12)

        assert get_effective_consumption_value(player, card, _animal_config()) == 2


def test_grande_balzo_keeps_own_coniglio_four_effective_comparison_at_four():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    card = Card(Color.RED, 4)

    assert card.value == 4
    assert card.consumption_value == 4
    assert card.comparison_value == 4
    assert get_effective_comparison_value(player, card, _animal_config()) == 4


def test_grande_balzo_is_inactive_when_animal_effects_are_disabled():
    player = PlayerState(player_id=1, color=Color.RED, lives=12)
    card = Card(Color.RED, 4)

    assert get_effective_comparison_value(player, card, GameConfig()) == 4


def test_grande_balzo_is_inactive_when_other_animal_plays_coniglio_four():
    card = Card(Color.RED, 4)

    for color in (Color.BLUE, Color.GREEN, Color.YELLOW):
        player = PlayerState(player_id=1, color=color, lives=12)

        assert get_effective_comparison_value(player, card, _animal_config()) == 4


def test_round_affamato_uses_scatto_improvviso_effective_comparison_value():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 1),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.lowest_value == 1
    assert result.critical_wound_players == [1]
    assert players[0].critical_wounds == 1
    assert players[1].critical_wounds == 0


def test_round_result_has_empty_animal_events_without_tracked_effects():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 2),
        2: Card(Color.RED, 3),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.animal_events == []


def test_round_logs_scatto_improvviso_animal_event():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 1),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    scatto_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_SCATTO_IMPROVVISO
    ]
    assert len(scatto_events) == 1
    event = scatto_events[0]
    assert event.effect_id == CONIGLIO_SCATTO_IMPROVVISO
    assert event.effect_name == "Scatto Improvviso"
    assert event.timing == "comparison"
    assert event.status == "applied"
    assert event.player_id == 2
    assert event.card_color == "RED"
    assert event.card_value == 1
    assert event.value_before == 1
    assert event.value_after == 2


def test_round_does_not_log_scatto_improvviso_when_animals_disabled():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 1),
    }

    result = resolve_round(
        players,
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )

    assert result.animal_events == []


def test_round_passo_leggero_reduces_consumption_when_coniglio_gets_no_affamato():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [1]
    assert result.lowest_value == 1
    assert result.base_damage_by_player[2] == 1
    assert players[1].lives == 11
    passo_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_PASSO_LEGGERO
    ]
    assert len(passo_events) == 1
    event = passo_events[0]
    assert event.timing == "consumption"
    assert event.status == "applied"
    assert event.value_before == 2
    assert event.value_after == 1
    assert event.amount == 1
    assert event.actual_amount == 1
    assert event.reason == "no_affamato"


def test_round_passo_leggero_shared_printed_two_no_longer_sets_three_three():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 2),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 2]
    assert result.base_damage_by_player[2] == 0
    assert players[1].lives == 12

    passo_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_PASSO_LEGGERO
    ]
    assert passo_events == []


def test_round_passo_leggero_ignores_other_printed_two_even_if_effective_value_differs():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 2, custom_comparison_value=5),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.lowest_value == 2
    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[2] == 0
    assert players[1].lives == 12
    assert not any(event.effect_id == CONIGLIO_PASSO_LEGGERO for event in result.animal_events)


def test_round_base_consumption_keeps_coniglio_two_standard_when_animals_disabled():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, GameConfig(color_effects_enabled=False))

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[2] == 2
    assert players[1].lives == 10


def test_round_base_consumption_keeps_coniglio_two_standard_for_other_animal():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.RED, 2),
        2: Card(Color.BLUE, 1),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 2
    assert players[0].lives == 10


def test_passo_leggero_affamato_coniglio_consumes_zero_without_shared_printed_event():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 2, custom_comparison_value=4),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[2] == 0
    assert players[1].lives == 12
    assert not any(
        event.effect_id == CONIGLIO_PASSO_LEGGERO
        for event in result.animal_events
    )


def test_round_grande_balzo_keeps_comparison_four_and_schedules_debt():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 4),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.lowest_value == 4
    assert result.critical_wound_players == [1, 2]
    assert players[0].critical_wounds == 1
    assert players[1].critical_wounds == 1
    assert players[1].active_animal_effects == [CONIGLIO_GRANDE_BALZO_DEBT]
    assert result.base_damage_by_player[2] == 0


def test_round_logs_grande_balzo_current_free_and_schedule_events():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 4),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    balzo_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_GRANDE_BALZO
    ]
    assert {
        (event.timing, event.status, event.value_before, event.value_after, event.reason)
        for event in balzo_events
    } == {
        ("consumption", "applied", 4, 0, "current_round_free"),
        ("next_round_schedule", "scheduled", None, None, "triple_next_consumption"),
    }


def test_grande_balzo_debt_next_round_consumption_one_pays_three():
    players = [
        PlayerState(
            player_id=1,
            color=Color.RED,
            lives=12,
            active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.RED, 1),
            2: Card(Color.BLUE, 5),
        },
        _animal_config(),
    )

    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 9
    assert players[0].active_animal_effects == []


def test_grande_balzo_debt_next_round_red_two_uses_passo_leggero_then_pays_three():
    players = [
        PlayerState(
            player_id=1,
            color=Color.RED,
            lives=12,
            active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.RED, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 9


def test_grande_balzo_debt_next_round_plain_consumption_two_pays_six():
    players = [
        PlayerState(
            player_id=1,
            color=Color.RED,
            lives=12,
            active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.base_damage_by_player[1] == 6
    assert players[0].lives == 6


def test_grande_balzo_debt_next_round_consumption_four_pays_twelve():
    players = [
        PlayerState(
            player_id=1,
            color=Color.RED,
            lives=15,
            active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 4),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(initial_lives=15),
    )

    assert result.base_damage_by_player[1] == 12
    assert players[0].lives == 3


def test_grande_balzo_debt_applies_even_when_coniglio_receives_affamato():
    players = [
        PlayerState(
            player_id=1,
            color=Color.RED,
            lives=12,
            active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.RED, 2),
            2: Card(Color.BLUE, 5),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 6
    assert players[0].lives == 6


def test_grande_balzo_debt_logs_apply_and_consume_events():
    players = [
        PlayerState(
            player_id=1,
            color=Color.RED,
            lives=12,
            active_animal_effects=[CONIGLIO_GRANDE_BALZO_DEBT],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.RED, 1),
            2: Card(Color.BLUE, 5),
        },
        _animal_config(),
    )

    balzo_events = [
        event
        for event in result.animal_events
        if event.effect_id == CONIGLIO_GRANDE_BALZO
    ]
    assert {
        (event.timing, event.status, event.value_before, event.value_after, event.reason)
        for event in balzo_events
    } == {
        ("consumption", "applied", 1, 3, "triple_debt_applied"),
        ("next_round_consume", "consumed", None, None, "triple_debt_consumed"),
    }


def test_round_ties_coniglio_four_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 4),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, GameConfig(color_effects_enabled=False))

    assert result.lowest_value == 4
    assert result.critical_wound_players == [1, 2]


def test_round_ties_coniglio_one_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 1),
    }

    result = resolve_round(players, selected_cards, GameConfig(color_effects_enabled=False))

    assert result.lowest_value == 1
    assert result.critical_wound_players == [1, 2]


def test_hunger_effects_still_resolve_after_scatto_improvviso_assignment():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=7),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    config = _animal_config(
        critical_card_effects_enabled=True,
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
        },
        config,
        critical_deck=[BRICIOLA_NASCOSTA],
    )

    assert result.critical_wound_players == [1]
    assert players[0].critical_cards_drawn == [BRICIOLA_NASCOSTA]
    assert players[0].lives == 8
    assert players[1].critical_cards_drawn == []


def test_runtime_standard_result_does_not_change_without_animal_effect_flag():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 1),
    }

    baseline = resolve_round(
        [
            PlayerState(player_id=1, color=Color.BLUE, lives=12),
            PlayerState(player_id=2, color=Color.RED, lives=12),
        ],
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )
    v05_without_animals = resolve_round(
        players,
        selected_cards,
        replace(
            get_v05_config_for_players(2),
            critical_card_effects_enabled=False,
            animal_card_effects_enabled=False,
        ),
    )

    assert v05_without_animals.critical_wound_players == baseline.critical_wound_players
    assert v05_without_animals.lowest_value == baseline.lowest_value
