import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from random import Random

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import (
    BENDAGGIO_EMERGENZA,
    BRICIOLA_NASCOSTA,
    COLPO_DI_CODA,
    CRITICAL_CARD_IDS,
    FERITA_ESPOSTA,
    FIUTO_DA_DISPENSA,
    LEGACY_CRITICAL_DECK_PROFILE,
    LEGACY_CRITICAL_DECK_PROFILE_ID,
    MANO_LUCIDA,
    MANO_TREMANTE,
    MORSO_DELLA_FAME,
    PANCIA_BRONTOLANTE,
    RAZIONE_RISPARMIATA,
    RESPIRO_CALMO,
    SANGUE_FREDDO,
    SCUDO_ISTINTIVO,
    SONO_ANCORA_QUI,
    SONO_ANCORA_QUI_SINGLE_1,
    SONO_ANCORA_QUI_SINGLE_2,
    SONO_ANCORA_QUI_UP_TO_2_TARGETS,
    V05_HUNGER_CARD_IDS,
    V05_HUNGER_CARD_NAMES,
    V05_HUNGER_DECK_PROFILE,
    V05_HUNGER_DECK_PROFILE_ID,
    build_critical_deck,
    get_critical_deck_profile,
    shuffle_critical_deck,
    validate_critical_deck_order,
)
from sotto_soglia.exporters import CSV_DELIMITER, export_simulation_result
from sotto_soglia.game import _hand_sizes_from_critical_effects
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.round import resolve_round
from sotto_soglia.simulation import SimulationRunner
from sotto_soglia.strategies import (
    AggressiveStrategy,
    BaseStrategy,
    AdaptivePressureStrategy,
    create_strategy,
    choose_fallback_critical_effect_target,
)


def _critical_config(deck_order=None, sono_variant="single_2"):
    return GameConfig(
        initial_lives=18,
        critical_wounds_limit=5,
        critical_card_effects_enabled=True,
        critical_deck_order=tuple(deck_order) if deck_order else None,
        sono_ancora_qui_variant=sono_variant,
    )


def test_critical_deck_contains_two_copies_of_eight_effects():
    deck = build_critical_deck()

    assert len(deck) == 16
    assert set(deck) == set(CRITICAL_CARD_IDS)
    assert Counter(deck) == {card_id: 2 for card_id in CRITICAL_CARD_IDS}


def test_legacy_critical_deck_profile_matches_existing_deck_composition():
    deck = build_critical_deck(LEGACY_CRITICAL_DECK_PROFILE)

    assert LEGACY_CRITICAL_DECK_PROFILE.profile_id == "legacy"
    assert LEGACY_CRITICAL_DECK_PROFILE.deck_name == "Mazzo Ferita Critica"
    assert LEGACY_CRITICAL_DECK_PROFILE.cards_count == 16
    assert LEGACY_CRITICAL_DECK_PROFILE.copies_per_effect == 2
    assert LEGACY_CRITICAL_DECK_PROFILE.card_ids == CRITICAL_CARD_IDS
    assert Counter(deck) == {card_id: 2 for card_id in CRITICAL_CARD_IDS}


def test_critical_deck_profiles_are_recoverable_by_id():
    assert (
        get_critical_deck_profile(LEGACY_CRITICAL_DECK_PROFILE_ID)
        is LEGACY_CRITICAL_DECK_PROFILE
    )
    assert (
        get_critical_deck_profile(V05_HUNGER_DECK_PROFILE_ID)
        is V05_HUNGER_DECK_PROFILE
    )


def test_unknown_critical_deck_profile_id_raises_clear_error():
    with pytest.raises(ValueError) as error_info:
        get_critical_deck_profile("unknown_profile")

    assert "Unknown critical deck profile 'unknown_profile'" in str(error_info.value)
    assert "legacy" in str(error_info.value)
    assert "v05_hunger" in str(error_info.value)


def test_v05_hunger_deck_profile_contains_six_effects_and_eighteen_cards():
    deck = build_critical_deck(V05_HUNGER_DECK_PROFILE)

    assert V05_HUNGER_DECK_PROFILE.deck_name == "Mazzo Affamato"
    assert V05_HUNGER_DECK_PROFILE.cards_count == 18
    assert V05_HUNGER_DECK_PROFILE.copies_per_effect == 3
    assert len(V05_HUNGER_CARD_IDS) == 6
    assert len(deck) == 18
    assert set(deck) == set(V05_HUNGER_CARD_IDS)
    assert Counter(deck) == {card_id: 3 for card_id in V05_HUNGER_CARD_IDS}


def test_critical_deck_can_be_built_from_profile_id():
    legacy_deck = build_critical_deck(LEGACY_CRITICAL_DECK_PROFILE_ID)
    hunger_deck = build_critical_deck(V05_HUNGER_DECK_PROFILE_ID)

    assert len(legacy_deck) == 16
    assert Counter(legacy_deck) == {card_id: 2 for card_id in CRITICAL_CARD_IDS}
    assert len(hunger_deck) == 18
    assert Counter(hunger_deck) == {card_id: 3 for card_id in V05_HUNGER_CARD_IDS}


def test_v05_hunger_deck_profile_uses_expected_effect_names():
    assert V05_HUNGER_CARD_NAMES == {
        BRICIOLA_NASCOSTA: "Briciola Nascosta",
        RAZIONE_RISPARMIATA: "Razione Risparmiata",
        FIUTO_DA_DISPENSA: "Fiuto da Dispensa",
        PANCIA_BRONTOLANTE: "Pancia Brontolante",
        MORSO_DELLA_FAME: "Morso della Fame",
        RESPIRO_CALMO: "Respiro Calmo",
    }


def test_v05_hunger_deck_shuffle_is_reproducible_with_seed():
    first = shuffle_critical_deck(123, V05_HUNGER_DECK_PROFILE)
    second = shuffle_critical_deck(123, V05_HUNGER_DECK_PROFILE)
    different_seed = shuffle_critical_deck(124, V05_HUNGER_DECK_PROFILE)

    assert first == second
    assert first != different_seed
    assert Counter(first) == {card_id: 3 for card_id in V05_HUNGER_CARD_IDS}


def test_v05_hunger_profile_is_not_silently_used_in_runtime_before_effects_exist():
    config = GameConfig(
        critical_card_effects_enabled=True,
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )

    with pytest.raises(NotImplementedError) as error_info:
        SimulationRunner().run(
            players_count=2,
            games_count=1,
            seed=42,
            config=config,
        )

    assert "Critical deck profile 'v05_hunger' is not implemented" in str(
        error_info.value
    )


def test_critical_deck_shuffle_is_reproducible_with_seed():
    assert shuffle_critical_deck(123) == shuffle_critical_deck(123)
    assert shuffle_critical_deck(123) != shuffle_critical_deck(124)


def test_fixed_critical_deck_order_validation_accepts_valid_order():
    order = ",".join(build_critical_deck())

    assert validate_critical_deck_order(order) == tuple(build_critical_deck())


def test_fixed_critical_deck_order_validation_rejects_invalid_order():
    invalid_order = ",".join([BENDAGGIO_EMERGENZA] * 16)

    try:
        validate_critical_deck_order(invalid_order)
    except ValueError as error:
        assert "exactly 2 copies" in str(error)
        return

    assert False, "Expected ValueError for invalid critical deck order"


def test_critical_card_effects_off_draws_no_cards():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    deck = [BENDAGGIO_EMERGENZA]

    result = resolve_round(
        players,
        {1: Card(Color.BLUE, 1), 2: Card(Color.RED, 3)},
        GameConfig(),
        critical_deck=deck,
    )

    assert result.critical_wound_players == [1]
    assert players[0].critical_cards_drawn == []
    assert deck == [BENDAGGIO_EMERGENZA]
    assert result.critical_events == []


def test_critical_draw_uses_top_card_and_empty_deck_has_no_effect():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    deck = [BENDAGGIO_EMERGENZA]

    resolve_round(
        players,
        {1: Card(Color.BLUE, 1), 2: Card(Color.RED, 3)},
        _critical_config(),
        critical_deck=deck,
    )

    assert players[0].critical_wounds == 1
    assert players[0].critical_cards_drawn == [BENDAGGIO_EMERGENZA]
    assert players[0].lives == 11
    assert deck == []

    resolve_round(
        players,
        {1: Card(Color.BLUE, 1), 2: Card(Color.RED, 3)},
        _critical_config(),
        critical_deck=deck,
    )

    assert players[0].critical_wounds == 2
    assert players[0].critical_cards_drawn == [BENDAGGIO_EMERGENZA]


def test_multiple_critical_draws_follow_player_id_order():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=16),
        PlayerState(player_id=2, color=Color.RED, lives=16),
        PlayerState(player_id=3, color=Color.GREEN, lives=16),
    ]
    deck = [BENDAGGIO_EMERGENZA, SANGUE_FREDDO]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
            3: Card(Color.GREEN, 4),
        },
        _critical_config(),
        critical_deck=deck,
    )

    assert result.critical_draw_order == [1, 2]
    assert players[0].critical_cards_drawn == [BENDAGGIO_EMERGENZA]
    assert players[1].critical_cards_drawn == [SANGUE_FREDDO]
    assert [event.draw_order for event in result.critical_events] == [1, 2]


def test_bendaggio_does_not_exceed_initial_lives():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=17),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]

    resolve_round(
        players,
        {1: Card(Color.BLUE, 1), 2: Card(Color.RED, 3)},
        _critical_config(),
        critical_deck=[BENDAGGIO_EMERGENZA],
    )

    assert players[0].lives == 18
    assert players[0].life_gained_from_critical_cards == 1


def test_sono_ancora_qui_default_damages_one_valid_nonimmune_opponent_for_two():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]

    resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
            3: Card(Color.GREEN, 4),
        },
        _critical_config(),
        critical_deck=[SONO_ANCORA_QUI],
    )

    assert players[0].lives == 18
    assert players[1].lives == 18
    assert players[2].lives == 13


def test_bendaggio_recovers_one_life_not_two():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]

    resolve_round(
        players,
        {1: Card(Color.BLUE, 1), 2: Card(Color.RED, 3)},
        _critical_config(),
        critical_deck=[BENDAGGIO_EMERGENZA],
    )

    assert players[0].lives == 11
    assert players[0].life_gained_from_critical_cards == 1


def test_sono_ancora_qui_default_hits_only_one_valid_target_and_logs_two_damage():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=10),
        PlayerState(player_id=3, color=Color.GREEN, lives=6),
        PlayerState(player_id=4, color=Color.YELLOW, lives=6, critical_wounds=2),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 4),
            3: Card(Color.GREEN, 4),
            4: Card(Color.YELLOW, 4),
        },
        _critical_config(),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_events = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ]
    assert len(sono_events) == 1
    assert sono_events[0].target_player_id == "4"
    assert sono_events[0].life_delta_targets == {4: -2}
    assert len(sono_events[0].life_delta_targets) == 1


def test_sono_ancora_qui_single_1_variant_hits_one_target_for_one_life():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=4),
        PlayerState(player_id=3, color=Color.GREEN, lives=8),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 4),
            3: Card(Color.GREEN, 4),
        },
        _critical_config(sono_variant=SONO_ANCORA_QUI_SINGLE_1),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.target_player_id == "2"
    assert sono_event.life_delta_targets == {2: -1}


def test_sono_ancora_qui_single_2_hits_one_target_for_two_life_without_below_zero():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=1),
        PlayerState(player_id=3, color=Color.GREEN, lives=8),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 4),
            3: Card(Color.GREEN, 4),
        },
        _critical_config(sono_variant=SONO_ANCORA_QUI_SINGLE_2),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.target_player_id == "2"
    assert sono_event.life_delta_targets == {2: -1}
    assert players[1].lives == 0
    assert players[2].lives == 5


def test_sono_ancora_qui_up_to_2_targets_hits_two_valid_targets():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=4),
        PlayerState(player_id=3, color=Color.GREEN, lives=5),
        PlayerState(player_id=4, color=Color.YELLOW, lives=9),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 4),
            3: Card(Color.GREEN, 4),
            4: Card(Color.YELLOW, 4),
        },
        _critical_config(sono_variant=SONO_ANCORA_QUI_UP_TO_2_TARGETS),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.target_player_id == "2,3"
    assert sono_event.life_delta_targets == {2: -1, 3: -1}
    assert players[1].lives == 0
    assert players[2].lives == 1
    assert players[3].lives == 6


def test_sono_ancora_qui_up_to_2_targets_hits_one_when_only_one_is_valid():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=5, is_alive=False),
        PlayerState(player_id=4, color=Color.YELLOW, lives=7),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
            4: Card(Color.YELLOW, 4),
        },
        _critical_config(sono_variant=SONO_ANCORA_QUI_UP_TO_2_TARGETS),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.target_player_id == "4"
    assert sono_event.life_delta_targets == {4: -1}


def test_sono_ancora_qui_does_not_hit_eliminated_immune_or_self():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=5, is_alive=False),
        PlayerState(player_id=4, color=Color.YELLOW, lives=7),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
            4: Card(Color.YELLOW, 4),
        },
        _critical_config(),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.target_player_id == "4"
    assert sono_event.life_delta_targets == {4: -2}
    assert players[0].lives == 18
    assert players[1].lives == 18
    assert players[2].lives == 5


def test_sono_ancora_qui_has_no_effect_without_valid_targets():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
        },
        _critical_config(),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.effect_triggered is False
    assert sono_event.target_player_id is None
    assert sono_event.life_delta_targets == {}
    assert players[0].lives == 18
    assert players[1].lives == 18


def test_sono_ancora_qui_up_to_2_targets_has_no_effect_without_valid_targets():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 1),
        },
        _critical_config(sono_variant=SONO_ANCORA_QUI_UP_TO_2_TARGETS),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: create_strategy("critical_adaptive")},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.effect_triggered is False
    assert sono_event.target_player_id is None
    assert sono_event.life_delta_targets == {}


def test_sono_ancora_qui_uses_strategy_target_choice():
    class PickHighestIdStrategy(BaseStrategy):
        name = "pick_highest_id"

        def choose_card(self, player, hand, game_state, rng):
            return hand[0]

        def choose_critical_effect_target(
            self,
            game_state,
            source_player,
            effect_id,
            valid_targets,
            rng,
        ):
            return max(valid_targets, key=lambda target: target.player_id)

    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=3),
        PlayerState(player_id=3, color=Color.GREEN, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 4),
            3: Card(Color.GREEN, 4),
        },
        _critical_config(),
        critical_deck=[SONO_ANCORA_QUI],
        strategies={1: PickHighestIdStrategy()},
    )

    sono_event = [
        event for event in result.critical_events if event.critical_card_id == SONO_ANCORA_QUI
    ][0]
    assert sono_event.target_player_id == "3"


def test_mano_lucida_and_mano_tremante_set_next_round_hand_size():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    players[0].active_critical_effects = [MANO_LUCIDA]
    players[1].active_critical_effects = [MANO_TREMANTE]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _critical_config(),
        {1: [MANO_LUCIDA], 2: [MANO_TREMANTE]},
        game_id=1,
        round_number=2,
    )

    assert hand_sizes == {1: 4, 2: 2}
    assert [event.critical_card_id for event in events] == [MANO_LUCIDA, MANO_TREMANTE]


def test_sangue_freddo_reduces_own_color_damage_by_two_with_minimum_one():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    players[0].active_critical_effects = [SANGUE_FREDDO]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 0),
            3: Card(Color.GREEN, 4),
        },
        _critical_config(),
        critical_deck=[],
    )

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 1
    assert players[0].active_critical_effects == []
    assert players[0].consumed_critical_effects == [SANGUE_FREDDO]


def test_scudo_istintivo_ignores_only_first_extra_damage():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
        PlayerState(player_id=4, color=Color.YELLOW, lives=18),
    ]
    players[0].active_critical_effects = [SCUDO_ISTINTIVO]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 3),
            3: Card(Color.BLUE, 5),
            4: Card(Color.YELLOW, 1),
        },
        _critical_config(),
        critical_deck=[],
    )

    assert result.extra_damage_by_player[1] == 1
    assert result.critical_prevented_damage_by_player[1] == 1
    assert players[0].lives == 13


def test_ferita_esposta_increases_only_first_extra_damage():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
        PlayerState(player_id=4, color=Color.YELLOW, lives=18),
    ]
    players[0].active_critical_effects = [FERITA_ESPOSTA]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 3),
            3: Card(Color.BLUE, 5),
            4: Card(Color.YELLOW, 1),
        },
        _critical_config(),
        critical_deck=[],
    )

    assert result.extra_damage_by_player[1] == 3
    assert players[0].lives == 11


def test_colpo_di_coda_triggers_only_on_next_critical_and_uses_valid_target():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
        PlayerState(player_id=3, color=Color.GREEN, lives=18),
    ]
    players[0].active_critical_effects = [COLPO_DI_CODA]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 3),
            3: Card(Color.GREEN, 1),
        },
        _critical_config(),
        critical_deck=[],
        strategies={1: AggressiveStrategy()},
        rng=Random(1),
    )

    assert result.critical_wound_players == [1, 3]
    assert players[1].lives == 14
    assert players[2].lives == 18
    assert players[0].active_critical_effects == []
    colpo_events = [
        event for event in result.critical_events if event.critical_card_id == COLPO_DI_CODA
    ]
    assert colpo_events[0].target_player_id == 2


def test_colpo_di_coda_consumes_without_trigger_when_no_new_critical():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=18),
        PlayerState(player_id=2, color=Color.RED, lives=18),
    ]
    players[0].active_critical_effects = [COLPO_DI_CODA]

    resolve_round(
        players,
        {1: Card(Color.BLUE, 4), 2: Card(Color.RED, 1)},
        _critical_config(),
        critical_deck=[],
    )

    assert players[1].lives == 18
    assert players[0].active_critical_effects == []
    assert players[0].consumed_critical_effects == [COLPO_DI_CODA]


def test_critical_adaptive_strategy_is_selectable():
    assert create_strategy("critical_adaptive").name == "critical_adaptive"


def test_choose_critical_effect_target_returns_valid_target_and_fallback_works():
    source = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    target_a = PlayerState(player_id=2, color=Color.RED, lives=4)
    target_b = PlayerState(player_id=3, color=Color.GREEN, lives=8)
    valid_targets = [target_a, target_b]

    selected = AggressiveStrategy().choose_critical_effect_target(
        {"players": [source, target_a, target_b]},
        source,
        COLPO_DI_CODA,
        valid_targets,
        Random(1),
    )

    assert selected in valid_targets
    assert choose_fallback_critical_effect_target(valid_targets) == target_a


def test_adaptive_pressure_targets_lowest_lives_for_sono_ancora_qui():
    source = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    target_a = PlayerState(player_id=2, color=Color.RED, lives=6, critical_wounds=0)
    target_b = PlayerState(player_id=3, color=Color.GREEN, lives=4, critical_wounds=0)

    selected = AdaptivePressureStrategy().choose_critical_effect_target(
        {"players": [source, target_a, target_b]},
        source,
        SONO_ANCORA_QUI,
        [target_a, target_b],
        Random(1),
    )

    assert selected == target_b


def test_adaptive_pressure_breaks_sono_ancora_qui_life_ties_by_critical_wounds():
    source = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    target_a = PlayerState(player_id=2, color=Color.RED, lives=4, critical_wounds=0)
    target_b = PlayerState(player_id=3, color=Color.GREEN, lives=4, critical_wounds=2)

    selected = AdaptivePressureStrategy().choose_critical_effect_target(
        {"players": [source, target_a, target_b]},
        source,
        SONO_ANCORA_QUI,
        [target_a, target_b],
        Random(1),
    )

    assert selected == target_b


def test_strategy_without_target_override_uses_base_fallback():
    class PlainStrategy(BaseStrategy):
        name = "plain"

        def choose_card(self, player, hand, game_state, rng):
            return hand[0]

    source = PlayerState(player_id=1, color=Color.BLUE, lives=18)
    target = PlayerState(player_id=2, color=Color.RED, lives=3)

    assert (
        PlainStrategy().choose_critical_effect_target(
            None,
            source,
            COLPO_DI_CODA,
            [target],
            Random(1),
        )
        == target
    )


def test_export_writes_critical_files_when_enabled(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=3,
        seed=42,
        config=_critical_config(build_critical_deck()),
        strategies=create_strategy("critical_adaptive"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    assert exported_files["critical_events"].exists()
    assert exported_files["critical_deck_orders"].exists()
    assert exported_files["critical_card_stats"].exists()

    with exported_files["critical_events"].open(encoding="utf-8", newline="") as file:
        events = list(csv.DictReader(file, delimiter=CSV_DELIMITER))
    assert events
    assert "critical_card_id" in events[0]

    with exported_files["critical_deck_orders"].open(encoding="utf-8", newline="") as file:
        orders = list(csv.DictReader(file, delimiter=CSV_DELIMITER))
    assert len(orders) == 3
    assert orders[0]["critical_deck_order"].startswith(BENDAGGIO_EMERGENZA)

    with exported_files["aggregate_stats"].open(encoding="utf-8") as file:
        stats = json.load(file)
    assert "critical_cards_drawn_total" in stats
    assert "bendaggio_trigger_count" in stats


def test_export_keeps_historical_files_only_when_critical_effects_off(tmp_path):
    simulation = SimulationRunner().run(players_count=4, games_count=2, seed=42)

    exported_files = export_simulation_result(simulation, tmp_path)

    assert "games_summary" in exported_files
    assert "rounds_summary" in exported_files
    assert "critical_events" not in exported_files


def test_cli_accepts_critical_adaptive_and_critical_flags(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "3",
            "--seed",
            "42",
            "--strategy",
            "critical_adaptive",
            "--critical-card-effects",
            "on",
            "--critical-deck-seed",
            "123",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "- critical_adaptive:" in result.stdout
    assert (tmp_path / "critical_events.csv").exists()


def test_cli_defaults_sono_ancora_qui_variant_to_single_2(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "2",
            "--seed",
            "42",
            "--strategy",
            "critical_adaptive",
            "--critical-card-effects",
            "on",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with (tmp_path / "simulation_config.json").open(encoding="utf-8") as file:
        config = json.load(file)

    assert config["sono_ancora_qui_variant"] == "single_2"


def test_cli_exports_sono_ancora_qui_variant_and_critical_damage(tmp_path):
    order = ",".join(
        [
            SONO_ANCORA_QUI,
            SONO_ANCORA_QUI,
            BENDAGGIO_EMERGENZA,
            BENDAGGIO_EMERGENZA,
            SANGUE_FREDDO,
            SANGUE_FREDDO,
            MANO_LUCIDA,
            MANO_LUCIDA,
            SCUDO_ISTINTIVO,
            SCUDO_ISTINTIVO,
            MANO_TREMANTE,
            MANO_TREMANTE,
            COLPO_DI_CODA,
            COLPO_DI_CODA,
            FERITA_ESPOSTA,
            FERITA_ESPOSTA,
        ]
    )
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "3",
            "--seed",
            "42",
            "--strategy",
            "critical_adaptive",
            "--critical-card-effects",
            "on",
            "--critical-deck-order",
            order,
            "--sono-ancora-qui-variant",
            "up_to_2_targets",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with (tmp_path / "simulation_config.json").open(encoding="utf-8") as file:
        config = json.load(file)
    with (tmp_path / "critical_events.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))
    with (tmp_path / "aggregate_stats.json").open(encoding="utf-8") as file:
        stats = json.load(file)

    sono_rows = [
        row for row in rows if row["critical_card_id"] == SONO_ANCORA_QUI
    ]
    assert config["sono_ancora_qui_variant"] == "up_to_2_targets"
    assert sono_rows
    assert any("," in row["target_player_id"] for row in sono_rows)
    assert stats["critical_card_stats"][SONO_ANCORA_QUI]["total_life_delta"] < 0


def test_cli_without_final_config_flags_uses_v05_player_preset(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "2",
            "--games",
            "1",
            "--seed",
            "42",
            "--strategy",
            "adaptive_pressure",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with (tmp_path / "simulation_config.json").open(encoding="utf-8") as file:
        config = json.load(file)

    preset = get_v05_config_for_players(2)
    assert config["initial_lives"] == preset.initial_lives
    assert config["critical_wounds_limit"] == preset.critical_wounds_limit
    assert config["color_effects_enabled"] is False


def test_cli_final_config_flags_for_two_players_are_exported(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "2",
            "--games",
            "3",
            "--seed",
            "42",
            "--strategy",
            "critical_adaptive",
            "--initial-lives",
            "12",
            "--critical-wounds-max",
            "5",
            "--critical-card-effects",
            "on",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with (tmp_path / "simulation_config.json").open(encoding="utf-8") as file:
        config = json.load(file)

    assert config["players_count"] == 2
    assert config["initial_lives"] == 12
    assert config["critical_wounds_limit"] == 5
    assert (tmp_path / "critical_events.csv").exists()
    assert (tmp_path / "critical_deck_orders.csv").exists()
    assert (tmp_path / "critical_card_stats.csv").exists()


def test_cli_final_config_flags_for_three_players_are_exported(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "3",
            "--games",
            "3",
            "--seed",
            "42",
            "--strategy",
            "adaptive_pressure",
            "--initial-lives",
            "17",
            "--critical-wounds-max",
            "4",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with (tmp_path / "simulation_config.json").open(encoding="utf-8") as file:
        config = json.load(file)

    assert config["players_count"] == 3
    assert config["initial_lives"] == 17
    assert config["critical_wounds_limit"] == 4


def test_cli_final_config_flags_for_four_players_are_exported(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "3",
            "--seed",
            "42",
            "--strategy",
            "adaptive_pressure",
            "--initial-lives",
            "24",
            "--critical-wounds-max",
            "4",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with (tmp_path / "simulation_config.json").open(encoding="utf-8") as file:
        config = json.load(file)

    assert config["players_count"] == 4
    assert config["initial_lives"] == 24
    assert config["critical_wounds_limit"] == 4


def test_cli_parametric_uses_critical_card_flags(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "3",
            "--seed",
            "42",
            "--parametric",
            "--strategy",
            "critical_adaptive",
            "--lives-values",
            "24",
            "--critical-wounds-values",
            "4",
            "--color-effects",
            "on",
            "--critical-card-effects",
            "on",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Sotto Soglia Parametric Simulation" in result.stdout
    with (tmp_path / "parametric_stats.json").open(encoding="utf-8") as file:
        stats = json.load(file)
    aggregate_stats = stats["config_results"][0]["aggregate_stats"]
    assert aggregate_stats["critical_cards_drawn_total"] > 0


def test_cli_tournament_uses_critical_card_flags(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_simulation.py"),
            "--players",
            "4",
            "--games",
            "1",
            "--seed",
            "42",
            "--tournament-strategies",
            "critical_adaptive",
            "adaptive_pressure",
            "random",
            "defensive",
            "--critical-card-effects",
            "on",
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Sotto Soglia Strategy Tournament" in result.stdout
    with (tmp_path / "strategy_tournament_stats.json").open(encoding="utf-8") as file:
        stats = json.load(file)
    aggregate_stats = stats["aggregate_stats"]
    assert aggregate_stats["critical_cards_drawn_total"] > 0
