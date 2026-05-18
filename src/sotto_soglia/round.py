"""Round-level result models."""

from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping
from random import Random

from sotto_soglia.config import GameConfig
from sotto_soglia.critical import (
    BENDAGGIO_EMERGENZA,
    COLPO_DI_CODA,
    FERITA_ESPOSTA,
    SANGUE_FREDDO,
    SCUDO_ISTINTIVO,
    SONO_ANCORA_QUI,
    SONO_ANCORA_QUI_SINGLE_2,
    SONO_ANCORA_QUI_UP_TO_2_TARGETS,
    CriticalCardEvent,
    critical_card_name,
    critical_card_timing,
)
from sotto_soglia.models import Card
from sotto_soglia.models import PlayerState
from sotto_soglia.rules import (
    apply_life_loss,
    find_lowest_value_players,
    resolve_eliminations,
)
from sotto_soglia.strategies import BaseStrategy, choose_fallback_critical_effect_target


@dataclass
class RoundResult:
    """Minimal result data for one resolved round."""

    round_number: int
    selected_cards: dict[int, Card] = field(default_factory=dict)
    lowest_value: int | None = None
    critical_wound_players: list[int] = field(default_factory=list)
    base_damage_by_player: dict[int, int] = field(default_factory=dict)
    extra_damage_by_player: dict[int, int] = field(default_factory=dict)
    total_damage_by_player: dict[int, int] = field(default_factory=dict)
    eliminated_players: list[int] = field(default_factory=list)
    lives_before: dict[int, int] = field(default_factory=dict)
    lives_after: dict[int, int] = field(default_factory=dict)
    critical_wounds_before: dict[int, int] = field(default_factory=dict)
    critical_wounds_after: dict[int, int] = field(default_factory=dict)
    critical_events: list[CriticalCardEvent] = field(default_factory=list)
    critical_draw_order: list[int] = field(default_factory=list)
    critical_prevented_damage_by_player: dict[int, int] = field(default_factory=dict)
    critical_life_delta_by_player: dict[int, int] = field(default_factory=dict)

    @property
    def damage_by_player(self) -> dict[int, int]:
        """Backward-compatible alias for total round damage."""

        return self.total_damage_by_player


def _players_by_id(
    players: Mapping[int, PlayerState] | Iterable[PlayerState],
) -> dict[int, PlayerState]:
    """Return players indexed by id."""

    if isinstance(players, Mapping):
        return dict(players)
    return {player.player_id: player for player in players}


def resolve_round(
    players: Mapping[int, PlayerState] | Iterable[PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    round_number: int = 1,
    game_id: int = 1,
    critical_deck: list[str] | None = None,
    critical_effects_snapshot: Mapping[int, list[str]] | None = None,
    strategies: Mapping[int, BaseStrategy] | None = None,
    rng: Random | None = None,
    preliminary_critical_events: Iterable[CriticalCardEvent] | None = None,
    game_state: dict | None = None,
) -> RoundResult:
    """Resolve one simultaneous reveal round and mutate player states."""

    player_map = _players_by_id(players)
    selected_cards = dict(selected_cards)
    rng = rng or Random()

    missing_player_ids = set(selected_cards) - set(player_map)
    if missing_player_ids:
        raise ValueError(f"Selected cards contain unknown players: {missing_player_ids}")

    lives_before = {
        player_id: player.lives
        for player_id, player in player_map.items()
    }
    critical_wounds_before = {
        player_id: player.critical_wounds
        for player_id, player in player_map.items()
    }
    active_effects_by_player: dict[int, list[str]] = {}
    if config.critical_card_effects_enabled:
        active_effects_by_player = {
            player_id: list(effects)
            for player_id, effects in (critical_effects_snapshot or {}).items()
        }
        if not active_effects_by_player:
            active_effects_by_player = {
                player_id: list(player.active_critical_effects)
                for player_id, player in player_map.items()
            }
    critical_events = list(preliminary_critical_events or [])
    critical_life_delta_by_player = {player_id: 0 for player_id in player_map}

    critical_wound_player_ids = find_lowest_value_players(selected_cards)
    lowest_value = min((card.value for card in selected_cards.values()), default=None)

    critical_draw_order = [
        player_id
        for player_id in sorted(selected_cards)
        if player_id in critical_wound_player_ids
    ]
    for draw_index, player_id in enumerate(critical_draw_order, start=1):
        player_map[player_id].critical_wounds += 1
        if config.critical_card_effects_enabled:
            _draw_and_apply_critical_card(
                player_map=player_map,
                player_id=player_id,
                game_id=game_id,
                round_number=round_number,
                draw_order=draw_index,
                critical_deck=critical_deck,
                critical_wound_player_ids=critical_wound_player_ids,
                config=config,
                critical_events=critical_events,
                critical_life_delta_by_player=critical_life_delta_by_player,
                strategies=strategies or {},
                rng=rng,
                game_state=game_state,
            )

    base_damage_by_player = {
        player_id: _calculate_base_damage_with_critical_effects(
            player=player_map[player_id],
            card=card,
            received_critical_wound=player_id in critical_wound_player_ids,
            color_effects_enabled=config.color_effects_enabled,
            active_effects=active_effects_by_player.get(player_id, []),
            critical_events=critical_events,
            game_id=game_id,
            round_number=round_number,
        )
        for player_id, card in selected_cards.items()
    }

    extra_damage_by_player, prevented_damage_by_player = _calculate_extra_damage_with_critical_effects(
        player_map,
        selected_cards,
        critical_wound_player_ids,
        color_effects_enabled=config.color_effects_enabled,
        active_effects_by_player=active_effects_by_player,
        critical_events=critical_events,
        game_id=game_id,
        round_number=round_number,
    )

    total_damage_by_player = {
        player_id: base_damage_by_player.get(player_id, 0)
        + extra_damage_by_player.get(player_id, 0)
        for player_id in player_map
    }

    for player_id, damage in total_damage_by_player.items():
        apply_life_loss(player_map[player_id], damage)

    if config.critical_card_effects_enabled:
        _apply_colpo_di_coda(
            player_map=player_map,
            critical_wound_player_ids=critical_wound_player_ids,
            active_effects_by_player=active_effects_by_player,
            strategies=strategies or {},
            rng=rng,
            game_state=game_state,
            critical_events=critical_events,
            critical_life_delta_by_player=critical_life_delta_by_player,
            game_id=game_id,
            round_number=round_number,
        )

    for player_id, prevented_damage in prevented_damage_by_player.items():
        player_map[player_id].damage_prevented_by_critical_cards += prevented_damage

    eliminated_players = resolve_eliminations(player_map, config)

    if config.critical_card_effects_enabled:
        _consume_active_critical_effects(player_map, active_effects_by_player)

    lives_after = {
        player_id: player.lives
        for player_id, player in player_map.items()
    }
    critical_wounds_after = {
        player_id: player.critical_wounds
        for player_id, player in player_map.items()
    }

    return RoundResult(
        round_number=round_number,
        selected_cards=selected_cards,
        lowest_value=lowest_value,
        critical_wound_players=sorted(critical_wound_player_ids),
        base_damage_by_player=base_damage_by_player,
        extra_damage_by_player=extra_damage_by_player,
        total_damage_by_player=total_damage_by_player,
        eliminated_players=eliminated_players,
        lives_before=lives_before,
        lives_after=lives_after,
        critical_wounds_before=critical_wounds_before,
        critical_wounds_after=critical_wounds_after,
        critical_events=critical_events,
        critical_draw_order=critical_draw_order,
        critical_prevented_damage_by_player=prevented_damage_by_player,
        critical_life_delta_by_player=critical_life_delta_by_player,
    )


def _draw_and_apply_critical_card(
    player_map: dict[int, PlayerState],
    player_id: int,
    game_id: int,
    round_number: int,
    draw_order: int,
    critical_deck: list[str] | None,
    critical_wound_player_ids: set[int],
    config: GameConfig,
    critical_events: list[CriticalCardEvent],
    critical_life_delta_by_player: dict[int, int],
    strategies: Mapping[int, BaseStrategy],
    rng: Random,
    game_state: dict | None,
) -> None:
    """Draw one critical card, if available, and apply or register its effect."""

    if not critical_deck:
        return

    card_id = critical_deck.pop(0)
    player = player_map[player_id]
    player.critical_cards_drawn.append(card_id)
    deck_position = len(player.critical_cards_drawn) + sum(
        len(other.critical_cards_drawn)
        for other in player_map.values()
        if other.player_id != player_id
    )
    life_delta_player = 0
    life_delta_targets: dict[int, int] = {}
    effect_triggered = card_id in (BENDAGGIO_EMERGENZA, SONO_ANCORA_QUI)

    if card_id == BENDAGGIO_EMERGENZA:
        before = player.lives
        player.lives = min(config.initial_lives, player.lives + 1)
        life_delta_player = player.lives - before
        player.life_gained_from_critical_cards += life_delta_player
        critical_life_delta_by_player[player_id] += life_delta_player
    elif card_id == SONO_ANCORA_QUI:
        valid_targets = [
            target
            for target in player_map.values()
            if target.player_id != player_id
            and target.is_alive
            and target.player_id not in critical_wound_player_ids
        ]
        selected_targets = _choose_sono_ancora_qui_targets(
            source=player,
            valid_targets=valid_targets,
            strategy=strategies.get(player_id),
            rng=rng,
            game_state=game_state,
            variant=config.sono_ancora_qui_variant,
        )
        target_damage = 2 if config.sono_ancora_qui_variant == SONO_ANCORA_QUI_SINGLE_2 else 1
        target_ids: list[int] = []
        for target in selected_targets:
            before = target.lives
            apply_life_loss(target, target_damage)
            delta = target.lives - before
            if delta:
                target.life_lost_from_critical_cards += -delta
                critical_life_delta_by_player[target.player_id] += delta
                life_delta_targets[target.player_id] = delta
            target_ids.append(target.player_id)
        target_player_id = ",".join(str(target_id) for target_id in target_ids) or None
    else:
        player.active_critical_effects.append(card_id)

    critical_events.append(
        CriticalCardEvent(
            game_id=game_id,
            round_number=round_number,
            draw_order=draw_order,
            player_id=player_id,
            critical_card_id=card_id,
            critical_card_name=critical_card_name(card_id),
            timing=critical_card_timing(card_id),
            effect_triggered=effect_triggered if card_id != SONO_ANCORA_QUI else target_player_id is not None,
            target_player_id=target_player_id if card_id == SONO_ANCORA_QUI else None,
            life_delta_player=life_delta_player,
            life_delta_targets=life_delta_targets,
            deck_position=deck_position,
            player_lives_after=player.lives,
            player_critical_wounds_after=player.critical_wounds,
        )
    )


def _choose_sono_ancora_qui_targets(
    source: PlayerState,
    valid_targets: list[PlayerState],
    strategy: BaseStrategy | None,
    rng: Random,
    game_state: dict | None,
    variant: str,
) -> list[PlayerState]:
    """Choose one or two Sono ancora qui targets using strategy target choice."""

    target_count = 2 if variant == SONO_ANCORA_QUI_UP_TO_2_TARGETS else 1
    remaining_targets = list(valid_targets)
    selected_targets: list[PlayerState] = []

    for _ in range(target_count):
        if not remaining_targets:
            break
        if strategy is None:
            target = choose_fallback_critical_effect_target(remaining_targets)
        else:
            target = strategy.choose_critical_effect_target(
                game_state,
                source,
                SONO_ANCORA_QUI,
                remaining_targets,
                rng,
            )
            if target not in remaining_targets:
                target = choose_fallback_critical_effect_target(remaining_targets)
        if target is None:
            break
        selected_targets.append(target)
        remaining_targets.remove(target)

    return selected_targets


def _calculate_base_damage_with_critical_effects(
    player: PlayerState,
    card: Card,
    received_critical_wound: bool,
    color_effects_enabled: bool,
    active_effects: list[str],
    critical_events: list[CriticalCardEvent],
    game_id: int,
    round_number: int,
) -> int:
    """Calculate base damage with Sangue Freddo support."""

    if received_critical_wound:
        return 0

    damage = card.value
    reduction = 0
    if color_effects_enabled and card.color == player.color:
        reduction = 2 if SANGUE_FREDDO in active_effects else 1
        damage -= reduction

    final_damage = max(1, damage)
    if SANGUE_FREDDO in active_effects:
        prevented = 1 if color_effects_enabled and card.color == player.color else 0
        critical_events.append(
            CriticalCardEvent(
                game_id=game_id,
                round_number=round_number,
                draw_order=None,
                player_id=player.player_id,
                critical_card_id=SANGUE_FREDDO,
                critical_card_name=critical_card_name(SANGUE_FREDDO),
                timing="next_round",
                effect_triggered=prevented > 0,
                prevented_damage=prevented,
                player_lives_after=player.lives,
                player_critical_wounds_after=player.critical_wounds,
            )
        )
        player.damage_prevented_by_critical_cards += prevented

    return final_damage


def _calculate_extra_damage_with_critical_effects(
    players: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    critical_wound_player_ids: set[int],
    color_effects_enabled: bool,
    active_effects_by_player: Mapping[int, list[str]],
    critical_events: list[CriticalCardEvent],
    game_id: int,
    round_number: int,
) -> tuple[dict[int, int], dict[int, int]]:
    """Calculate extra color damage with shield and exposed-wound modifiers."""

    extra_damage = {player_id: 0 for player_id in players}
    prevented_damage = {player_id: 0 for player_id in players}
    if not color_effects_enabled:
        return extra_damage, prevented_damage

    shield_used: set[int] = set()
    exposed_used: set[int] = set()

    for source_id in sorted(selected_cards):
        card = selected_cards[source_id]
        source = players[source_id]
        if source_id in critical_wound_player_ids or not source.is_alive:
            continue

        for target_id in sorted(players):
            target = players[target_id]
            if target.player_id == source_id or not target.is_alive:
                continue
            if target.player_id in critical_wound_player_ids:
                continue
            if target.color != card.color:
                continue

            damage = 1
            active_effects = active_effects_by_player.get(target.player_id, [])
            if SCUDO_ISTINTIVO in active_effects and target.player_id not in shield_used:
                damage = 0
                shield_used.add(target.player_id)
                prevented_damage[target.player_id] += 1
                critical_events.append(
                    _effect_event(
                        game_id,
                        round_number,
                        target,
                        SCUDO_ISTINTIVO,
                        effect_triggered=True,
                        prevented_damage=1,
                    )
                )
            elif FERITA_ESPOSTA in active_effects and target.player_id not in exposed_used:
                damage = 2
                exposed_used.add(target.player_id)
                critical_events.append(
                    _effect_event(
                        game_id,
                        round_number,
                        target,
                        FERITA_ESPOSTA,
                        effect_triggered=True,
                        life_delta_player=-1,
                    )
                )

            extra_damage[target.player_id] += damage

    return extra_damage, prevented_damage


def _apply_colpo_di_coda(
    player_map: dict[int, PlayerState],
    critical_wound_player_ids: set[int],
    active_effects_by_player: Mapping[int, list[str]],
    strategies: Mapping[int, BaseStrategy],
    rng: Random,
    game_state: dict | None,
    critical_events: list[CriticalCardEvent],
    critical_life_delta_by_player: dict[int, int],
    game_id: int,
    round_number: int,
) -> None:
    """Apply Colpo di Coda after normal round damage."""

    for source_id in sorted(critical_wound_player_ids):
        source = player_map[source_id]
        if COLPO_DI_CODA not in active_effects_by_player.get(source_id, []):
            continue

        valid_targets = [
            target
            for target in player_map.values()
            if target.player_id != source_id
            and target.is_alive
            and target.player_id not in critical_wound_player_ids
        ]
        strategy = strategies.get(source_id)
        if strategy is None:
            target = choose_fallback_critical_effect_target(valid_targets)
        else:
            target = strategy.choose_critical_effect_target(
                game_state,
                source,
                COLPO_DI_CODA,
                valid_targets,
                rng,
            )
            if target not in valid_targets:
                target = choose_fallback_critical_effect_target(valid_targets)

        life_delta_targets = {}
        target_player_id = None
        triggered = target is not None
        if target is not None:
            target_player_id = target.player_id
            before = target.lives
            apply_life_loss(target, 2)
            delta = target.lives - before
            if delta:
                target.life_lost_from_critical_cards += -delta
                critical_life_delta_by_player[target.player_id] += delta
                life_delta_targets[target.player_id] = delta

        critical_events.append(
            CriticalCardEvent(
                game_id=game_id,
                round_number=round_number,
                draw_order=None,
                player_id=source_id,
                critical_card_id=COLPO_DI_CODA,
                critical_card_name=critical_card_name(COLPO_DI_CODA),
                timing="next_round",
                effect_triggered=triggered,
                target_player_id=target_player_id,
                life_delta_targets=life_delta_targets,
                player_lives_after=source.lives,
                player_critical_wounds_after=source.critical_wounds,
            )
        )


def _effect_event(
    game_id: int,
    round_number: int,
    player: PlayerState,
    card_id: str,
    effect_triggered: bool,
    life_delta_player: int = 0,
    prevented_damage: int = 0,
) -> CriticalCardEvent:
    """Build a standard next-round effect event."""

    return CriticalCardEvent(
        game_id=game_id,
        round_number=round_number,
        draw_order=None,
        player_id=player.player_id,
        critical_card_id=card_id,
        critical_card_name=critical_card_name(card_id),
        timing="next_round",
        effect_triggered=effect_triggered,
        life_delta_player=life_delta_player,
        prevented_damage=prevented_damage,
        player_lives_after=player.lives,
        player_critical_wounds_after=player.critical_wounds,
    )


def _consume_active_critical_effects(
    player_map: dict[int, PlayerState],
    active_effects_by_player: Mapping[int, list[str]],
) -> None:
    """Consume effects that were active at the start of the round."""

    for player_id, effects in active_effects_by_player.items():
        player = player_map[player_id]
        for effect_id in effects:
            if effect_id in player.active_critical_effects:
                player.active_critical_effects.remove(effect_id)
                player.consumed_critical_effects.append(effect_id)
