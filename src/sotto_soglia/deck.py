"""Deck construction utilities."""

from collections.abc import Iterable

from sotto_soglia.models import Card, Color


def build_deck(active_colors: Iterable[Color], card_values: Iterable[int]) -> list[Card]:
    """Build a deck with one card for each active color/value pair."""

    return [Card(color=color, value=value) for color in active_colors for value in card_values]
