"""Rule functions for Sotto Soglia.

The full game rules will be implemented incrementally in later phases.
"""

from collections.abc import Iterable, Mapping

from sotto_soglia.config import GameConfig
from sotto_soglia.models import Card, EliminationReason, PlayerState


PlayerCollection = Mapping[int, PlayerState] | Iterable[PlayerState]


def _players_by_id(players: PlayerCollection) -> dict[int, PlayerState]:
    """Return players indexed by id."""

    if isinstance(players, Mapping):
        return dict(players)
    return {player.player_id: player for player in players}


def find_lowest_value_players(selected_cards: Mapping[int, Card]) -> set[int]:
    """Return player ids that played the lowest revealed card value."""

    if not selected_cards:
        return set()

    lowest_value = min(card.value for card in selected_cards.values())
    return {
        player_id
        for player_id, card in selected_cards.items()
        if card.value == lowest_value
    }


def find_lowest_value_cards(selected_cards: Mapping[int, Card]) -> set[int]:
    """Backward-compatible alias for lowest-value player ids."""

    return find_lowest_value_players(selected_cards)


def calculate_base_damage(
    player: PlayerState,
    card: Card,
    received_critical_wound: bool,
) -> int:
    """Calculate life damage from a player's own revealed card."""

    if received_critical_wound:
        return 0

    damage = card.value
    if card.color == player.color:
        damage -= 1

    return max(1, damage)


def calculate_extra_damage(
    players: PlayerCollection,
    selected_cards: Mapping[int, Card],
    critical_wound_player_ids: set[int],
) -> dict[int, int]:
    """Calculate cumulative extra damage from opponent-color cards.

    Players who received a critical wound neither deal nor receive extra damage.
    """

    player_map = _players_by_id(players)
    extra_damage = {player_id: 0 for player_id in player_map}

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
) -> dict[int, int]:
    """Backward-compatible wrapper for color effect damage."""

    return calculate_extra_damage(players, selected_cards, critical_wound_player_ids)


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
