from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.deck import build_deck
from sotto_soglia.models import Color


CARD_VALUES = (1, 2, 3, 4, 5)


def test_build_deck_with_two_colors_has_ten_cards():
    deck = build_deck([Color.BLUE, Color.RED], CARD_VALUES)

    assert len(deck) == 10


def test_build_deck_with_three_colors_has_fifteen_cards():
    deck = build_deck([Color.BLUE, Color.RED, Color.GREEN], CARD_VALUES)

    assert len(deck) == 15


def test_build_deck_with_four_colors_has_twenty_cards():
    deck = build_deck(list(Color), CARD_VALUES)

    assert len(deck) == 20


def test_each_color_has_all_values():
    colors = [Color.BLUE, Color.RED, Color.GREEN, Color.YELLOW]
    deck = build_deck(colors, CARD_VALUES)

    values_by_color = {
        color: {card.value for card in deck if card.color == color}
        for color in colors
    }

    assert values_by_color == {color: set(CARD_VALUES) for color in colors}


def test_standard_deck_cards_use_printed_values_without_overrides():
    deck = build_deck([Color.BLUE, Color.RED], CARD_VALUES)

    assert all(card.custom_consumption_value is None for card in deck)
    assert all(card.custom_comparison_value is None for card in deck)
    assert all(card.consumption_value == card.value for card in deck)
    assert all(card.comparison_value == card.value for card in deck)
