"""Card selection strategies."""

from random import Random

from sotto_soglia.models import Card


class BaseStrategy:
    """Base class for all strategies."""

    def choose_card(self, hand: list[Card], rng: Random) -> Card:
        """Choose one card from the current hand."""

        raise NotImplementedError


class RandomStrategy(BaseStrategy):
    """Strategy that selects a random card from the hand."""

    def choose_card(self, hand: list[Card], rng: Random) -> Card:
        """Return a random card using the provided random generator."""

        return rng.choice(hand)
