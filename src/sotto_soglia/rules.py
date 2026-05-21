"""Rule functions for Sotto Soglia.

The full game rules will be implemented incrementally in later phases.
"""

from collections.abc import Iterable, Mapping

from sotto_soglia.animal_effects import (
    CONIGLIO_GRANDE_BALZO,
    CONIGLIO_PASSO_LEGGERO,
    CONIGLIO_SCATTO_IMPROVVISO,
    get_effect_id_for_card,
    is_own_animal_card_effect_active,
)
from sotto_soglia.config import GameConfig
from sotto_soglia.critical import RESPIRO_CALMO
from sotto_soglia.models import Card, EliminationReason, PlayerState


PlayerCollection = Mapping[int, PlayerState] | Iterable[PlayerState]


def _players_by_id(players: PlayerCollection) -> dict[int, PlayerState]:
    """Return players indexed by id."""

    if isinstance(players, Mapping):
        return dict(players)
    return {player.player_id: player for player in players}


def find_lowest_value_players(selected_cards: Mapping[int, Card]) -> set[int]:
    """Return player ids that played the lowest comparison value."""

    if not selected_cards:
        return set()

    lowest_value = min(card.comparison_value for card in selected_cards.values())
    return {
        player_id
        for player_id, card in selected_cards.items()
        if card.comparison_value == lowest_value
    }


def find_lowest_value_cards(selected_cards: Mapping[int, Card]) -> set[int]:
    """Backward-compatible alias for lowest-value player ids."""

    return find_lowest_value_players(selected_cards)


def get_active_own_animal_effect_id(
    player: PlayerState,
    card: Card,
    config: GameConfig,
) -> str | None:
    """Return the active own-animal effect id for this play, if any."""

    if not config.animal_card_effects_enabled:
        return None

    if not is_own_animal_card_effect_active(player, card):
        return None

    return get_effect_id_for_card(card)


def get_effective_comparison_value(
    player: PlayerState,
    card: Card,
    config: GameConfig,
) -> int:
    """Return the comparison value for a card as played by one player."""

    effect_id = get_active_own_animal_effect_id(player, card, config)
    if effect_id == CONIGLIO_SCATTO_IMPROVVISO:
        return 2

    if effect_id == CONIGLIO_GRANDE_BALZO:
        return 5

    return card.comparison_value


def get_effective_consumption_value(
    player: PlayerState,
    card: Card,
    config: GameConfig,
) -> int:
    """Return the consumption value for a card as played by one player."""

    effect_id = get_active_own_animal_effect_id(player, card, config)
    if effect_id == CONIGLIO_PASSO_LEGGERO:
        return 1

    return card.consumption_value


def find_lowest_effective_value_players(
    players: PlayerCollection,
    selected_cards: Mapping[int, Card],
    config: GameConfig,
) -> set[int]:
    """Return player ids with the lowest contextual comparison value."""

    if not selected_cards:
        return set()

    player_map = _players_by_id(players)
    effective_values = {
        player_id: get_effective_comparison_value(
            player_map[player_id],
            card,
            config,
        )
        for player_id, card in selected_cards.items()
    }
    lowest_value = min(effective_values.values())
    return {
        player_id
        for player_id, effective_value in effective_values.items()
        if effective_value == lowest_value
    }


def valid_comparison_value_targets(
    source_player: PlayerState,
    players: PlayerCollection,
    revealed_cards: Mapping[int, Card],
) -> list[PlayerState]:
    """Return valid targets for effects that modify comparison values."""

    player_map = _players_by_id(players)
    return [
        player_map[player_id]
        for player_id in sorted(revealed_cards)
        if player_id in player_map
        and player_id != source_player.player_id
        and player_map[player_id].is_alive
    ]


def choose_comparison_value_target(
    valid_targets: Iterable[PlayerState],
) -> PlayerState | None:
    """Choose one comparison-value target with deterministic fallback."""

    targets = list(valid_targets)
    if not targets:
        return None
    return min(targets, key=lambda target: target.player_id)


def apply_comparison_value_modifier(
    comparison_value: int,
    modifier: int,
    target_active_effects: Iterable[str] | None = None,
    caused_by_opponent: bool = False,
) -> int:
    """Apply a comparison-value modifier, respecting Respiro Calmo protection."""

    active_effects = set(target_active_effects or [])
    is_blocked_opponent_reduction = (
        modifier < 0
        and caused_by_opponent
        and RESPIRO_CALMO in active_effects
    )
    if is_blocked_opponent_reduction:
        return comparison_value

    return comparison_value + modifier


def calculate_base_damage(
    player: PlayerState,
    card: Card,
    received_critical_wound: bool,
    color_effects_enabled: bool = True,
) -> int:
    """Calculate life damage from a player's own revealed card."""

    if received_critical_wound:
        return 0

    damage = card.consumption_value
    if color_effects_enabled and card.color == player.color:
        damage -= 1

    return max(1, damage)


def calculate_extra_damage(
    players: PlayerCollection,
    selected_cards: Mapping[int, Card],
    critical_wound_player_ids: set[int],
    color_effects_enabled: bool = True,
) -> dict[int, int]:
    """Calculate cumulative extra damage from opponent-color cards.

    Players who received a critical wound neither deal nor receive extra damage.
    """

    player_map = _players_by_id(players)
    extra_damage = {player_id: 0 for player_id in player_map}
    if not color_effects_enabled:
        return extra_damage

    for source_id, card in selected_cards.items():
        source = player_map[source_id]
        if source_id in critical_wound_player_ids or not source.is_alive:
            continue

        for target in player_map.values():
            if target.player_id == source_id or not target.is_alive:
                continue
            if target.player_id in critical_wound_player_ids:
                continue
            if target.color == card.color:
                extra_damage[target.player_id] += 1

    return extra_damage


def apply_color_effects(
    players: PlayerCollection,
    selected_cards: Mapping[int, Card],
    critical_wound_player_ids: set[int],
    color_effects_enabled: bool = True,
) -> dict[int, int]:
    """Backward-compatible wrapper for color effect damage."""

    return calculate_extra_damage(
        players,
        selected_cards,
        critical_wound_player_ids,
        color_effects_enabled=color_effects_enabled,
    )


def apply_life_loss(player: PlayerState, amount: int) -> None:
    """Apply life loss without letting lives drop below zero."""

    if amount <= 0:
        return

    player.lives = max(0, player.lives - amount)


def resolve_eliminations(
    players: PlayerCollection,
    config: GameConfig,
) -> list[int]:
    """Mark players eliminated after all round effects are resolved."""

    eliminated_players: list[int] = []

    for player in _players_by_id(players).values():
        if not player.is_alive:
            continue

        if player.critical_wounds >= config.critical_wounds_limit:
            player.is_alive = False
            player.elimination_reason = EliminationReason.CRITICAL_WOUNDS
            eliminated_players.append(player.player_id)
        elif player.lives <= 0:
            player.lives = 0
            player.is_alive = False
            player.elimination_reason = EliminationReason.LIVES
            eliminated_players.append(player.player_id)

    return eliminated_players


def resolve_final_tiebreaker(*args, **kwargs):
    """Resolve final-round simultaneous elimination tiebreakers.

    TODO: Implement critical-wound, previous-life and draw logic.
    """

    raise NotImplementedError
