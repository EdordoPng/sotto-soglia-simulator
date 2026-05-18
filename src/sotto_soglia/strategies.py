"""Card selection strategies."""

from random import Random
from typing import Any

from sotto_soglia.models import Card, Color, PlayerState


def _color_order(color: Color) -> int:
    """Return stable enum order for deterministic tie-breaking."""

    return list(Color).index(color)


def _card_key(card: Card) -> tuple[int, int]:
    """Sort cards by value and then stable color order."""

    return (card.value, _color_order(card.color))


def _alive_opponent_colors(
    player: PlayerState,
    game_state: dict[str, Any] | None,
) -> set[Color]:
    """Return colors of currently alive opponents from the minimal game state."""

    if not game_state:
        return set()

    players = game_state.get("players", [])
    return {
        other.color
        for other in players
        if other.player_id != player.player_id and other.is_alive
    }


class BaseStrategy:
    """Base class for all strategies."""

    name = "base"

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

    name = "random"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Return a random card using the provided random generator."""

        return rng.choice(hand)


class PrudentStrategy(BaseStrategy):
    """Strategy that minimizes direct card value damage."""

    name = "prudent"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose the lowest value card, preferring own color on ties."""

        return min(
            hand,
            key=lambda card: (
                card.value,
                card.color != player.color,
                _color_order(card.color),
            ),
        )


class DefensiveStrategy(BaseStrategy):
    """Strategy that prefers cards matching the player's own color."""

    name = "defensive"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose the lowest own-color card if available, otherwise lowest value."""

        own_color_cards = [card for card in hand if card.color == player.color]
        if own_color_cards:
            return min(own_color_cards, key=_card_key)
        return min(hand, key=_card_key)


class AggressiveStrategy(BaseStrategy):
    """Strategy that prefers cards matching alive opponents' colors."""

    name = "aggressive"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose an opponent-color card, avoiding value 1 when possible."""

        opponent_colors = _alive_opponent_colors(player, game_state)
        opponent_cards = [card for card in hand if card.color in opponent_colors]
        if opponent_cards:
            non_one_cards = [card for card in opponent_cards if card.value > 1]
            candidates = non_one_cards or opponent_cards
            return min(candidates, key=_card_key)

        return min(hand, key=_card_key)


class AntiCriticalStrategy(BaseStrategy):
    """Strategy that avoids the lowest card value when possible."""

    name = "anti_critical"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Avoid the lowest value, then prefer a middle/high own-color card."""

        lowest_value = min(card.value for card in hand)
        candidates = [card for card in hand if card.value > lowest_value] or hand
        sorted_candidates = sorted(
            candidates,
            key=lambda card: (
                card.value,
                card.color != player.color,
                _color_order(card.color),
            ),
        )
        return sorted_candidates[len(sorted_candidates) // 2]


class MixedStrategy(BaseStrategy):
    """Strategy that balances value, own color and opponent color."""

    name = "mixed"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose the highest scoring card with a simple deterministic formula."""

        opponent_colors = _alive_opponent_colors(player, game_state)

        def score(card: Card) -> tuple[float, int, int]:
            points = 6 - card.value
            if card.color == player.color:
                points += 2
            if card.color in opponent_colors:
                points += 2
            if card.value == 1:
                points -= 1
            return (points, -card.value, -_color_order(card.color))

        return max(hand, key=score)


AVAILABLE_STRATEGIES = {
    RandomStrategy.name: RandomStrategy,
    PrudentStrategy.name: PrudentStrategy,
    DefensiveStrategy.name: DefensiveStrategy,
    AggressiveStrategy.name: AggressiveStrategy,
    AntiCriticalStrategy.name: AntiCriticalStrategy,
    MixedStrategy.name: MixedStrategy,
}


def create_strategy(name: str) -> BaseStrategy:
    """Create a strategy by name."""

    normalized_name = name.strip().lower()
    strategy_class = AVAILABLE_STRATEGIES.get(normalized_name)
    if strategy_class is None:
        available = ", ".join(sorted(AVAILABLE_STRATEGIES))
        raise ValueError(f"Unknown strategy '{name}'. Available strategies: {available}")
    return strategy_class()
