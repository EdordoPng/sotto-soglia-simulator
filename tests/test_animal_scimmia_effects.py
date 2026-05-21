from dataclasses import replace
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.animal_effects import PANDA_GRANDE_LETARGO
from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import RESPIRO_CALMO, V05_HUNGER_DECK_PROFILE_ID
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


def test_buccia_di_banana_reduces_lowest_valid_target_comparison_by_one():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.YELLOW, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 3),
            3: Card(Color.RED, 4),
        },
        _animal_config(),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 2]


def test_buccia_di_banana_does_not_reduce_below_one():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 1),
        },
        _animal_config(),
    )

    assert result.lowest_value == 1
    assert result.critical_wound_players == [2]


def test_buccia_di_banana_does_not_change_target_consumption():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.YELLOW, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 4),
            3: Card(Color.RED, 1),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [3]
    assert players[0].critical_wounds == 0
    assert players[1].critical_wounds == 0
    assert players[2].critical_wounds == 1
    assert result.base_damage_by_player[2] == 4
    assert players[1].lives == 8


def test_buccia_di_banana_does_not_change_static_card_values():
    source = PlayerState(player_id=1, color=Color.GREEN, lives=12)
    target_card = Card(Color.BLUE, 4)

    resolve_round(
        [
            source,
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
            PlayerState(player_id=3, color=Color.RED, lives=12),
        ],
        {
            1: Card(Color.GREEN, 2),
            2: target_card,
            3: Card(Color.RED, 1),
        },
        _animal_config(),
    )

    assert target_card.value == 4
    assert target_card.comparison_value == 4
    assert target_card.consumption_value == 4


def test_buccia_di_banana_is_inactive_when_animal_effects_are_disabled():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 3),
            3: Card(Color.RED, 4),
        },
        GameConfig(color_effects_enabled=False),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1]


def test_buccia_di_banana_is_inactive_when_other_animals_play_scimmia_two():
    for color in (Color.BLUE, Color.RED, Color.YELLOW):
        players = [
            PlayerState(player_id=1, color=color, lives=12),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
            PlayerState(player_id=3, color=Color.RED, lives=12),
        ]

        result = resolve_round(
            players,
            {
                1: Card(Color.GREEN, 2),
                2: Card(Color.BLUE, 3),
                3: Card(Color.RED, 4),
            },
            _animal_config(),
        )

        assert result.lowest_value == 2
        assert result.critical_wound_players == [1]


def test_buccia_di_banana_cannot_target_source_player():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.RED, 5),
        },
        _animal_config(),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1]


def test_buccia_di_banana_ignores_players_without_revealed_card():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            3: Card(Color.RED, 3),
        },
        _animal_config(),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 3]


def test_buccia_di_banana_ignores_eliminated_players_as_targets():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12, is_alive=False),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 3),
            3: Card(Color.RED, 3),
        },
        _animal_config(),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 3]


def test_buccia_di_banana_can_target_player_who_will_receive_affamato():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 2),
            3: Card(Color.RED, 3),
        },
        _animal_config(),
    )

    assert result.lowest_value == 1
    assert result.critical_wound_players == [2]


def test_buccia_di_banana_respiro_calmo_blocks_reduction_without_retargeting():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(
            player_id=2,
            color=Color.BLUE,
            lives=12,
            active_critical_effects=[RESPIRO_CALMO],
        ),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]
    config = _animal_config(
        critical_card_effects_enabled=True,
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 2),
            3: Card(Color.RED, 2),
        },
        config,
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 2, 3]
    assert players[1].critical_wounds == 1


def test_buccia_di_banana_reduces_grande_letargo_target_from_three_to_two():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(
            player_id=2,
            color=Color.BLUE,
            lives=12,
            active_animal_effects=[PANDA_GRANDE_LETARGO],
        ),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 5),
            3: Card(Color.RED, 4),
        },
        _animal_config(),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1, 2]


def test_buccia_di_banana_grande_letargo_target_with_respiro_calmo_stays_three():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(
            player_id=2,
            color=Color.BLUE,
            lives=12,
            active_animal_effects=[PANDA_GRANDE_LETARGO],
            active_critical_effects=[RESPIRO_CALMO],
        ),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]
    config = _animal_config(
        critical_card_effects_enabled=True,
        critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
    )

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 5),
            3: Card(Color.RED, 4),
        },
        config,
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1]
    assert players[1].critical_wounds == 0


def test_buccia_di_banana_can_change_affamato_assignment():
    players = [
        PlayerState(player_id=1, color=Color.GREEN, lives=12),
        PlayerState(player_id=2, color=Color.BLUE, lives=12),
        PlayerState(player_id=3, color=Color.RED, lives=12),
    ]

    result = resolve_round(
        players,
        {
            1: Card(Color.GREEN, 2),
            2: Card(Color.BLUE, 2),
            3: Card(Color.RED, 3),
        },
        _animal_config(),
    )

    assert result.critical_wound_players == [2]
    assert players[1].critical_wounds == 1


def test_buccia_di_banana_no_valid_targets_does_not_error():
    players = [PlayerState(player_id=1, color=Color.GREEN, lives=12)]

    result = resolve_round(
        players,
        {1: Card(Color.GREEN, 2)},
        _animal_config(),
    )

    assert result.lowest_value == 2
    assert result.critical_wound_players == [1]


def test_coniglio_effects_continue_to_work_with_scimmia_effects_enabled():
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


def test_panda_effects_continue_to_work_with_scimmia_effects_enabled():
    panda = PlayerState(player_id=1, color=Color.BLUE, lives=12)
    sleeping_panda = PlayerState(
        player_id=1,
        color=Color.BLUE,
        lives=12,
        active_animal_effects=[PANDA_GRANDE_LETARGO],
    )

    assert get_effective_consumption_value(
        panda,
        Card(Color.BLUE, 3),
        _animal_config(),
    ) == 2
    assert get_effective_comparison_value(
        sleeping_panda,
        Card(Color.RED, 4),
        _animal_config(),
    ) == 3

    players = [
        PlayerState(player_id=1, color=Color.BLUE, lives=10),
        PlayerState(player_id=2, color=Color.RED, lives=12),
    ]
    resolve_round(
        players,
        {
            1: Card(Color.BLUE, 1),
            2: Card(Color.RED, 2),
        },
        _animal_config(),
    )

    assert players[0].lives == 11


def test_other_scimmia_effect_cards_keep_standard_values_for_now():
    scimmia = PlayerState(player_id=1, color=Color.GREEN, lives=12)

    assert get_effective_comparison_value(
        scimmia,
        Card(Color.GREEN, 1),
        _animal_config(),
    ) == 1
    assert get_effective_consumption_value(
        scimmia,
        Card(Color.GREEN, 1),
        _animal_config(),
    ) == 1
    assert get_effective_comparison_value(
        scimmia,
        Card(Color.GREEN, 5),
        _animal_config(),
    ) == 5
    assert get_effective_consumption_value(
        scimmia,
        Card(Color.GREEN, 5),
        _animal_config(),
    ) == 5


def test_scoiattolo_effect_cards_keep_standard_values_for_now():
    for value in (1, 3, 4):
        scoiattolo = PlayerState(player_id=1, color=Color.YELLOW, lives=12)
        card = Card(Color.YELLOW, value)

        assert (
            get_effective_comparison_value(scoiattolo, card, _animal_config())
            == value
        )
        assert (
            get_effective_consumption_value(scoiattolo, card, _animal_config())
            == value
        )


def test_runtime_standard_result_does_not_change_without_animal_effect_flag_for_scimmia_two():
    selected_cards = {
        1: Card(Color.GREEN, 2),
        2: Card(Color.BLUE, 3),
        3: Card(Color.RED, 4),
    }

    baseline = resolve_round(
        [
            PlayerState(player_id=1, color=Color.GREEN, lives=12),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
            PlayerState(player_id=3, color=Color.RED, lives=12),
        ],
        selected_cards,
        GameConfig(color_effects_enabled=False),
    )
    v05_without_animals = resolve_round(
        [
            PlayerState(player_id=1, color=Color.GREEN, lives=12),
            PlayerState(player_id=2, color=Color.BLUE, lives=12),
            PlayerState(player_id=3, color=Color.RED, lives=12),
        ],
        selected_cards,
        replace(get_v05_config_for_players(3), critical_card_effects_enabled=False),
    )

    assert v05_without_animals.critical_wound_players == baseline.critical_wound_players
    assert v05_without_animals.base_damage_by_player == baseline.base_damage_by_player
    assert v05_without_animals.lowest_value == baseline.lowest_value


def test_game_config_and_v05_presets_keep_animal_effects_disabled():
    assert GameConfig().animal_card_effects_enabled is False
    assert get_v05_config_for_players(2).animal_card_effects_enabled is False
    assert get_v05_config_for_players(3).animal_card_effects_enabled is False
    assert get_v05_config_for_players(4).animal_card_effects_enabled is False
