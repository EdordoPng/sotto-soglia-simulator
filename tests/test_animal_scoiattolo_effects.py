from pathlib import Path
from random import Random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.animal_effects import (
    PANDA_GRANDE_LETARGO,
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
            1: Card(Color.YELLOW, 4),
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


def test_piccola_riserva_and_dispensa_ordinata_are_not_implemented_yet():
    players = [
        PlayerState(player_id=1, color=Color.YELLOW, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 3),
            2: Card(Color.BLUE, 2),
        },
        _animal_config(),
    )
    resolve_round(
        players,
        {
            1: Card(Color.YELLOW, 4),
            2: Card(Color.BLUE, 2),
        },
        _animal_config(),
    )

    assert players[0].active_animal_effects == []
    assert (
        get_effective_consumption_value(
            players[0],
            Card(Color.YELLOW, 3),
            _animal_config(),
        )
        == 3
    )
    assert (
        get_effective_comparison_value(
            players[0],
            Card(Color.YELLOW, 4),
            _animal_config(),
        )
        == 4
    )


def test_standard_runtime_does_not_change_when_animal_effects_are_disabled():
    players = [
        PlayerState(
            player_id=1,
            color=Color.YELLOW,
            lives=12,
            active_animal_effects=[SCOIATTOLO_GHIANDA_NASCOSTA],
        )
    ]

    hand_sizes, events = _hand_sizes_from_critical_effects(
        players,
        GameConfig(),
        {},
        game_id=1,
        round_number=2,
        active_animal_effects_by_player={1: [SCOIATTOLO_GHIANDA_NASCOSTA]},
    )

    assert hand_sizes == {}
    assert events == []
    assert GameConfig().animal_card_effects_enabled is False
    assert get_v05_config_for_players(4).animal_card_effects_enabled is False
