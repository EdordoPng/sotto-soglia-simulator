from dataclasses import replace
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import RAZIONE_RISPARMIATA, V05_HUNGER_DECK_PROFILE_ID
from sotto_soglia.animal_effects import PANDA_GRANDE_LETARGO
from sotto_soglia.models import Card, Color, EliminationReason, PlayerState
import sotto_soglia.round as round_module
from sotto_soglia.round import resolve_round
from sotto_soglia.rules import (
    get_effective_comparison_value,
    get_effective_consumption_value,
)


def _animal_config(**overrides) -> GameConfig:
    values = {
        "initial_lives": 12,
        "critical_wounds_limit": 5,
        "color_effects_enabled": False,
        "animal_card_effects_enabled": True,
    }
    values.update(overrides)
    return GameConfig(**values)


def test_riposo_forzato_recovers_one_in_recovery_phase():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0
    assert players[0].lives == 11


def test_riposo_forzato_does_not_recover_before_recovery_phase(monkeypatch):
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }
    lives_seen_before_recovery = {}
    pending_seen_at_recovery = {}
    original_apply = round_module.apply_pending_animal_life_recoveries

    def spy_apply_pending_animal_life_recoveries(
        player_map,
        pending_life_recoveries,
        config,
    ):
        lives_seen_before_recovery.update(
            {
                player_id: player.lives
                for player_id, player in player_map.items()
            }
        )
        pending_seen_at_recovery.update(pending_life_recoveries)
        return original_apply(player_map, pending_life_recoveries, config)

    monkeypatch.setattr(
        round_module,
        "apply_pending_animal_life_recoveries",
        spy_apply_pending_animal_life_recoveries,
    )

    round_module.resolve_round(players, selected_cards, _animal_config())

    assert pending_seen_at_recovery == {1: 1}
    assert lives_seen_before_recovery[1] == 10
    assert players[0].lives == 11


def test_riposo_forzato_does_not_exceed_initial_lives():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    resolve_round(players, selected_cards, _animal_config())

    assert players[0].lives == 12


def test_riposo_forzato_works_when_panda_receives_affamato():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [1]
    assert players[0].critical_wounds == 1
    assert result.base_damage_by_player[1] == 0
    assert players[0].lives == 11


def test_riposo_forzato_does_not_prevent_affamato_threshold_elimination():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    result = resolve_round(
        players,
        selected_cards,
        _animal_config(critical_wounds_limit=1),
    )

    assert result.critical_wound_players == [1]
    assert result.eliminated_players == [1]
    assert players[0].lives == 11
    assert players[0].critical_wounds == 1
    assert players[0].is_alive is False
    assert players[0].elimination_reason == EliminationReason.CRITICAL_WOUNDS


def test_riposo_forzato_is_inactive_when_other_animals_play_panda_one():
    for color in (Color.RED, Color.GREEN, Color.YELLOW):
        players = [
            PlayerState(player_id=1, color=color, lives=10),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
        ]
        selected_cards = {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 2),
        }

        result = resolve_round(players, selected_cards, _animal_config())

        assert result.critical_wound_players == [1]
        assert result.base_damage_by_player[1] == 0
        assert players[0].lives == 10


def test_riposo_forzato_keeps_panda_one_printed_values_unchanged():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 1)

    assert card.value == 1
    assert card.comparison_value == 1
    assert card.consumption_value == 1
    assert get_effective_comparison_value(player, card, _animal_config()) == 1
    assert get_effective_consumption_value(player, card, _animal_config()) == 1


def test_respiro_lento_reduces_own_panda_three_consumption_by_one():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3)
    config = _animal_config()

    assert card.value == 3
    assert card.consumption_value == 3
    assert card.comparison_value == 3
    assert get_effective_consumption_value(player, card, config) == 2
    assert get_effective_comparison_value(player, card, config) == 3


def test_respiro_lento_is_inactive_when_animal_effects_are_disabled():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3)

    assert get_effective_consumption_value(player, card, GameConfig()) == 3


def test_respiro_lento_is_inactive_when_other_animals_play_panda_three():
    card = Card(Color.BLUE, 3)

    for color in (Color.RED, Color.GREEN, Color.YELLOW):
        player = PlayerState(player_id=1, color=color, lives=12)

        assert get_effective_consumption_value(player, card, _animal_config()) == 3
        assert get_effective_comparison_value(player, card, _animal_config()) == 3


def test_round_base_consumption_uses_respiro_lento_when_panda_is_not_affamato():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 1),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 2
    assert players[0].lives == 10


def test_respiro_lento_does_not_make_affamato_panda_consume_two():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0
    assert players[0].lives == 12


def test_respiro_lento_does_not_modify_effective_comparison_value():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3)

    assert get_effective_comparison_value(player, card, _animal_config()) == 3


def test_respiro_lento_combines_with_razione_risparmiata_to_minimum_one():
    players = [
        PlayerState(
            player_id=1,
            color=Color.BLUE,
            lives=12,
            active_critical_effects=[RAZIONE_RISPARMIATA],
        ),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 3),
        2: Card(Color.RED, 1),
    }
    config = _animal_config(
        critical_card_effects_enabled=True,
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )

    result = resolve_round(players, selected_cards, config)

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 1
    assert players[0].lives == 11
    assert players[0].consumed_critical_effects == [RAZIONE_RISPARMIATA]


def test_respiro_lento_consumption_never_drops_below_one():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    card = Card(Color.BLUE, 3, custom_consumption_value=1)

    assert get_effective_consumption_value(player, card, _animal_config()) == 1


def test_grande_letargo_registers_next_round_without_changing_current_comparison():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 5),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.lowest_value == 5
    assert result.critical_wound_players == [1, 2]
    assert players[0].active_animal_effects == [PANDA_GRANDE_LETARGO]
    assert result.base_damage_by_player[1] == 0


def test_grande_letargo_registers_even_when_panda_receives_affamato():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 5),
        2: Card(Color.RED, 4),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert 1 in result.critical_wound_players
    assert result.base_damage_by_player[1] == 0
    assert players[0].active_animal_effects == [PANDA_GRANDE_LETARGO]


def test_grande_letargo_active_sets_panda_five_comparison_to_three_and_keeps_consumption():
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        active_animal_effects=[PANDA_GRANDE_LETARGO],
    )
    card = Card(Color.BLUE, 5)

    assert get_effective_comparison_value(player, card, _animal_config()) == 3
    assert get_effective_consumption_value(player, card, _animal_config()) == 5


def test_grande_letargo_active_sets_panda_one_comparison_to_three_and_keeps_consumption():
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        active_animal_effects=[PANDA_GRANDE_LETARGO],
    )
    card = Card(Color.BLUE, 1)

    assert get_effective_comparison_value(player, card, _animal_config()) == 3
    assert get_effective_consumption_value(player, card, _animal_config()) == 1


def test_grande_letargo_active_applies_to_non_panda_card_without_grande_balzo():
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        active_animal_effects=[PANDA_GRANDE_LETARGO],
    )
    card = Card(Color.RED, 4)

    assert get_effective_comparison_value(player, card, _animal_config()) == 3
    assert get_effective_consumption_value(player, card, _animal_config()) == 4


def test_grande_letargo_is_consumed_after_next_round():
    players = [
        PlayerState(
            player_id=1,
            color=Color.BLUE,
            lives=12,
            active_animal_effects=[PANDA_GRANDE_LETARGO],
        ),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 2),
        2: Card(Color.BLUE, 1),
    }

    result = resolve_round(players, selected_cards, _animal_config())

    assert result.lowest_value == 1
    assert result.base_damage_by_player[1] == 2
    assert players[0].active_animal_effects == []


def test_grande_letargo_does_not_apply_twice():
    players = [
        PlayerState(
            player_id=1,
            color=Color.BLUE,
            lives=12,
            active_animal_effects=[PANDA_GRANDE_LETARGO],
        ),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]

    first_result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )
    second_result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 2),
            2: Card(Color.RED, 4),
        },
        _animal_config(),
    )

    assert first_result.lowest_value == 1
    assert second_result.lowest_value == 2
    assert second_result.critical_wound_players == [1]
    assert players[0].active_animal_effects == []


def test_grande_letargo_does_not_modify_consumption_in_round_resolution():
    players = [
        PlayerState(
            player_id=1,
            color=Color.BLUE,
            lives=12,
            active_animal_effects=[PANDA_GRANDE_LETARGO],
        ),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.BLUE, 5),
            2: Card(Color.RED, 1),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 5
    assert players[0].lives == 7


def test_grande_letargo_active_keeps_respiro_lento_consumption_reduction():
    player = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        active_animal_effects=[PANDA_GRANDE_LETARGO],
    )
    card = Card(Color.BLUE, 3)

    assert get_effective_comparison_value(player, card, _animal_config()) == 3
    assert get_effective_consumption_value(player, card, _animal_config()) == 2


def test_grande_letargo_is_inactive_when_other_animals_play_panda_five():
    for color in (Color.RED, Color.GREEN, Color.YELLOW):
        players = [
            PlayerState(player_id=1, color=color, lives=12),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
        ]
        selected_cards = {
            1: Card(Color.BLUE, 5),
            2: Card(Color.RED, 1),
        }

        resolve_round(players, selected_cards, _animal_config())

        assert players[0].active_animal_effects == []


def test_grande_letargo_is_inactive_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    selected_cards = {
        1: Card(Color.BLUE, 5),
        2: Card(Color.RED, 1),
    }

    resolve_round(players, selected_cards, GameConfig(color_effects_enabled=False))

    assert players[0].active_animal_effects == []


def test_coniglio_effects_continue_to_use_their_effective_values():
    coniglio = PlayerState(player_id=1, color=Color.RED, lives=12)

    assert get_effective_comparison_value(
        coniglio,
        Card(Color.RED, 1),
        _animal_config(),
    ) == 2
    assert get_effective_consumption_value(
        coniglio,
        Card(Color.RED, 2),
        _animal_config(),
    ) == 1
    assert get_effective_comparison_value(
        coniglio,
        Card(Color.RED, 4),
        _animal_config(),
    ) == 5


def test_panda_one_and_inactive_panda_five_keep_standard_values():
    player = PlayerState(player_id=1, color=Color.BLUE, lives=12)

    assert get_effective_consumption_value(
        player,
        Card(Color.BLUE, 1),
        _animal_config(),
    ) == 1
    assert get_effective_comparison_value(
        player,
        Card(Color.BLUE, 1),
        _animal_config(),
    ) == 1
    assert get_effective_consumption_value(
        player,
        Card(Color.BLUE, 5),
        _animal_config(),
    ) == 5
    assert get_effective_comparison_value(
        player,
        Card(Color.BLUE, 5),
        _animal_config(),
    ) == 5


def test_scimmia_and_scoiattolo_effect_cards_keep_standard_values_for_now():
    cases = (
        (Color.GREEN, 1),
        (Color.GREEN, 2),
        (Color.GREEN, 5),
        (Color.YELLOW, 1),
        (Color.YELLOW, 3),
        (Color.YELLOW, 4),
    )

    for color, value in cases:
        player = PlayerState(player_id=1, color=color, lives=12)
        card = Card(color, value)

        assert get_effective_consumption_value(player, card, _animal_config()) == value
        assert get_effective_comparison_value(player, card, _animal_config()) == value


def test_runtime_standard_result_does_not_change_without_animal_effect_flag_for_panda_three():
    selected_cards = {
        1: Card(Color.BLUE, 3),
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
        [
            PlayerState(player_id=1, color=Color.BLUE, lives=12),
            PlayerState(player_id=2, color=Color.RED, lives=12),
        ],
        selected_cards,
        replace(
            get_v05_config_for_players(2),
            critical_card_effects_enabled=False,
            animal_card_effects_enabled=False,
        ),
    )

    assert v05_without_animals.critical_wound_players == baseline.critical_wound_players
    assert v05_without_animals.base_damage_by_player == baseline.base_damage_by_player
    assert v05_without_animals.lowest_value == baseline.lowest_value


def test_runtime_standard_result_does_not_recover_panda_one_without_animal_effect_flag():
    selected_cards = {
        1: Card(Color.BLUE, 1),
        2: Card(Color.RED, 2),
    }

    baseline_players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    v05_players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]

    baseline = resolve_round(
        baseline_players,
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )
    v05_without_animals = resolve_round(
        v05_players,
        selected_cards,
        replace(
            get_v05_config_for_players(2),
            critical_card_effects_enabled=False,
            animal_card_effects_enabled=False,
        ),
    )

    assert v05_without_animals.critical_wound_players == baseline.critical_wound_players
    assert v05_without_animals.base_damage_by_player == baseline.base_damage_by_player
    assert v05_without_animals.lowest_value == baseline.lowest_value
    assert v05_players[0].lives == baseline_players[0].lives == 10


def test_game_config_legacy_disables_and_v05_presets_enable_animal_effects():
    assert GameConfig().animal_card_effects_enabled is False
    assert get_v05_config_for_players(2).animal_card_effects_enabled is True
    assert get_v05_config_for_players(3).animal_card_effects_enabled is True
    assert get_v05_config_for_players(4).animal_card_effects_enabled is True
