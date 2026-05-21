"""Card selection strategies."""

from dataclasses import dataclass
from random import Random
from typing import Any

from sotto_soglia.animal_effects import (
    ANIMAL_DISPLAY_NAMES,
    get_animal_for_color,
    get_display_color_for_technical_color,
)
from sotto_soglia.config import GameConfig
from sotto_soglia.critical import COLPO_DI_CODA, SONO_ANCORA_QUI
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.rules import (
    get_effective_comparison_value,
    get_effective_consumption_value,
)


def _color_order(color: Color) -> int:
    """Return stable enum order for deterministic tie-breaking."""

    return list(Color).index(color)


def _card_key(card: Card) -> tuple[int, int]:
    """Sort cards by value and then stable color order."""

    return (card.value, _color_order(card.color))


@dataclass(frozen=True)
class StrategyDecisionCandidate:
    """Scoring breakdown for one strategy candidate card."""

    candidate_card_color: str
    candidate_card_display_color: str
    candidate_card_animal: str
    candidate_card_value: int
    effective_comparison: int
    effective_consumption: int
    score: float
    chosen: bool
    choice_rank: int
    reason_flags: tuple[str, ...]


@dataclass(frozen=True)
class _RankedStrategyCandidate:
    """Internal ranked candidate retaining the original card object."""

    card: Card
    candidate: StrategyDecisionCandidate
    sort_key: tuple[float, int, int, int, int]


def _alive_opponent_colors(
    player: PlayerState,
    game_state: dict[str, Any] | None,
) -> set[Color]:
    """Return colors of currently alive opponents from the minimal game state."""

    return {opponent.color for opponent in _alive_opponents(player, game_state)}


def _alive_opponents(
    player: PlayerState,
    game_state: dict[str, Any] | None,
) -> list[PlayerState]:
    """Return currently alive opponents from the minimal game state."""

    if not game_state:
        return []

    players = game_state.get("players", [])
    return [
        other
        for other in players
        if other.player_id != player.player_id and other.is_alive
    ]


def _game_config(game_state: dict[str, Any] | None) -> GameConfig:
    """Return the active config from game state, or legacy defaults."""

    if game_state and isinstance(game_state.get("config"), GameConfig):
        return game_state["config"]
    return GameConfig()


def _v05_reason_flags(
    player: PlayerState,
    comparison: int,
    consumption: int,
    lowest_hand_comparison: int,
    config: GameConfig,
) -> tuple[str, ...]:
    """Return simple audit flags for a v0.5 strategy candidate."""

    flags: list[str] = []
    if comparison == lowest_hand_comparison:
        flags.append("lowest_comparison")
    if player.critical_wounds >= config.critical_wounds_limit - 1:
        flags.append("near_abandonment")
    if consumption >= player.lives:
        flags.append("lethal_consumption")
    else:
        remaining_lives = player.lives - consumption
        if remaining_lives == 1:
            flags.append("remaining_lives_1")
        elif remaining_lives == 2:
            flags.append("remaining_lives_2")
        elif remaining_lives == 3:
            flags.append("remaining_lives_3")
    if comparison >= 4:
        flags.append("high_comparison")
    if consumption <= 1:
        flags.append("low_consumption")
    return tuple(flags)


def _build_strategy_decision_candidate(
    card: Card,
    comparison: int,
    consumption: int,
    score: float,
    chosen: bool,
    choice_rank: int,
    reason_flags: tuple[str, ...],
) -> StrategyDecisionCandidate:
    """Build public candidate telemetry for one scored card."""

    animal = get_animal_for_color(card.color)
    return StrategyDecisionCandidate(
        candidate_card_color=card.color.name,
        candidate_card_display_color=get_display_color_for_technical_color(card.color),
        candidate_card_animal=ANIMAL_DISPLAY_NAMES[animal],
        candidate_card_value=card.value,
        effective_comparison=comparison,
        effective_consumption=consumption,
        score=score,
        chosen=chosen,
        choice_rank=choice_rank,
        reason_flags=reason_flags,
    )


def _rank_v05_basic_candidates(
    player: PlayerState,
    hand: list[Card],
    game_state: dict[str, Any] | None,
) -> list[_RankedStrategyCandidate]:
    """Rank v05_basic candidate cards with the strategy's current scoring."""

    config = _game_config(game_state)
    alive_players_count = 1 + len(_alive_opponents(player, game_state))
    evaluated_cards = [
        (
            card,
            get_effective_comparison_value(player, card, config),
            get_effective_consumption_value(player, card, config),
        )
        for card in hand
    ]
    lowest_hand_comparison = min(
        comparison
        for _, comparison, _ in evaluated_cards
    )
    affamato_remaining = config.critical_wounds_limit - player.critical_wounds
    near_abandonment = affamato_remaining <= 1
    cautious = affamato_remaining <= 2

    scored_candidates = []
    for card, comparison, consumption in evaluated_cards:
        points = comparison * 3.0
        points -= consumption * 2.0

        low_comparison_penalty = max(0, 4 - comparison) * 2.0
        if comparison == lowest_hand_comparison:
            low_comparison_penalty += 3.0
        if near_abandonment:
            low_comparison_penalty *= 3.0
        elif cautious:
            low_comparison_penalty *= 1.8
        if alive_players_count <= 2:
            low_comparison_penalty *= 0.8
        points -= low_comparison_penalty

        if consumption >= player.lives:
            points -= 100.0
        else:
            remaining_lives = player.lives - consumption
            if remaining_lives <= 1:
                points -= 18.0
            elif remaining_lives <= 2:
                points -= 9.0

        sort_key = (
            points,
            -consumption,
            comparison,
            -card.value,
            -_color_order(card.color),
        )
        scored_candidates.append((card, comparison, consumption, points, sort_key))

    return _rank_scored_v05_candidates(
        player,
        scored_candidates,
        lowest_hand_comparison,
        config,
    )


def _rank_v05_balanced_candidates(
    player: PlayerState,
    hand: list[Card],
    game_state: dict[str, Any] | None,
) -> list[_RankedStrategyCandidate]:
    """Rank v05_balanced candidate cards with the strategy's current scoring."""

    config = _game_config(game_state)
    evaluated_cards = [
        (
            card,
            get_effective_comparison_value(player, card, config),
            get_effective_consumption_value(player, card, config),
        )
        for card in hand
    ]
    lowest_hand_comparison = min(
        comparison
        for _, comparison, _ in evaluated_cards
    )
    affamato_remaining = config.critical_wounds_limit - player.critical_wounds
    near_abandonment = affamato_remaining <= 1
    cautious = affamato_remaining <= 2

    scored_candidates = []
    for card, comparison, consumption in evaluated_cards:
        points = min(comparison, 4) * 2.4
        points -= consumption * 3.0

        low_comparison_penalty = max(0, 3 - comparison) * 1.5
        if comparison == lowest_hand_comparison:
            low_comparison_penalty += 2.0
        if near_abandonment:
            low_comparison_penalty *= 2.0
        elif cautious:
            low_comparison_penalty *= 1.4
        points -= low_comparison_penalty

        if consumption >= player.lives:
            points -= 120.0
        else:
            remaining_lives = player.lives - consumption
            if remaining_lives <= 1:
                points -= 24.0
            elif remaining_lives <= 2:
                points -= 12.0
            elif remaining_lives <= 3:
                points -= 4.0

        sort_key = (
            points,
            -consumption,
            comparison,
            -card.value,
            -_color_order(card.color),
        )
        scored_candidates.append((card, comparison, consumption, points, sort_key))

    return _rank_scored_v05_candidates(
        player,
        scored_candidates,
        lowest_hand_comparison,
        config,
    )


def _rank_scored_v05_candidates(
    player: PlayerState,
    scored_candidates: list[tuple[Card, int, int, float, tuple[float, int, int, int, int]]],
    lowest_hand_comparison: int,
    config: GameConfig,
) -> list[_RankedStrategyCandidate]:
    """Return scored candidates ordered by strategy preference."""

    ranked_input = sorted(
        scored_candidates,
        key=lambda item: item[4],
        reverse=True,
    )
    ranked_candidates = []
    for index, (card, comparison, consumption, points, sort_key) in enumerate(
        ranked_input,
        start=1,
    ):
        candidate = _build_strategy_decision_candidate(
            card=card,
            comparison=comparison,
            consumption=consumption,
            score=points,
            chosen=index == 1,
            choice_rank=index,
            reason_flags=_v05_reason_flags(
                player,
                comparison,
                consumption,
                lowest_hand_comparison,
                config,
            ),
        )
        ranked_candidates.append(
            _RankedStrategyCandidate(
                card=card,
                candidate=candidate,
                sort_key=sort_key,
            )
        )
    return ranked_candidates


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

    def evaluate_candidates(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
    ) -> list[StrategyDecisionCandidate]:
        """Return optional scoring telemetry for strategies that expose it."""

        return []

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Choose a target for a critical-card effect."""

        return choose_fallback_critical_effect_target(valid_targets)


def choose_fallback_critical_effect_target(
    valid_targets: list[PlayerState],
) -> PlayerState | None:
    """Fallback target choice: alive valid opponent with the fewest lives."""

    if not valid_targets:
        return None
    return min(valid_targets, key=lambda target: (target.lives, target.player_id))


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

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Choose a random valid target."""

        if not valid_targets:
            return None
        return rng.choice(valid_targets)


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

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Target the opponent with the highest lives."""

        if not valid_targets:
            return None
        return max(valid_targets, key=lambda target: (target.lives, -target.player_id))


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

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Target the opponent with the fewest lives."""

        return choose_fallback_critical_effect_target(valid_targets)


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

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Target the opponent furthest from critical-wound elimination."""

        if not valid_targets:
            return None
        return min(valid_targets, key=lambda target: (target.critical_wounds, target.lives, target.player_id))


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

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Target using a simple lives and critical-wounds heuristic."""

        if not valid_targets:
            return None
        return max(
            valid_targets,
            key=lambda target: (
                target.critical_wounds * 2 + max(0, 8 - target.lives),
                -target.player_id,
            ),
        )


class V05BasicStrategy(BaseStrategy):
    """Simple v0.5 strategy balancing Affamato risk and Scorte consumption."""

    name = "v05_basic"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose a card using effective v0.5 comparison and consumption values."""

        return _rank_v05_basic_candidates(player, hand, game_state)[0].card

    def evaluate_candidates(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
    ) -> list[StrategyDecisionCandidate]:
        """Return ranked scoring breakdown for v05_basic candidate cards."""

        return [
            ranked.candidate
            for ranked in _rank_v05_basic_candidates(player, hand, game_state)
        ]


class V05BalancedStrategy(BaseStrategy):
    """More Scorte-conscious v0.5 strategy with moderated Affamato avoidance."""

    name = "v05_balanced"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose a card using a conservative Scorte/Affamato balance."""

        return _rank_v05_balanced_candidates(player, hand, game_state)[0].card

    def evaluate_candidates(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
    ) -> list[StrategyDecisionCandidate]:
        """Return ranked scoring breakdown for v05_balanced candidate cards."""

        return [
            ranked.candidate
            for ranked in _rank_v05_balanced_candidates(player, hand, game_state)
        ]


class AdaptivePressureStrategy(BaseStrategy):
    """Strategy that balances pressure, critical-wound risk and survival."""

    name = "adaptive_pressure"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose the highest scoring card with deterministic tie-breakers."""

        opponents_by_color = {
            opponent.color: opponent
            for opponent in _alive_opponents(player, game_state)
        }

        def opponent_vulnerability(card: Card) -> float:
            opponent = opponents_by_color.get(card.color)
            if opponent is None:
                return 0.0

            points = opponent.critical_wounds * 1.5
            if opponent.lives <= 3:
                points += 3
            elif opponent.lives <= 6:
                points += 2
            elif opponent.lives <= 9:
                points += 1
            return points

        def score(card: Card) -> tuple[float, bool, float, int, int]:
            points = -card.value * 1.2

            if player.critical_wounds >= 2:
                if card.value == 1:
                    points -= 8
                elif card.value == 2:
                    points -= 6
                else:
                    points += card.value * 1.5
                    if card.value >= 4:
                        points += 3
            else:
                points -= max(0, 3 - card.value) * 0.8
                if player.lives <= 3:
                    points += (6 - card.value) * 1.4
                elif player.lives <= 6:
                    points += (5 - card.value) * 0.4

            if card.color == player.color:
                points += 2
                if player.lives <= 3:
                    points += 3
                elif player.lives <= 6:
                    points += 2

            vulnerability = opponent_vulnerability(card)
            if vulnerability:
                points += 2 + vulnerability

            too_risky = player.critical_wounds >= 2 and card.value <= 2
            value_preference = card.value if too_risky else -card.value
            return (
                points,
                card.color == player.color,
                vulnerability,
                value_preference,
                -_color_order(card.color),
            )

        return max(hand, key=score)

    def choose_critical_effect_target(
        self,
        game_state: dict[str, Any] | None,
        source_player: PlayerState,
        effect_id: str,
        valid_targets: list[PlayerState],
        rng: Random,
    ) -> PlayerState | None:
        """Target the opponent under the most immediate pressure."""

        if not valid_targets:
            return None

        if effect_id == SONO_ANCORA_QUI:
            return min(
                valid_targets,
                key=lambda target: (
                    target.lives,
                    -target.critical_wounds,
                    target.player_id,
                ),
            )

        if effect_id == COLPO_DI_CODA:
            return max(
                valid_targets,
                key=lambda target: (
                    target.critical_wounds * 3.0 + max(0, 10 - target.lives),
                    -target.lives,
                    -target.player_id,
                ),
            )

        return max(
            valid_targets,
            key=lambda target: (
                target.critical_wounds * 2.0 + max(0, 10 - target.lives),
                -target.lives,
                -target.player_id,
            ),
        )


class CriticalAdaptiveStrategy(AdaptivePressureStrategy):
    """Adaptive strategy aware of active critical wound card effects."""

    name = "critical_adaptive"

    def choose_card(
        self,
        player: PlayerState,
        hand: list[Card],
        game_state: dict[str, Any] | None,
        rng: Random,
    ) -> Card:
        """Choose a card using adaptive pressure plus critical-effect context."""

        opponents_by_color = {
            opponent.color: opponent
            for opponent in _alive_opponents(player, game_state)
        }
        active_effects = set(player.active_critical_effects)
        critical_limit = 3
        if game_state and game_state.get("config") is not None:
            critical_limit = game_state["config"].critical_wounds_limit

        def score(card: Card) -> tuple[float, bool, float, int, int]:
            points = -card.value * 1.15
            one_wound_from_elimination = (
                player.critical_wounds >= critical_limit - 1
            )

            if one_wound_from_elimination:
                points -= max(0, 4 - card.value) * 4.0
            elif player.critical_wounds >= max(1, critical_limit - 2):
                points -= max(0, 3 - card.value) * 2.0
            else:
                points -= max(0, 3 - card.value) * 0.7

            if card.color == player.color:
                points += 2.0
                if "sangue_freddo" in active_effects:
                    points += 2.0
                if player.lives <= 6:
                    points += 1.5

            opponent = opponents_by_color.get(card.color)
            vulnerability = 0.0
            if opponent is not None:
                vulnerability += opponent.critical_wounds * 1.4
                if opponent.lives <= 3:
                    vulnerability += 4.0
                elif opponent.lives <= 6:
                    vulnerability += 2.5
                elif opponent.lives <= 9:
                    vulnerability += 1.0
                points += 1.5 + vulnerability

            if "scudo_istintivo" in active_effects:
                points += 0.5
            if "ferita_esposta" in active_effects:
                points -= 1.0
                if card.color != player.color:
                    points -= 0.5
            if "colpo_di_coda" in active_effects and not one_wound_from_elimination:
                points += max(0, 3 - card.value) * 0.5

            if player.lives <= 3:
                points += (6 - card.value) * 1.1

            too_risky = one_wound_from_elimination and card.value <= 2
            value_preference = card.value if too_risky else -card.value
            return (
                points,
                card.color == player.color,
                vulnerability,
                value_preference,
                -_color_order(card.color),
            )

        return max(hand, key=score)


AVAILABLE_STRATEGIES = {
    RandomStrategy.name: RandomStrategy,
    PrudentStrategy.name: PrudentStrategy,
    DefensiveStrategy.name: DefensiveStrategy,
    AggressiveStrategy.name: AggressiveStrategy,
    AntiCriticalStrategy.name: AntiCriticalStrategy,
    MixedStrategy.name: MixedStrategy,
    V05BasicStrategy.name: V05BasicStrategy,
    V05BalancedStrategy.name: V05BalancedStrategy,
    AdaptivePressureStrategy.name: AdaptivePressureStrategy,
    CriticalAdaptiveStrategy.name: CriticalAdaptiveStrategy,
}


def create_strategy(name: str) -> BaseStrategy:
    """Create a strategy by name."""

    normalized_name = name.strip().lower()
    strategy_class = AVAILABLE_STRATEGIES.get(normalized_name)
    if strategy_class is None:
        available = ", ".join(sorted(AVAILABLE_STRATEGIES))
        raise ValueError(f"Unknown strategy '{name}'. Available strategies: {available}")
    return strategy_class()
