"""Round-level result models."""

from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping
from random import Random

from sotto_soglia.animal_effects import (
    ANIMAL_DISPLAY_NAMES,
    AnimalEffectEvent,
    CONIGLIO_GRANDE_BALZO,
    CONIGLIO_GRANDE_BALZO_DEBT,
    CONIGLIO_PASSO_LEGGERO,
    CONIGLIO_SCATTO_IMPROVVISO,
    PANDA_GRANDE_LETARGO,
    PANDA_RIPOSO_FORZATO,
    PANDA_RESPIRO_LENTO,
    SCIMMIA_BANANA_RUBATA,
    SCIMMIA_BUCCIA_DI_BANANA,
    SCIMMIA_FINTA_INNOCENTE,
    SCOIATTOLO_DISPENSA_ORDINATA,
    SCOIATTOLO_GHIANDA_NASCOSTA,
    SCOIATTOLO_PICCOLA_RISERVA,
    get_animal_for_color,
)
from sotto_soglia.config import GameConfig
from sotto_soglia.critical import (
    BENDAGGIO_EMERGENZA,
    BRICIOLA_NASCOSTA,
    COLPO_DI_CODA,
    FERITA_ESPOSTA,
    MORSO_DELLA_FAME,
    RAZIONE_RISPARMIATA,
    RESPIRO_CALMO,
    SANGUE_FREDDO,
    SCUDO_ISTINTIVO,
    SONO_ANCORA_QUI,
    SONO_ANCORA_QUI_SINGLE_2,
    SONO_ANCORA_QUI_UP_TO_2_TARGETS,
    NEXT_ROUND_EFFECTS,
    V05_HUNGER_CARD_IDS,
    CriticalCardEvent,
    critical_card_name,
    critical_card_timing,
    get_critical_deck_profile,
    resolve_v05_hunger_effect,
)
from sotto_soglia.models import Card
from sotto_soglia.models import PlayerState
from sotto_soglia.rules import (
    apply_comparison_value_modifier,
    apply_coniglio_grande_balzo_debt,
    apply_life_loss,
    choose_comparison_value_target,
    get_active_own_animal_effect_id,
    get_effective_comparison_value,
    get_effective_consumption_value,
    has_coniglio_grande_balzo_debt,
    resolve_eliminations,
    valid_comparison_value_targets,
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
    animal_events: list[AnimalEffectEvent] = field(default_factory=list)

    @property
    def damage_by_player(self) -> dict[int, int]:
        """Backward-compatible alias for total round damage."""

        return self.total_damage_by_player


@dataclass
class PendingExtraConsumption:
    """One extra consumption scheduled for the round extra-consumption phase."""

    source_player_id: int
    target_player_id: int
    amount: int
    effect_id: str
    event: CriticalCardEvent | None = None
    recovery_player_id: int | None = None
    source_card: Card | None = None


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
        _validate_active_critical_effects_for_profile(active_effects_by_player, config)
    active_animal_effects_by_player: dict[int, list[str]] = {}
    if config.animal_card_effects_enabled:
        active_animal_effects_by_player = {
            player_id: list(player.active_animal_effects)
            for player_id, player in player_map.items()
        }
    critical_events = list(preliminary_critical_events or [])
    critical_life_delta_by_player = {player_id: 0 for player_id in player_map}
    pending_life_recoveries = {player_id: 0 for player_id in player_map}
    pending_animal_life_recoveries: dict[int, int] = {}
    pending_life_recovery_events: dict[int, list[CriticalCardEvent]] = {
        player_id: [] for player_id in player_map
    }
    pending_extra_consumptions: list[PendingExtraConsumption] = []

    effective_comparison_values = {
        player_id: get_effective_comparison_value(
            player_map[player_id],
            card,
            config,
        )
        for player_id, card in selected_cards.items()
    }
    animal_events = _collect_comparison_animal_events(
        player_map,
        selected_cards,
        config,
        effective_comparison_values,
    )
    _apply_animal_comparison_effects(
        player_map,
        selected_cards,
        config,
        effective_comparison_values,
        active_effects_by_player,
        animal_events,
    )
    hunger_excluded_player_ids = _find_finta_innocente_excluded_players(
        player_map,
        selected_cards,
        config,
        animal_events,
    )
    eligible_comparison_values = {
        player_id: effective_value
        for player_id, effective_value in effective_comparison_values.items()
        if player_id not in hunger_excluded_player_ids
    }
    lowest_value = min(eligible_comparison_values.values(), default=None)
    critical_wound_player_ids = {
        player_id
        for player_id, effective_value in eligible_comparison_values.items()
        if effective_value == lowest_value
    }
    if lowest_value is None:
        critical_wound_player_ids = set()

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
                pending_life_recoveries=pending_life_recoveries,
                pending_life_recovery_events=pending_life_recovery_events,
                strategies=strategies or {},
                rng=rng,
                game_state=game_state,
            )

    _schedule_animal_life_recoveries(
        player_map=player_map,
        selected_cards=selected_cards,
        config=config,
        critical_wound_player_ids=critical_wound_player_ids,
        pending_life_recoveries=pending_animal_life_recoveries,
        animal_events=animal_events,
    )
    _schedule_next_round_animal_effects(
        player_map=player_map,
        selected_cards=selected_cards,
        config=config,
        critical_wound_player_ids=critical_wound_player_ids,
        animal_events=animal_events,
    )
    _schedule_animal_extra_consumptions(
        player_map=player_map,
        selected_cards=selected_cards,
        config=config,
        critical_wound_player_ids=critical_wound_player_ids,
        pending_extra_consumptions=pending_extra_consumptions,
        animal_events=animal_events,
    )

    base_damage_by_player = {
        player_id: _calculate_base_damage_with_critical_effects(
            player=player_map[player_id],
            card=card,
            config=config,
            received_critical_wound=player_id in critical_wound_player_ids,
            color_effects_enabled=config.color_effects_enabled,
            active_effects=active_effects_by_player.get(player_id, []),
            critical_events=critical_events,
            game_id=game_id,
            round_number=round_number,
            animal_events=animal_events,
            selected_cards=selected_cards,
            player_map=player_map,
            active_animal_effects=active_animal_effects_by_player.get(player_id, []),
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
    for target_id, amount in extra_damage_by_player.items():
        if amount > 0:
            schedule_extra_consumption(
                pending_extra_consumptions,
                source_player_id=target_id,
                target_player_id=target_id,
                amount=amount,
                effect_id="color_extra",
            )

    if config.critical_card_effects_enabled:
        _schedule_morso_della_fame(
            player_map=player_map,
            critical_wound_player_ids=critical_wound_player_ids,
            active_effects_by_player=active_effects_by_player,
            strategies=strategies or {},
            rng=rng,
            game_state=game_state,
            critical_events=critical_events,
            pending_extra_consumptions=pending_extra_consumptions,
            game_id=game_id,
            round_number=round_number,
        )

    for player_id, damage in base_damage_by_player.items():
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

    applied_extra_consumptions = apply_pending_extra_consumptions(
        player_map=player_map,
        pending_extra_consumptions=pending_extra_consumptions,
        critical_wound_player_ids=critical_wound_player_ids,
        critical_life_delta_by_player=critical_life_delta_by_player,
        pending_animal_life_recoveries=pending_animal_life_recoveries,
        animal_events=animal_events,
    )
    extra_damage_by_player = {
        player_id: applied_extra_consumptions.get(player_id, 0)
        for player_id in player_map
    }
    total_damage_by_player = {
        player_id: base_damage_by_player.get(player_id, 0)
        + extra_damage_by_player.get(player_id, 0)
        for player_id in player_map
    }

    apply_pending_life_recoveries(
        player_map=player_map,
        pending_life_recoveries=pending_life_recoveries,
        config=config,
        critical_life_delta_by_player=critical_life_delta_by_player,
        pending_life_recovery_events=pending_life_recovery_events,
    )
    apply_pending_animal_life_recoveries(
        player_map=player_map,
        pending_life_recoveries=pending_animal_life_recoveries,
        config=config,
    )

    for player_id, prevented_damage in prevented_damage_by_player.items():
        player_map[player_id].damage_prevented_by_critical_cards += prevented_damage

    eliminated_players = resolve_eliminations(player_map, config)

    if config.critical_card_effects_enabled:
        _consume_active_critical_effects(player_map, active_effects_by_player)
    if config.animal_card_effects_enabled:
        _consume_active_animal_effects(
            player_map,
            active_animal_effects_by_player,
            selected_cards,
            animal_events,
        )

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
        animal_events=animal_events,
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
    pending_life_recoveries: dict[int, int],
    pending_life_recovery_events: dict[int, list[CriticalCardEvent]],
    strategies: Mapping[int, BaseStrategy],
    rng: Random,
    game_state: dict | None,
) -> None:
    """Draw one critical card, if available, and apply or register its effect."""

    if not critical_deck:
        return

    card_id = critical_deck.pop(0)
    profile = get_critical_deck_profile(config.critical_deck_profile_id)
    if card_id not in profile.card_ids:
        raise ValueError(
            f"Critical card '{card_id}' is not valid for profile "
            f"'{profile.profile_id}'"
        )

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

    if card_id in V05_HUNGER_CARD_IDS:
        resolve_v05_hunger_effect(card_id, player, config)
        effect_triggered = False
        if card_id == BRICIOLA_NASCOSTA:
            schedule_life_recovery(pending_life_recoveries, player_id, 1)
    elif card_id == BENDAGGIO_EMERGENZA:
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
        target_damage = (
            2 if config.sono_ancora_qui_variant == SONO_ANCORA_QUI_SINGLE_2 else 1
        )
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
    elif card_id in NEXT_ROUND_EFFECTS:
        player.active_critical_effects.append(card_id)
    else:
        raise ValueError(
            f"Critical card '{card_id}' is not supported by the round resolver"
        )

    event = CriticalCardEvent(
        game_id=game_id,
        round_number=round_number,
        draw_order=draw_order,
        player_id=player_id,
        critical_card_id=card_id,
        critical_card_name=critical_card_name(card_id),
        timing=critical_card_timing(card_id),
        effect_triggered=(
            effect_triggered
            if card_id != SONO_ANCORA_QUI
            else target_player_id is not None
        ),
        target_player_id=target_player_id if card_id == SONO_ANCORA_QUI else None,
        life_delta_player=life_delta_player,
        life_delta_targets=life_delta_targets,
        deck_position=deck_position,
        player_lives_after=player.lives,
        player_critical_wounds_after=player.critical_wounds,
    )
    critical_events.append(event)
    if card_id == BRICIOLA_NASCOSTA:
        pending_life_recovery_events[player_id].append(event)


def _animal_event(
    player: PlayerState,
    card: Card,
    effect_id: str,
    effect_name: str,
    timing: str,
    status: str,
    target_player_id: int | None = None,
    value_before: int | None = None,
    value_after: int | None = None,
    amount: int | None = None,
    actual_amount: int | None = None,
    reason: str | None = None,
) -> AnimalEffectEvent:
    """Build internal animal-effect telemetry for a played card."""

    return AnimalEffectEvent(
        player_id=player.player_id,
        animal=ANIMAL_DISPLAY_NAMES[get_animal_for_color(player.color)],
        card_color=card.color.name,
        card_value=card.value,
        effect_id=effect_id,
        effect_name=effect_name,
        timing=timing,
        status=status,
        target_player_id=target_player_id,
        value_before=value_before,
        value_after=value_after,
        amount=amount,
        actual_amount=actual_amount,
        reason=reason,
    )


def _collect_comparison_animal_events(
    player_map: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    effective_comparison_values: Mapping[int, int],
) -> list[AnimalEffectEvent]:
    """Collect telemetry for animal effects that change comparison values."""

    animal_events: list[AnimalEffectEvent] = []
    comparison_effect_names = {
        CONIGLIO_SCATTO_IMPROVVISO: "Scatto Improvviso",
    }
    for player_id, card in selected_cards.items():
        player = player_map[player_id]
        effective_value = effective_comparison_values[player_id]
        if (
            config.animal_card_effects_enabled
            and PANDA_GRANDE_LETARGO in player.active_animal_effects
            and effective_value == 3
        ):
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=PANDA_GRANDE_LETARGO,
                    effect_name="Grande Letargo",
                    timing="comparison",
                    status="applied",
                    value_before=card.comparison_value,
                    value_after=effective_value,
                )
            )
            continue

        effect_id = get_active_own_animal_effect_id(player, card, config)
        if (
            effect_id in comparison_effect_names
            and effective_value != card.comparison_value
        ):
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=effect_id,
                    effect_name=comparison_effect_names[effect_id],
                    timing="comparison",
                    status="applied",
                    value_before=card.comparison_value,
                    value_after=effective_value,
                )
            )

    return animal_events


def _collect_consumption_animal_event(
    player: PlayerState,
    card: Card,
    config: GameConfig,
    value_before: int,
    value_after: int,
    animal_events: list[AnimalEffectEvent],
    reason: str | None = None,
) -> None:
    """Collect telemetry for animal effects that change base consumption."""

    effect_id = get_active_own_animal_effect_id(player, card, config)
    if effect_id == CONIGLIO_PASSO_LEGGERO and value_after != value_before:
        animal_events.append(
            _animal_event(
                player=player,
                card=card,
                effect_id=CONIGLIO_PASSO_LEGGERO,
                effect_name="Passo Leggero",
                timing="consumption",
                status="applied",
                value_before=value_before,
                value_after=value_after,
                amount=value_before - value_after,
                actual_amount=value_before - value_after,
                reason=reason,
            )
        )
    elif effect_id == PANDA_RESPIRO_LENTO and value_after != value_before:
        animal_events.append(
            _animal_event(
                player=player,
                card=card,
                effect_id=PANDA_RESPIRO_LENTO,
                effect_name="Respiro Lento",
                timing="consumption",
                status="applied",
                value_before=value_before,
                value_after=value_after,
                amount=1,
                actual_amount=1,
                reason=reason,
            )
        )


def _apply_animal_comparison_effects(
    player_map: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    effective_comparison_values: dict[int, int],
    active_effects_by_player: Mapping[int, list[str]],
    animal_events: list[AnimalEffectEvent],
) -> None:
    """Apply supported after-reveal animal effects to round comparison values."""

    for player_id, card in selected_cards.items():
        source = player_map[player_id]
        effect_id = get_active_own_animal_effect_id(source, card, config)
        if effect_id != SCIMMIA_BUCCIA_DI_BANANA:
            continue

        valid_targets = valid_comparison_value_targets(
            source,
            player_map,
            selected_cards,
        )
        target = choose_comparison_value_target(valid_targets)
        if target is None:
            animal_events.append(
                _animal_event(
                    player=source,
                    card=card,
                    effect_id=SCIMMIA_BUCCIA_DI_BANANA,
                    effect_name="Buccia di Banana",
                    timing="comparison",
                    status="not_activated",
                    reason="no_valid_target",
                )
            )
            continue

        value_before = effective_comparison_values[target.player_id]
        modified_value = apply_comparison_value_modifier(
            value_before,
            -1,
            target_active_effects=active_effects_by_player.get(target.player_id, []),
            caused_by_opponent=True,
        )
        value_after = max(1, modified_value)
        effective_comparison_values[target.player_id] = value_after
        is_blocked = (
            value_after == value_before
            and RESPIRO_CALMO in active_effects_by_player.get(target.player_id, [])
        )
        is_minimum = value_after == value_before and value_before == 1
        if is_blocked:
            status = "blocked"
            reason = "blocked_by_respiro_calmo"
        elif is_minimum:
            status = "applied"
            reason = "minimum_1"
        else:
            status = "applied"
            reason = "target_selected"

        animal_events.append(
            _animal_event(
                player=source,
                card=card,
                effect_id=SCIMMIA_BUCCIA_DI_BANANA,
                effect_name="Buccia di Banana",
                timing="comparison",
                status=status,
                target_player_id=target.player_id,
                value_before=value_before,
                value_after=value_after,
                amount=1,
                actual_amount=value_before - value_after,
                reason=reason,
            )
        )


def _find_finta_innocente_excluded_players(
    player_map: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    animal_events: list[AnimalEffectEvent],
) -> set[int]:
    """Return players excluded from hunger by supported animal-card effects."""

    excluded_player_ids: set[int] = set()
    for player_id, card in selected_cards.items():
        player = player_map[player_id]
        effect_id = get_active_own_animal_effect_id(player, card, config)
        if effect_id != SCIMMIA_FINTA_INNOCENTE:
            continue

        has_other_printed_one = any(
            other_player_id != player_id and other_card.value == 1
            for other_player_id, other_card in selected_cards.items()
        )
        if has_other_printed_one:
            excluded_player_ids.add(player_id)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=SCIMMIA_FINTA_INNOCENTE,
                    effect_name="Finta Innocente",
                    timing="hunger_assignment",
                    status="applied",
                    reason="other_printed_one",
                )
            )
        else:
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=SCIMMIA_FINTA_INNOCENTE,
                    effect_name="Finta Innocente",
                    timing="hunger_assignment",
                    status="not_activated",
                    reason="no_other_printed_one",
                )
            )

    return excluded_player_ids


def _schedule_animal_life_recoveries(
    player_map: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    critical_wound_player_ids: set[int],
    pending_life_recoveries: dict[int, int],
    animal_events: list[AnimalEffectEvent],
) -> None:
    """Schedule same-round recovery from supported animal-card effects."""

    for player_id, card in selected_cards.items():
        player = player_map[player_id]
        effect_id = get_active_own_animal_effect_id(player, card, config)
        if effect_id == PANDA_RIPOSO_FORZATO:
            schedule_life_recovery(pending_life_recoveries, player_id, 1)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=PANDA_RIPOSO_FORZATO,
                    effect_name="Riposo Forzato",
                    timing="recovery_schedule",
                    status="scheduled",
                    amount=1,
                )
            )
        elif (
            effect_id == SCOIATTOLO_PICCOLA_RISERVA
            and player_id not in critical_wound_player_ids
        ):
            schedule_life_recovery(pending_life_recoveries, player_id, 1)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=SCOIATTOLO_PICCOLA_RISERVA,
                    effect_name="Piccola Riserva",
                    timing="recovery_schedule",
                    status="scheduled",
                    amount=1,
                )
            )


def _schedule_next_round_animal_effects(
    player_map: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    critical_wound_player_ids: set[int],
    animal_events: list[AnimalEffectEvent],
) -> None:
    """Register supported next-round animal-card effects."""

    for player_id, card in selected_cards.items():
        player = player_map[player_id]
        effect_id = get_active_own_animal_effect_id(player, card, config)
        if effect_id == PANDA_GRANDE_LETARGO:
            player.active_animal_effects.append(PANDA_GRANDE_LETARGO)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=PANDA_GRANDE_LETARGO,
                    effect_name="Grande Letargo",
                    timing="next_round_schedule",
                    status="scheduled",
                )
            )
        elif effect_id == CONIGLIO_GRANDE_BALZO:
            player.active_animal_effects.append(CONIGLIO_GRANDE_BALZO_DEBT)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=CONIGLIO_GRANDE_BALZO,
                    effect_name="Grande Balzo",
                    timing="consumption",
                    status="applied",
                    value_before=4,
                    value_after=0,
                    amount=4,
                    actual_amount=4,
                    reason="current_round_free",
                )
            )
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=CONIGLIO_GRANDE_BALZO,
                    effect_name="Grande Balzo",
                    timing="next_round_schedule",
                    status="scheduled",
                    amount=3,
                    reason="triple_next_consumption",
                )
            )
        elif effect_id == SCOIATTOLO_GHIANDA_NASCOSTA:
            player.active_animal_effects.append(SCOIATTOLO_GHIANDA_NASCOSTA)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=SCOIATTOLO_GHIANDA_NASCOSTA,
                    effect_name="Ghianda Nascosta",
                    timing="next_round_schedule",
                    status="scheduled",
                    amount=1,
                )
            )
        elif (
            effect_id == SCOIATTOLO_DISPENSA_ORDINATA
            and player_id not in critical_wound_player_ids
        ):
            player.active_animal_effects.append(SCOIATTOLO_DISPENSA_ORDINATA)
            animal_events.append(
                _animal_event(
                    player=player,
                    card=card,
                    effect_id=SCOIATTOLO_DISPENSA_ORDINATA,
                    effect_name="Dispensa Ordinata",
                    timing="next_round_schedule",
                    status="scheduled",
                    amount=1,
                )
            )


def _schedule_animal_extra_consumptions(
    player_map: Mapping[int, PlayerState],
    selected_cards: Mapping[int, Card],
    config: GameConfig,
    critical_wound_player_ids: set[int],
    pending_extra_consumptions: list[PendingExtraConsumption],
    animal_events: list[AnimalEffectEvent],
) -> None:
    """Schedule supported animal-card extra consumptions for the extra phase."""

    for player_id, card in selected_cards.items():
        source = player_map[player_id]
        effect_id = get_active_own_animal_effect_id(source, card, config)
        if effect_id != SCIMMIA_BANANA_RUBATA:
            continue
        if player_id in critical_wound_player_ids:
            animal_events.append(
                _animal_event(
                    player=source,
                    card=card,
                    effect_id=SCIMMIA_BANANA_RUBATA,
                    effect_name="Banana Rubata",
                    timing="extra_schedule",
                    status="not_activated",
                    reason="received_affamato",
                )
            )
            continue

        target = _choose_banana_rubata_target(
            player_map,
            source_player_id=player_id,
            critical_wound_player_ids=critical_wound_player_ids,
        )
        if target is None:
            animal_events.append(
                _animal_event(
                    player=source,
                    card=card,
                    effect_id=SCIMMIA_BANANA_RUBATA,
                    effect_name="Banana Rubata",
                    timing="extra_schedule",
                    status="not_activated",
                    reason="no_valid_target",
                )
            )
            continue

        schedule_extra_consumption(
            pending_extra_consumptions,
            source_player_id=player_id,
            target_player_id=target.player_id,
            amount=1,
            effect_id=SCIMMIA_BANANA_RUBATA,
            recovery_player_id=player_id,
            source_card=card,
        )
        animal_events.append(
            _animal_event(
                player=source,
                card=card,
                effect_id=SCIMMIA_BANANA_RUBATA,
                effect_name="Banana Rubata",
                timing="extra_schedule",
                status="scheduled",
                target_player_id=target.player_id,
                amount=1,
                reason="target_selected",
            )
        )


def _choose_banana_rubata_target(
    player_map: Mapping[int, PlayerState],
    source_player_id: int,
    critical_wound_player_ids: set[int],
) -> PlayerState | None:
    """Choose Banana Rubata target with deterministic player-id fallback."""

    valid_targets = [
        target
        for target in player_map.values()
        if target.player_id != source_player_id
        and target.is_alive
        and target.player_id not in critical_wound_player_ids
        and target.lives > 0
    ]
    if not valid_targets:
        return None
    return min(valid_targets, key=lambda target: target.player_id)


def schedule_life_recovery(
    pending_life_recoveries: dict[int, int],
    player_id: int,
    amount: int,
) -> None:
    """Schedule same-round life/scorte recovery for the recovery phase."""

    if amount <= 0:
        return

    pending_life_recoveries[player_id] = (
        pending_life_recoveries.get(player_id, 0) + amount
    )


def apply_pending_life_recoveries(
    player_map: Mapping[int, PlayerState],
    pending_life_recoveries: Mapping[int, int],
    config: GameConfig,
    critical_life_delta_by_player: dict[int, int] | None = None,
    pending_life_recovery_events: Mapping[int, list[CriticalCardEvent]] | None = None,
) -> dict[int, int]:
    """Apply scheduled recovery after damage and before eliminations."""

    applied_recoveries: dict[int, int] = {}
    for player_id, amount in pending_life_recoveries.items():
        if amount <= 0:
            continue

        player = player_map[player_id]
        before = player.lives
        player.lives = min(config.initial_lives, player.lives + amount)
        recovered = player.lives - before
        applied_recoveries[player_id] = recovered

        if recovered:
            player.life_gained_from_critical_cards += recovered
            if critical_life_delta_by_player is not None:
                critical_life_delta_by_player[player_id] = (
                    critical_life_delta_by_player.get(player_id, 0) + recovered
                )

        remaining_recovered = recovered
        for event in (pending_life_recovery_events or {}).get(player_id, []):
            event_delta = min(1, remaining_recovered)
            event.life_delta_player = event_delta
            event.effect_triggered = event_delta > 0
            event.player_lives_after = player.lives
            event.player_critical_wounds_after = player.critical_wounds
            remaining_recovered -= event_delta

    return applied_recoveries


def apply_pending_animal_life_recoveries(
    player_map: Mapping[int, PlayerState],
    pending_life_recoveries: Mapping[int, int],
    config: GameConfig,
) -> dict[int, int]:
    """Apply scheduled animal-card recovery in the recovery phase."""

    applied_recoveries: dict[int, int] = {}
    for player_id, amount in pending_life_recoveries.items():
        if amount <= 0:
            continue

        player = player_map[player_id]
        before = player.lives
        player.lives = min(config.initial_lives, player.lives + amount)
        applied_recoveries[player_id] = player.lives - before

    return applied_recoveries


def schedule_extra_consumption(
    pending_extra_consumptions: list[PendingExtraConsumption],
    source_player_id: int,
    target_player_id: int,
    amount: int,
    effect_id: str,
    event: CriticalCardEvent | None = None,
    recovery_player_id: int | None = None,
    source_card: Card | None = None,
) -> None:
    """Schedule extra consumption for the explicit extra-consumption phase."""

    if amount <= 0:
        return

    pending_extra_consumptions.append(
        PendingExtraConsumption(
            source_player_id=source_player_id,
            target_player_id=target_player_id,
            amount=amount,
            effect_id=effect_id,
            event=event,
            recovery_player_id=recovery_player_id,
            source_card=source_card,
        )
    )


def is_valid_extra_consumption_target(
    player_map: Mapping[int, PlayerState],
    target_player_id: int,
    critical_wound_player_ids: set[int],
) -> bool:
    """Return whether a target can receive extra consumption now."""

    target = player_map.get(target_player_id)
    if target is None:
        return False
    if not target.is_alive:
        return False
    if target.player_id in critical_wound_player_ids:
        return False
    return target.lives > 0


def apply_pending_extra_consumptions(
    player_map: Mapping[int, PlayerState],
    pending_extra_consumptions: list[PendingExtraConsumption],
    critical_wound_player_ids: set[int],
    critical_life_delta_by_player: dict[int, int] | None = None,
    pending_animal_life_recoveries: dict[int, int] | None = None,
    animal_events: list[AnimalEffectEvent] | None = None,
) -> dict[int, int]:
    """Apply scheduled extra consumption after base consumption."""

    applied_by_player = {player_id: 0 for player_id in player_map}
    for pending in pending_extra_consumptions:
        target = player_map.get(pending.target_player_id)
        if target is None:
            _collect_banana_rubata_extra_apply_event(
                player_map=player_map,
                pending=pending,
                actual_consumed=0,
                animal_events=animal_events,
                reason="target_not_valid",
            )
            continue

        actual_consumed = 0
        if is_valid_extra_consumption_target(
            player_map,
            pending.target_player_id,
            critical_wound_player_ids,
        ):
            before = target.lives
            apply_life_loss(target, pending.amount)
            actual_consumed = before - target.lives
            applied_by_player[pending.target_player_id] += actual_consumed
            if pending.effect_id == MORSO_DELLA_FAME and actual_consumed:
                target.life_lost_from_critical_cards += actual_consumed
                if critical_life_delta_by_player is not None:
                    critical_life_delta_by_player[target.player_id] = (
                        critical_life_delta_by_player.get(target.player_id, 0)
                        - actual_consumed
                    )
            reason = "extra_consumed" if actual_consumed else "actual_consumed_zero"
            _collect_banana_rubata_extra_apply_event(
                player_map=player_map,
                pending=pending,
                actual_consumed=actual_consumed,
                animal_events=animal_events,
                reason=reason,
            )
            if (
                pending.recovery_player_id is not None
                and pending_animal_life_recoveries is not None
                and actual_consumed
            ):
                schedule_life_recovery(
                    pending_animal_life_recoveries,
                    pending.recovery_player_id,
                    1,
                )
                _collect_banana_rubata_recovery_schedule_event(
                    player_map=player_map,
                    pending=pending,
                    animal_events=animal_events,
                )
        else:
            _collect_banana_rubata_extra_apply_event(
                player_map=player_map,
                pending=pending,
                actual_consumed=actual_consumed,
                animal_events=animal_events,
                reason="actual_consumed_zero",
            )

        if pending.event is not None:
            pending.event.effect_triggered = actual_consumed > 0
            pending.event.life_delta_targets = (
                {target.player_id: -actual_consumed} if actual_consumed else {}
            )
            pending.event.player_lives_after = player_map[
                pending.source_player_id
            ].lives
            pending.event.player_critical_wounds_after = player_map[
                pending.source_player_id
            ].critical_wounds

    return applied_by_player


def _collect_banana_rubata_extra_apply_event(
    player_map: Mapping[int, PlayerState],
    pending: PendingExtraConsumption,
    actual_consumed: int,
    animal_events: list[AnimalEffectEvent] | None,
    reason: str,
) -> None:
    """Collect telemetry for Banana Rubata extra consumption application."""

    if (
        animal_events is None
        or pending.effect_id != SCIMMIA_BANANA_RUBATA
        or pending.source_card is None
    ):
        return

    source = player_map.get(pending.source_player_id)
    if source is None:
        return

    animal_events.append(
        _animal_event(
            player=source,
            card=pending.source_card,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="extra_apply",
            status="applied" if actual_consumed > 0 else "not_applied",
            target_player_id=pending.target_player_id,
            amount=pending.amount,
            actual_amount=actual_consumed,
            reason=reason,
        )
    )


def _collect_banana_rubata_recovery_schedule_event(
    player_map: Mapping[int, PlayerState],
    pending: PendingExtraConsumption,
    animal_events: list[AnimalEffectEvent] | None,
) -> None:
    """Collect telemetry for Banana Rubata recovery scheduling."""

    if (
        animal_events is None
        or pending.effect_id != SCIMMIA_BANANA_RUBATA
        or pending.source_card is None
        or pending.recovery_player_id is None
    ):
        return

    source = player_map.get(pending.recovery_player_id)
    if source is None:
        return

    animal_events.append(
        _animal_event(
            player=source,
            card=pending.source_card,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="recovery_schedule",
            status="scheduled",
            target_player_id=pending.target_player_id,
            amount=1,
            reason="extra_consumed",
        )
    )


def _validate_active_critical_effects_for_profile(
    active_effects_by_player: Mapping[int, list[str]],
    config: GameConfig,
) -> None:
    """Reject active effects that do not belong to the configured profile."""

    profile = get_critical_deck_profile(config.critical_deck_profile_id)
    invalid_effects = sorted(
        {
            effect_id
            for effects in active_effects_by_player.values()
            for effect_id in effects
            if effect_id not in profile.card_ids
        }
    )
    if invalid_effects:
        raise ValueError(
            "Active critical effects are not valid for profile "
            f"'{profile.profile_id}': " + ", ".join(invalid_effects)
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


def _valid_nonimmune_opponent_targets(
    player_map: Mapping[int, PlayerState],
    source_id: int,
    critical_wound_player_ids: set[int],
) -> list[PlayerState]:
    """Return opponents that can receive next-round critical effect damage."""

    return [
        target
        for target in player_map.values()
        if target.player_id != source_id
        and target.is_alive
        and target.player_id not in critical_wound_player_ids
    ]


def _choose_single_critical_effect_target(
    source: PlayerState,
    effect_id: str,
    valid_targets: list[PlayerState],
    strategy: BaseStrategy | None,
    rng: Random,
    game_state: dict | None,
) -> PlayerState | None:
    """Choose one valid target for a critical-card effect."""

    if strategy is None:
        return choose_fallback_critical_effect_target(valid_targets)

    target = strategy.choose_critical_effect_target(
        game_state,
        source,
        effect_id,
        valid_targets,
        rng,
    )
    if target not in valid_targets:
        target = choose_fallback_critical_effect_target(valid_targets)
    return target


def _calculate_base_damage_with_critical_effects(
    player: PlayerState,
    card: Card,
    config: GameConfig,
    received_critical_wound: bool,
    color_effects_enabled: bool,
    active_effects: list[str],
    critical_events: list[CriticalCardEvent],
    game_id: int,
    round_number: int,
    animal_events: list[AnimalEffectEvent],
    selected_cards: Mapping[int, Card],
    player_map: Mapping[int, PlayerState],
    active_animal_effects: list[str] | None = None,
) -> int:
    """Calculate base damage with supported next-round critical effects."""

    active_animal_effects = active_animal_effects or []
    has_grande_balzo_debt = (
        CONIGLIO_GRANDE_BALZO_DEBT in active_animal_effects
        and has_coniglio_grande_balzo_debt(player, config)
    )

    if received_critical_wound and not has_grande_balzo_debt:
        if RAZIONE_RISPARMIATA in active_effects:
            critical_events.append(
                _effect_event(
                    game_id,
                    round_number,
                    player,
                    RAZIONE_RISPARMIATA,
                    effect_triggered=False,
                )
            )
        return 0

    base_consumption = card.consumption_value
    damage = _normal_effective_consumption_for_round(
        player=player,
        card=card,
        config=config,
        received_critical_wound=received_critical_wound,
    )
    consumption_reason = None
    effect_id = get_active_own_animal_effect_id(player, card, config)
    if effect_id == CONIGLIO_PASSO_LEGGERO and not received_critical_wound:
        consumption_reason = "no_affamato"
    elif effect_id == PANDA_RESPIRO_LENTO and not received_critical_wound:
        panda_wounds_before_current = player.critical_wounds - (
            1 if received_critical_wound else 0
        )
        if panda_wounds_before_current >= 2:
            consumption_reason = "has_at_least_2_affamato"
    _collect_consumption_animal_event(
        player=player,
        card=card,
        config=config,
        value_before=base_consumption,
        value_after=damage,
        animal_events=animal_events,
        reason=consumption_reason,
    )
    if has_grande_balzo_debt:
        debt_before = damage
        damage = apply_coniglio_grande_balzo_debt(debt_before)
        animal_events.append(
            _animal_event(
                player=player,
                card=card,
                effect_id=CONIGLIO_GRANDE_BALZO,
                effect_name="Grande Balzo",
                timing="consumption",
                status="applied",
                value_before=debt_before,
                value_after=damage,
                amount=damage - debt_before,
                actual_amount=damage,
                reason="triple_debt_applied",
            )
        )
    if RAZIONE_RISPARMIATA in active_effects and damage > 0:
        before = damage
        damage = max(1, damage - 1)
        prevented = before - damage
        critical_events.append(
            _effect_event(
                game_id,
                round_number,
                player,
                RAZIONE_RISPARMIATA,
                effect_triggered=prevented > 0,
                prevented_damage=prevented,
            )
        )
        player.damage_prevented_by_critical_cards += prevented

    reduction = 0
    if color_effects_enabled and card.color == player.color:
        reduction = 2 if SANGUE_FREDDO in active_effects else 1
        damage -= reduction

    minimum_damage = 0 if effect_id == CONIGLIO_GRANDE_BALZO else 1
    final_damage = max(minimum_damage, damage)
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


def _normal_effective_consumption_for_round(
    player: PlayerState,
    card: Card,
    config: GameConfig,
    received_critical_wound: bool,
) -> int:
    """Return normal same-round consumption before special debt multipliers."""

    effect_id = get_active_own_animal_effect_id(player, card, config)
    consumption = card.consumption_value
    if effect_id == PANDA_RESPIRO_LENTO:
        wounds_before_current = player.critical_wounds - (
            1 if received_critical_wound else 0
        )
        if wounds_before_current >= 2:
            consumption = 2
    elif effect_id == CONIGLIO_PASSO_LEGGERO and not received_critical_wound:
        consumption = 1
    elif effect_id == CONIGLIO_GRANDE_BALZO:
        consumption = 0

    return max(0, consumption)


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

        valid_targets = _valid_nonimmune_opponent_targets(
            player_map,
            source_id,
            critical_wound_player_ids,
        )
        target = _choose_single_critical_effect_target(
            source,
            COLPO_DI_CODA,
            valid_targets,
            strategies.get(source_id),
            rng,
            game_state,
        )

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


def _schedule_morso_della_fame(
    player_map: dict[int, PlayerState],
    critical_wound_player_ids: set[int],
    active_effects_by_player: Mapping[int, list[str]],
    strategies: Mapping[int, BaseStrategy],
    rng: Random,
    game_state: dict | None,
    critical_events: list[CriticalCardEvent],
    pending_extra_consumptions: list[PendingExtraConsumption],
    game_id: int,
    round_number: int,
) -> None:
    """Schedule Morso della Fame extra consumption for the extra phase."""

    for source_id in sorted(critical_wound_player_ids):
        source = player_map[source_id]
        if MORSO_DELLA_FAME not in active_effects_by_player.get(source_id, []):
            continue

        valid_targets = _valid_nonimmune_opponent_targets(
            player_map,
            source_id,
            critical_wound_player_ids,
        )
        target = _choose_single_critical_effect_target(
            source,
            MORSO_DELLA_FAME,
            valid_targets,
            strategies.get(source_id),
            rng,
            game_state,
        )

        life_delta_targets = {}
        target_player_id = None
        triggered = target is not None
        if target is not None:
            target_player_id = target.player_id

        event = CriticalCardEvent(
            game_id=game_id,
            round_number=round_number,
            draw_order=None,
            player_id=source_id,
            critical_card_id=MORSO_DELLA_FAME,
            critical_card_name=critical_card_name(MORSO_DELLA_FAME),
            timing="next_round",
            effect_triggered=triggered,
            target_player_id=target_player_id,
            life_delta_targets=life_delta_targets,
            player_lives_after=source.lives,
            player_critical_wounds_after=source.critical_wounds,
        )
        critical_events.append(event)
        if target is not None:
            schedule_extra_consumption(
                pending_extra_consumptions,
                source_player_id=source_id,
                target_player_id=target.player_id,
                amount=2,
                effect_id=MORSO_DELLA_FAME,
                event=event,
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


def _consume_active_animal_effects(
    player_map: dict[int, PlayerState],
    active_effects_by_player: Mapping[int, list[str]],
    selected_cards: Mapping[int, Card],
    animal_events: list[AnimalEffectEvent],
) -> None:
    """Consume animal effects that were active at the start of the round."""

    for player_id, effects in active_effects_by_player.items():
        player = player_map[player_id]
        for effect_id in effects:
            if effect_id in player.active_animal_effects:
                player.active_animal_effects.remove(effect_id)
                if effect_id == PANDA_GRANDE_LETARGO and player_id in selected_cards:
                    animal_events.append(
                        _animal_event(
                            player=player,
                            card=selected_cards[player_id],
                            effect_id=PANDA_GRANDE_LETARGO,
                            effect_name="Grande Letargo",
                            timing="next_round_consume",
                            status="consumed",
                        )
                    )
                elif (
                    effect_id == CONIGLIO_GRANDE_BALZO_DEBT
                    and player_id in selected_cards
                ):
                    animal_events.append(
                        _animal_event(
                            player=player,
                            card=selected_cards[player_id],
                            effect_id=CONIGLIO_GRANDE_BALZO,
                            effect_name="Grande Balzo",
                            timing="next_round_consume",
                            status="consumed",
                            reason="triple_debt_consumed",
                        )
                    )
