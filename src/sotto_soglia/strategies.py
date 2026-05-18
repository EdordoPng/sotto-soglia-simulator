"""Card selection strategies."""

from random import Random
from typing import Any

from sotto_soglia.models import Card, PlayerState


class BaseStrategy:
    """Base class for all strategies."""

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose one card from the current hand."""

        raise NotImplementedError


class RandomStrategy(BaseStrategy):
    """Strategy that selects a random card from the hand."""

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Return a random card using the provided random generator."""

        return rng.choice(hand)
