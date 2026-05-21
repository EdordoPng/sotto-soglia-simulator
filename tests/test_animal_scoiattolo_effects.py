from pathlib import Path
from random import Random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.animal_effects import (
    PANDA_GRANDE_LETARGO,
    SCOIATTOLO_DISPENSA_ORDINATA,
    SCOIATTOLO_GHIANDA_NASCOSTA,
)
from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import (
    FIUTO_DA_DISPENSA,
    PANCIA_BRONTOLANTE,
    V05_HUNGER_DECK_PROFILE_ID,
)
from sotto_soglia.game import _deal_hands, _hand_sizes_from_critical_effects
from sotto_soglia.models import Card, Color, PlayerState
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


def _animal_hunger_config(**overrides) -> GameConfig:
    values = {
        "initial_lives": 12,
        "critical_wounds_limit": 5,
        "color_effects_enabled": False,
        "critical_card_effects_enabled": True,
        "animal_card_effects_enabled": True,
        "critical_deck_profile_id": V05_HUNGER_DECK_PROFILE_ID,
    }
    values.update(overrides)
    return GameConfig(**values)


def test_ghianda_nascosta_registers_next_round_without_current_hand_change():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 1),
            2: Card(Color.BLUE, 2),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0
    assert players[0].active_animal_effects == [SCOIATTOLO_GHIANDA_NASCOSTA]
    assert len(result.animal_events) == 1
    event = result.animal_events[0]
    assert event.effect_id == SCOIATTOLO_GHIANDA_NASCOSTA
    assert event.effect_name == "Ghianda Nascosta"
    assert event.timing == "next_round_schedule"
    assert event.status == "scheduled"
    assert event.amount == 1

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=1,
        active_animal_effects_by_player={},
    )
    assert hand_sizes == {}
    assert events == []


def test_ghianda_nascosta_registers_even_when_scoiattolo_receives_affamato():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 1),
            2: Card(Color.BLUE, 2),
        },
        _animal_config(),
    )

    assert 1 in result.critical_wound_players
    assert players[0].critical_wounds == 1
    assert players[0].active_animal_effects == [SCOIATTOLO_GHIANDA_NASCOSTA]


def test_ghianda_nascosta_deals_four_cards_next_round():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_GHIANDA_NASCOSTA],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_GHIANDA_NASCOSTA]},
    )
    hands = _deal_hands(players, Random(1), _animal_config(), hand_sizes)

    assert hand_sizes == {1: 4}
    assert len(hands[1]) == 4
    assert len(hands[2]) == 3
    assert events == []


def test_ghianda_nascosta_is_consumed_after_next_round():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_GHIANDA_NASCOSTA],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]
    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )
    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=3,
        active_animal_effects_by_player={},
    )

    assert players[0].active_animal_effects == []
    assert hand_sizes == {}
    assert events == []


def test_ghianda_nascosta_does_not_apply_twice():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_GHIANDA_NASCOSTA],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    first_hand_sizes, _ = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_GHIANDA_NASCOSTA]},
    )
    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )
    second_hand_sizes, _ = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=3,
        active_animal_effects_by_player={},
    )

    assert first_hand_sizes == {1: 4}
    assert second_hand_sizes == {}


def test_ghianda_nascosta_keeps_values_consumption_and_affamato_assignment():
    scoiattolo = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    card = Card(Color.YELLOW, 1)

    result = resolve_round(
        [scoiattolo, PlayerState(player_id=2, color=Color.BLUE, lives=12)],
        {
            1: card,
            2: Card(Color.BLUE, 2),
        },
        _animal_config(),
    )

    assert card.value == 1
    assert card.comparison_value == 1
    assert card.consumption_value == 1
    assert get_effective_comparison_value(scoiattolo, card, _animal_config()) == 1
    assert get_effective_consumption_value(scoiattolo, card, _animal_config()) == 1
    assert result.lowest_value == 1
    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0


def test_ghianda_nascosta_is_inactive_when_other_animals_play_scoiattolo_one():
    for color in (Color.BLUE, Color.RED, Color.GREEN):
        players = [
            PlayerState(player_id=1, color=color, lives=12),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
        ]

        resolve_round(
            players,
            {
                1: Card(Color.YELLOW, 1),
                2: Card(Color.BLUE, 2),
            },
            _animal_config(),
        )

        assert players[0].active_animal_effects == []


def test_ghianda_nascosta_is_inactive_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 1),
            2: Card(Color.BLUE, 2),
        },
        GameConfig(color_effects_enabled=False),
    )

    assert players[0].active_animal_effects == []


def test_ghianda_nascosta_and_fiuto_da_dispensa_clamp_to_four_cards():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_critical_effects=[FIUTO_DA_DISPENSA],
            active_animal_effects=[SCOIATTOLO_GHIANDA_NASCOSTA],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_hunger_config(),
        {1: [FIUTO_DA_DISPENSA]},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_GHIANDA_NASCOSTA]},
    )

    assert hand_sizes == {1: 4}
    assert [event.critical_card_id for event in events] == [FIUTO_DA_DISPENSA]


def test_ghianda_nascosta_and_pancia_brontolante_cancel_to_three_cards():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_critical_effects=[PANCIA_BRONTOLANTE],
            active_animal_effects=[SCOIATTOLO_GHIANDA_NASCOSTA],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_hunger_config(),
        {1: [PANCIA_BRONTOLANTE]},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_GHIANDA_NASCOSTA]},
    )

    assert hand_sizes == {1: 3}
    assert [event.critical_card_id for event in events] == [PANCIA_BRONTOLANTE]


def test_piccola_riserva_recovers_one_in_recovery_phase_when_not_affamato():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=10),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [2]
    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 8


def test_piccola_riserva_does_not_recover_before_recovery_phase(monkeypatch):
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=10),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]
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

    round_module.resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.RED, 1),
        },
        _animal_config(),
    )

    assert pending_seen_at_recovery == {1: 1}
    assert lives_seen_before_recovery[1] == 7
    assert players[0].lives == 8


def test_piccola_riserva_does_not_exceed_initial_lives():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 10


def test_piccola_riserva_does_not_activate_when_scoiattolo_receives_affamato():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=10),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 4),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0
    assert players[0].lives == 10


def test_piccola_riserva_is_inactive_when_other_animals_play_scoiattolo_three():
    for color in (Color.BLUE, Color.RED, Color.GREEN):
        players = [
            PlayerState(player_id=1, color=color, lives=10),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
        ]

        result = resolve_round(
            players,
            {
                1: Card(Color.YELLOW, 3),
                2: Card(Color.BLUE, 1),
            },
            _animal_config(),
        )

        assert result.base_damage_by_player[1] == 3
        assert players[0].lives == 7


def test_piccola_riserva_is_inactive_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=10),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 1),
        },
        GameConfig(color_effects_enabled=False),
    )

    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 7


def test_piccola_riserva_keeps_card_values_and_effective_comparison_unchanged():
    scoiattolo = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    card = Card(Color.YELLOW, 3)

    assert card.value == 3
    assert card.comparison_value == 3
    assert card.consumption_value == 3
    assert get_effective_comparison_value(scoiattolo, card, _animal_config()) == 3
    assert get_effective_consumption_value(scoiattolo, card, _animal_config()) == 3


def test_piccola_riserva_does_not_modify_base_consumption():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=10),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.base_damage_by_player[1] == 3
    assert result.total_damage_by_player[1] == 3
    assert players[0].lives == 8


def test_piccola_riserva_can_recover_from_zero_before_lives_elimination():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=3),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.base_damage_by_player[1] == 3
    assert players[0].lives == 1
    assert players[0].is_alive is True
    assert result.eliminated_players == []


def test_existing_scimmia_effects_still_work():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    finta = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 1),
            2: Card(Color.BLUE, 1),
            3: Card(Color.RED, 3),
        },
        _animal_config(),
    )
    assert finta.critical_wound_players == [2]

    buccia = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 3),
            3: Card(Color.RED, 4),
        },
        _animal_config(),
    )
    assert buccia.critical_wound_players == [1, 2]

    banana = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 5),
            2: Card(Color.BLUE, 1),
            3: Card(Color.RED, 4),
        },
        _animal_config(),
    )
    assert banana.extra_damage_by_player[3] == 1


def test_existing_panda_effects_still_work():
    panda = PlayerState(player_id=1, color=Color.BLUE, lives=10)
    riposo = resolve_round(
        [panda, PlayerState(player_id=2, color=Color.RED, lives=12)],
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 2),
        },
        _animal_config(),
    )

    assert riposo.critical_wound_players == [1]
    assert panda.lives == 11
    assert get_effective_consumption_value(
        PlayerState(player_id=1, color=Color.BLUE, lives=12),
        Card(Color.BLUE, 3),
        _animal_config(),
    ) == 2
    assert get_effective_comparison_value(
        PlayerState(
            player_id=1,
            color=Color.BLUE,
            lives=12,
            active_animal_effects=[PANDA_GRANDE_LETARGO],
        ),
        Card(Color.RED, 4),
        _animal_config(),
    ) == 3


def test_existing_coniglio_effects_still_work():
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


def test_dispensa_ordinata_registers_next_round_when_not_affamato():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [2]
    assert players[0].active_animal_effects == [SCOIATTOLO_DISPENSA_ORDINATA]
    dispensa_events = [
        event
        for event in result.animal_events
        if event.effect_id == SCOIATTOLO_DISPENSA_ORDINATA
    ]
    assert len(dispensa_events) == 1
    event = dispensa_events[0]
    assert event.effect_id == SCOIATTOLO_DISPENSA_ORDINATA
    assert event.effect_name == "Dispensa Ordinata"
    assert event.timing == "next_round_schedule"
    assert event.status == "scheduled"
    assert event.player_id == 1
    assert event.card_color == "YELLOW"
    assert event.card_value == 4
    assert event.amount == 1


def test_dispensa_ordinata_does_not_register_when_scoiattolo_receives_affamato():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 4),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [1, 2]
    assert result.base_damage_by_player[1] == 0
    assert players[0].active_animal_effects == []
    assert result.animal_events == []


def test_dispensa_ordinata_does_not_change_current_round_hand():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )
    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=1,
        active_animal_effects_by_player={},
    )

    assert players[0].active_animal_effects == [SCOIATTOLO_DISPENSA_ORDINATA]
    assert hand_sizes == {}
    assert events == []


def test_dispensa_ordinata_deals_four_cards_next_round():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_DISPENSA_ORDINATA],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_DISPENSA_ORDINATA]},
    )
    hands = _deal_hands(players, Random(1), _animal_config(), hand_sizes)

    assert hand_sizes == {1: 4}
    assert len(hands[1]) == 4
    assert len(hands[2]) == 3
    assert events == []


def test_dispensa_ordinata_is_consumed_after_next_round():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_DISPENSA_ORDINATA],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert players[0].active_animal_effects == []


def test_dispensa_ordinata_does_not_apply_twice():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_DISPENSA_ORDINATA],
        ),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    first_hand_sizes, _ = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_DISPENSA_ORDINATA]},
    )
    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )
    second_hand_sizes, _ = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=3,
        active_animal_effects_by_player={},
    )

    assert first_hand_sizes == {1: 4}
    assert second_hand_sizes == {}


def test_dispensa_ordinata_keeps_values_consumption_and_affamato_assignment():
    scoiattolo = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
    card = Card(Color.YELLOW, 4)

    result = resolve_round(
        [scoiattolo, PlayerState(player_id=2, color=Color.BLUE, lives=12)],
        {
            1: card,
            2: Card(Color.BLUE, 5),
        },
        _animal_config(),
    )

    assert card.value == 4
    assert card.comparison_value == 4
    assert card.consumption_value == 4
    assert (
        get_effective_comparison_value(
            scoiattolo,
            card,
            _animal_config(),
        )
        == 4
    )
    assert get_effective_consumption_value(scoiattolo, card, _animal_config()) == 4
    assert result.lowest_value == 4
    assert result.critical_wound_players == [1]
    assert result.base_damage_by_player[1] == 0
    assert scoiattolo.active_animal_effects == []


def test_dispensa_ordinata_is_inactive_when_other_animals_play_scoiattolo_four():
    for color in (Color.BLUE, Color.RED, Color.GREEN):
        players = [
            PlayerState(player_id=1, color=color, lives=12),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
        ]

        result = resolve_round(
            players,
            {
                1: Card(Color.YELLOW, 4),
                2: Card(Color.BLUE, 1),
            },
            _animal_config(),
        )

        assert result.base_damage_by_player[1] == 4
        assert players[0].active_animal_effects == []


def test_dispensa_ordinata_is_inactive_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 1),
        },
        GameConfig(color_effects_enabled=False),
    )

    assert result.base_damage_by_player[1] == 4
    assert players[0].active_animal_effects == []


def test_dispensa_ordinata_and_ghianda_nascosta_clamp_to_four_cards():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[
                SCOIATTOLO_DISPENSA_ORDINATA,
                SCOIATTOLO_GHIANDA_NASCOSTA,
            ],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_config(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={
            1: [SCOIATTOLO_DISPENSA_ORDINATA, SCOIATTOLO_GHIANDA_NASCOSTA]
        },
    )

    assert hand_sizes == {1: 4}
    assert events == []


def test_dispensa_ordinata_and_fiuto_da_dispensa_clamp_to_four_cards():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_critical_effects=[FIUTO_DA_DISPENSA],
            active_animal_effects=[SCOIATTOLO_DISPENSA_ORDINATA],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_hunger_config(),
        {1: [FIUTO_DA_DISPENSA]},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_DISPENSA_ORDINATA]},
    )

    assert hand_sizes == {1: 4}
    assert [event.critical_card_id for event in events] == [FIUTO_DA_DISPENSA]


def test_dispensa_ordinata_and_pancia_brontolante_cancel_to_three_cards():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_critical_effects=[PANCIA_BRONTOLANTE],
            active_animal_effects=[SCOIATTOLO_DISPENSA_ORDINATA],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        _animal_hunger_config(),
        {1: [PANCIA_BRONTOLANTE]},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_DISPENSA_ORDINATA]},
    )

    assert hand_sizes == {1: 3}
    assert [event.critical_card_id for event in events] == [PANCIA_BRONTOLANTE]


def test_standard_runtime_does_not_change_when_animal_effects_are_disabled():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[
                SCOIATTOLO_GHIANDA_NASCOSTA,
                SCOIATTOLO_DISPENSA_ORDINATA,
            ],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        GameConfig(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={
            1: [SCOIATTOLO_GHIANDA_NASCOSTA, SCOIATTOLO_DISPENSA_ORDINATA]
        },
    )

    assert hand_sizes == {}
    assert events == []
    assert GameConfig().animal_card_effects_enabled is False
    assert get_v05_config_for_players(4).animal_card_effects_enabled is True
