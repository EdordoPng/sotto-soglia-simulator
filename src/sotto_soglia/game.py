"""Game-level result models."""

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence
from random import Random

from sotto_soglia.config import GameConfig, get_v05_config_for_players
from sotto_soglia.critical import (
    MANO_LUCIDA,
    MANO_TREMANTE,
    CriticalCardEvent,
    build_critical_deck,
    critical_card_name,
)
from sotto_soglia.deck import build_deck
from sotto_soglia.models import Card, Color, PlayerState
from sotto_soglia.round import RoundResult, resolve_round
from sotto_soglia.strategies import BaseStrategy, RandomStrategy


@dataclass
class GameResult:
    """Result data for one completed game."""

    game_id: int
    winner_ids: list[int] = field(default_factory=list)
    is_draw: bool = False
    rounds_count: int = 0
    final_players: list[PlayerState] = field(default_factory=list)
    round_history: list[RoundResult] = field(default_factory=list)
    elimination_order: list[int] = field(default_factory=list)
    seed: int | None = None
    critical_card_effects_enabled: bool = False
    initial_critical_deck_order: list[str] = field(default_factory=list)
    remaining_critical_deck: list[str] = field(default_factory=list)
    critical_events: list[CriticalCardEvent] = field(default_factory=list)


def create_players(players_count: int, config: GameConfig) -> list[PlayerState]:
    """Create players with stable ids and colors."""

    if players_count < config.min_players or players_count > config.max_players:
        raise ValueError(
            f"players_count must be between {config.min_players} and {config.max_players}"
        )

    colors = list(Color)
    return [
        PlayerState(
            player_id=player_index + 1,
            color=colors[player_index],
            lives=config.initial_lives,
        )
        for player_index in range(players_count)
    ]


def _normalize_strategies(
    strategies: BaseStrategy | Sequence[BaseStrategy] | Mapping[int, BaseStrategy] | None,
    players: list[PlayerState],
) -> dict[int, BaseStrategy]:
    """Return one strategy per player id."""

    if strategies is None:
        return {player.player_id: RandomStrategy() for player in players}

    if isinstance(strategies, BaseStrategy):
        return {player.player_id: strategies for player in players}

    if isinstance(strategies, Mapping):
        missing_ids = {player.player_id for player in players} - set(strategies)
        if missing_ids:
            raise ValueError(f"Missing strategies for players: {missing_ids}")
        return {player.player_id: strategies[player.player_id] for player in players}

    if len(strategies) != len(players):
        raise ValueError("Strategy sequence length must match players_count")

    return {
        player.player_id: strategy
        for player, strategy in zip(players, strategies, strict=True)
    }


def _deal_hands(
    players: list[PlayerState],
    rng: Random,
    config: GameConfig,
    hand_sizes_by_player: Mapping[int, int] | None = None,
) -> dict[int, list[Card]]:
    """Build, shuffle and deal hands to alive players."""

    alive_players = [player for player in players if player.is_alive]
    active_colors = [player.color for player in alive_players]
    deck = build_deck(active_colors, config.card_values)
    rng.shuffle(deck)

    hand_sizes_by_player = hand_sizes_by_player or {}
    required_cards = sum(
        hand_sizes_by_player.get(player.player_id, config.cards_per_player)
        for player in alive_players
    )
    if len(deck) < required_cards:
        raise RuntimeError(
            f"Not enough cards to deal {config.cards_per_player} cards "
            f"to {len(alive_players)} alive players"
        )

    hands = {}
    cursor = 0
    for player in alive_players:
        hand_size = hand_sizes_by_player.get(player.player_id, config.cards_per_player)
        start = cursor
        end = start + hand_size
        hands[player.player_id] = deck[start:end]
        cursor = end

    return hands


def _build_game_critical_deck(config: GameConfig, seed: int | None, game_id: int) -> list[str]:
    """Build the initial critical deck for a game."""

    if not config.critical_card_effects_enabled:
        return []
    if config.critical_deck_order is not None:
        return list(config.critical_deck_order)

    deck = build_critical_deck()
    deck_seed = config.critical_deck_seed
    if deck_seed is None:
        deck_seed = seed
    if deck_seed is not None:
        deck_seed += game_id - 1
    Random(deck_seed).shuffle(deck)
    return deck


def _critical_effects_snapshot(players: list[PlayerState]) -> dict[int, list[str]]:
    """Snapshot next-round effects before this round can draw new cards."""

    return {
        player.player_id: list(player.active_critical_effects)
        for player in players
        if player.is_alive
    }


def _hand_sizes_from_critical_effects(
    players: list[PlayerState],
    config: GameConfig,
    active_effects_by_player: Mapping[int, list[str]],
    game_id: int,
    round_number: int,
) -> tuple[dict[int, int], list[CriticalCardEvent]]:
    """Return per-player hand sizes and events from Mano Lucida/Tremante."""

    hand_sizes: dict[int, int] = {}
    events: list[CriticalCardEvent] = []
    if not config.critical_card_effects_enabled:
        return hand_sizes, events

    for player in players:
        if not player.is_alive:
            continue
        active_effects = active_effects_by_player.get(player.player_id, [])
        card_id = None
        hand_size = config.cards_per_player
        if MANO_TREMANTE in active_effects:
            card_id = MANO_TREMANTE
            hand_size = 2
        elif MANO_LUCIDA in active_effects:
            card_id = MANO_LUCIDA
            hand_size = 4

        if card_id is None:
            continue

        hand_sizes[player.player_id] = hand_size
        events.append(
            CriticalCardEvent(
                game_id=game_id,
                round_number=round_number,
                draw_order=None,
                player_id=player.player_id,
                critical_card_id=card_id,
                critical_card_name=critical_card_name(card_id),
                timing="next_round",
                effect_triggered=True,
                player_lives_after=player.lives,
                player_critical_wounds_after=player.critical_wounds,
            )
        )

    return hand_sizes, events


def resolve_game_tiebreaker(
    candidate_player_ids: list[int],
    final_round_result: RoundResult,
) -> tuple[list[int], bool]:
    """Resolve a final round where every remaining player was eliminated."""

    if not candidate_player_ids:
        return [], True

    min_critical_wounds = min(
        final_round_result.critical_wounds_after[player_id]
        for player_id in candidate_player_ids
    )
    candidates = [
        player_id
        for player_id in candidate_player_ids
        if final_round_result.critical_wounds_after[player_id] == min_critical_wounds
    ]

    if len(candidates) == 1:
        return candidates, False

    max_previous_lives = max(
        final_round_result.lives_before[player_id]
        for player_id in candidates
    )
    candidates = [
        player_id
        for player_id in candidates
        if final_round_result.lives_before[player_id] == max_previous_lives
    ]

    return sorted(candidates), len(candidates) > 1


def play_game(
    game_id: int = 1,
    players_count: int = 4,
    strategies: BaseStrategy | Sequence[BaseStrategy] | Mapping[int, BaseStrategy] | None = None,
    seed: int | None = None,
    config: GameConfig | None = None,
    max_rounds: int = 1000,
) -> GameResult:
    """Play one complete game using the existing single-round resolver."""

    config = config or get_v05_config_for_players(players_count)
    players = create_players(players_count, config)
    strategy_by_player = _normalize_strategies(strategies, players)
    for player in players:
        player.strategy_name = strategy_by_player[player.player_id].name
    rng = Random(seed)
    round_history: list[RoundResult] = []
    elimination_order: list[int] = []
    critical_deck = _build_game_critical_deck(config, seed, game_id)
    initial_critical_deck_order = list(critical_deck)
    critical_events: list[CriticalCardEvent] = []

    while len([player for player in players if player.is_alive]) > 1:
        if len(round_history) >= max_rounds:
            raise RuntimeError(f"Game exceeded max_rounds={max_rounds}")

        round_number = len(round_history) + 1
        alive_start_ids = [
            player.player_id
            for player in players
            if player.is_alive
        ]
        active_effects_by_player = _critical_effects_snapshot(players)
        hand_sizes_by_player, preliminary_events = _hand_sizes_from_critical_effects(
            players,
            config,
            active_effects_by_player,
            game_id,
            round_number,
        )
        hands = _deal_hands(players, rng, config, hand_sizes_by_player)
        game_state = {
            "game_id": game_id,
            "round_number": round_number,
            "players": players,
            "round_history": round_history,
            "config": config,
        }

        selected_cards = {}
        for player_id in alive_start_ids:
            player = players[player_id - 1]
            hand = hands[player_id]
            selected_card = strategy_by_player[player_id].choose_card(
                player,
                hand,
                game_state,
                rng,
            )
            if selected_card not in hand:
                raise ValueError(
                    f"Strategy selected a card not present in player {player_id}'s hand"
                )
            selected_cards[player_id] = selected_card

        round_result = resolve_round(
            players,
            selected_cards,
            config,
            round_number=round_number,
            game_id=game_id,
            critical_deck=critical_deck,
            critical_effects_snapshot=active_effects_by_player,
            strategies=strategy_by_player,
            rng=rng,
            preliminary_critical_events=preliminary_events,
            game_state=game_state,
        )
        round_history.append(round_result)
        critical_events.extend(round_result.critical_events)
        elimination_order.extend(round_result.eliminated_players)

        alive_after = [
            player.player_id
            for player in players
            if player.is_alive
        ]

        if len(alive_after) == 1:
            return GameResult(
                game_id=game_id,
                winner_ids=alive_after,
                is_draw=False,
                rounds_count=len(round_history),
                final_players=players,
                round_history=round_history,
                elimination_order=elimination_order,
                seed=seed,
                critical_card_effects_enabled=config.critical_card_effects_enabled,
                initial_critical_deck_order=initial_critical_deck_order,
                remaining_critical_deck=list(critical_deck),
                critical_events=critical_events,
            )

        if not alive_after:
            winner_ids, is_draw = resolve_game_tiebreaker(
                alive_start_ids,
                round_result,
            )
            return GameResult(
                game_id=game_id,
                winner_ids=winner_ids,
                is_draw=is_draw,
                rounds_count=len(round_history),
                final_players=players,
                round_history=round_history,
                elimination_order=elimination_order,
                seed=seed,
                critical_card_effects_enabled=config.critical_card_effects_enabled,
                initial_critical_deck_order=initial_critical_deck_order,
                remaining_critical_deck=list(critical_deck),
                critical_events=critical_events,
            )

    alive_players = [player.player_id for player in players if player.is_alive]
    return GameResult(
        game_id=game_id,
        winner_ids=alive_players,
        is_draw=False,
        rounds_count=len(round_history),
        final_players=players,
        round_history=round_history,
        elimination_order=elimination_order,
        seed=seed,
        critical_card_effects_enabled=config.critical_card_effects_enabled,
        initial_critical_deck_order=initial_critical_deck_order,
        remaining_critical_deck=list(critical_deck),
        critical_events=critical_events,
    )
