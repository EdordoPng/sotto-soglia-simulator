from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.animal_effects import (
    ANIMAL_CARD_EFFECTS,
    ANIMAL_BY_COLOR,
    ANIMAL_DISPLAY_COLORS,
    COLOR_BY_ANIMAL as TECHNICAL_COLOR_BY_ANIMAL,
    Animal,
    get_display_color_for_animal,
    get_display_color_for_technical_color,
    get_animal_card_effect,
    get_animal_card_profile,
    get_effect_id_for_card,
    has_animal_card_effect,
    is_own_animal_card_effect_active,
)
from sotto_soglia.deck import build_deck
from sotto_soglia.models import Card, Color, PlayerState


CARD_VALUES = (1, 2, 3, 4, 5)

COLOR_BY_ANIMAL = {
    animal: color
    for color, animal in ANIMAL_BY_COLOR.items()
}

EXPECTED_EFFECTS = {
    (Animal.PANDA, 1): ("panda_riposo_forzato", "Riposo Forzato"),
    (Animal.PANDA, 3): ("panda_respiro_lento", "Respiro Lento"),
    (Animal.PANDA, 5): ("panda_grande_letargo", "Grande Letargo"),
    (Animal.CONIGLIO, 1): ("coniglio_scatto_improvviso", "Scatto Improvviso"),
    (Animal.CONIGLIO, 2): ("coniglio_passo_leggero", "Passo Leggero"),
    (Animal.CONIGLIO, 4): ("coniglio_grande_balzo", "Grande Balzo"),
    (Animal.SCIMMIA, 1): ("scimmia_finta_innocente", "Finta Innocente"),
    (Animal.SCIMMIA, 2): ("scimmia_buccia_di_banana", "Buccia di Banana"),
    (Animal.SCIMMIA, 5): ("scimmia_banana_rubata", "Banana Rubata"),
    (Animal.SCOIATTOLO, 1): ("scoiattolo_ghianda_nascosta", "Ghianda Nascosta"),
    (Animal.SCOIATTOLO, 3): ("scoiattolo_piccola_riserva", "Piccola Riserva"),
    (Animal.SCOIATTOLO, 4): ("scoiattolo_dispensa_ordinata", "Dispensa Ordinata"),
}

EXPECTED_NO_EFFECT = {
    (Animal.PANDA, 2),
    (Animal.PANDA, 4),
    (Animal.CONIGLIO, 3),
    (Animal.CONIGLIO, 5),
    (Animal.SCIMMIA, 3),
    (Animal.SCIMMIA, 4),
    (Animal.SCOIATTOLO, 2),
    (Animal.SCOIATTOLO, 5),
}


EXPECTED_TECHNICAL_ANIMAL_BY_COLOR = {
    Color.BLUE: Animal.PANDA,
    Color.RED: Animal.CONIGLIO,
    Color.GREEN: Animal.SCIMMIA,
    Color.YELLOW: Animal.SCOIATTOLO,
}

EXPECTED_TECHNICAL_COLOR_BY_ANIMAL = {
    Animal.PANDA: Color.BLUE,
    Animal.CONIGLIO: Color.RED,
    Animal.SCIMMIA: Color.GREEN,
    Animal.SCOIATTOLO: Color.YELLOW,
}

EXPECTED_DISPLAY_COLORS_BY_ANIMAL = {
    Animal.PANDA: "green",
    Animal.SCIMMIA: "yellow",
    Animal.CONIGLIO: "orange",
    Animal.SCOIATTOLO: "brown",
}

EXPECTED_DISPLAY_COLORS_BY_TECHNICAL_COLOR = {
    Color.BLUE: "green",
    Color.GREEN: "yellow",
    Color.RED: "orange",
    Color.YELLOW: "brown",
}


def _card(animal: Animal, value: int) -> Card:
    return Card(COLOR_BY_ANIMAL[animal], value)


def _player(animal: Animal) -> PlayerState:
    return PlayerState(
        player_id=1,
        color=COLOR_BY_ANIMAL[animal],
        lives=12,
    )


def test_display_color_mapping_by_animal():
    assert ANIMAL_DISPLAY_COLORS == EXPECTED_DISPLAY_COLORS_BY_ANIMAL

    for animal, display_color in EXPECTED_DISPLAY_COLORS_BY_ANIMAL.items():
        assert get_display_color_for_animal(animal) == display_color


def test_display_color_mapping_by_technical_color():
    for color, display_color in EXPECTED_DISPLAY_COLORS_BY_TECHNICAL_COLOR.items():
        assert get_display_color_for_technical_color(color) == display_color


def test_technical_animal_mapping_remains_unchanged():
    assert ANIMAL_BY_COLOR == EXPECTED_TECHNICAL_ANIMAL_BY_COLOR


def test_technical_color_by_animal_mapping_remains_unchanged():
    assert TECHNICAL_COLOR_BY_ANIMAL == EXPECTED_TECHNICAL_COLOR_BY_ANIMAL


def test_display_color_mapping_does_not_change_effect_recognition():
    assert get_effect_id_for_card(Card(Color.BLUE, 1)) == "panda_riposo_forzato"
    assert get_display_color_for_technical_color(Color.BLUE) == "green"


def test_all_twenty_animal_cards_are_represented():
    assert set(ANIMAL_CARD_EFFECTS) == {
        (animal, value)
        for animal in Animal
        for value in CARD_VALUES
    }

    for animal in Animal:
        for value in CARD_VALUES:
            profile = get_animal_card_profile(_card(animal, value))

            assert profile is not None
            assert profile.animal == animal
            assert profile.printed_value == value


def test_effect_cards_are_recognized():
    assert {
        key
        for key, profile in ANIMAL_CARD_EFFECTS.items()
        if profile.has_effect
    } == set(EXPECTED_EFFECTS)

    for animal, value in EXPECTED_EFFECTS:
        assert has_animal_card_effect(_card(animal, value)) is True


def test_cards_without_effect_are_recognized():
    assert {
        key
        for key, profile in ANIMAL_CARD_EFFECTS.items()
        if not profile.has_effect
    } == EXPECTED_NO_EFFECT

    for animal, value in EXPECTED_NO_EFFECT:
        card = _card(animal, value)

        assert has_animal_card_effect(card) is False
        assert get_animal_card_effect(card) is None
        assert get_effect_id_for_card(card) is None


def test_each_effect_card_returns_expected_id_and_name():
    for (animal, value), (effect_id, effect_name) in EXPECTED_EFFECTS.items():
        card = _card(animal, value)
        effect = get_animal_card_effect(card)

        assert effect is not None
        assert effect.effect_id == effect_id
        assert effect.effect_name == effect_name
        assert get_effect_id_for_card(card) == effect_id


def test_animal_card_effect_is_active_only_for_own_animal():
    for animal, value in EXPECTED_EFFECTS:
        card = _card(animal, value)

        assert is_own_animal_card_effect_active(_player(animal), card) is True


def test_animal_card_effect_is_not_active_for_other_animal():
    for animal, value in EXPECTED_EFFECTS:
        card = _card(animal, value)
        other_animal = next(candidate for candidate in Animal if candidate != animal)

        assert is_own_animal_card_effect_active(_player(other_animal), card) is False


def test_animal_card_without_effect_is_not_active_for_own_animal():
    for animal, value in EXPECTED_NO_EFFECT:
        card = _card(animal, value)

        assert is_own_animal_card_effect_active(_player(animal), card) is False


def test_standard_deck_still_has_five_cards_per_animal_color():
    deck = build_deck(list(Color), CARD_VALUES)

    values_by_color = {
        color: {card.value for card in deck if card.color == color}
        for color in Color
    }

    assert len(deck) == 20
    assert values_by_color == {color: set(CARD_VALUES) for color in Color}


def test_standard_deck_cards_keep_printed_and_resolved_values():
    deck = build_deck(list(Color), CARD_VALUES)

    assert all(card.value in CARD_VALUES for card in deck)
    assert all(card.custom_consumption_value is None for card in deck)
    assert all(card.custom_comparison_value is None for card in deck)
    assert all(card.consumption_value == card.value for card in deck)
    assert all(card.comparison_value == card.value for card in deck)
