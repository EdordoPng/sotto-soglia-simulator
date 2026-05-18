"""Round-level result models."""

from dataclasses import dataclass, field
from collections.abc import Iterable, Mapping

from sotto_soglia.config import GameConfig
from sotto_soglia.models import Card
from sotto_soglia.models import PlayerState
from sotto_soglia.rules import (
    apply_life_loss,
    calculate_base_damage,
    calculate_extra_damage,
    find_lowest_value_players,
    resolve_eliminations,
)


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
) -> RoundResult:
    """Resolve one simultaneous reveal round and mutate player states."""

    player_map = _players_by_id(players)
    selected_cards = dict(selected_cards)

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

    critical_wound_player_ids = find_lowest_value_players(selected_cards)
    lowest_value = min((card.value for card in selected_cards.values()), default=None)

    for player_id in critical_wound_player_ids:
        player_map[player_id].critical_wounds += 1

    base_damage_by_player = {
        player_id: calculate_base_damage(
            player_map[player_id],
            card,
            player_id in critical_wound_player_ids,
            color_effects_enabled=config.color_effects_enabled,
        )
        for player_id, card in selected_cards.items()
    }

    extra_damage_by_player = calculate_extra_damage(
        player_map,
        selected_cards,
        critical_wound_player_ids,
        color_effects_enabled=config.color_effects_enabled,
    )

    total_damage_by_player = {
        player_id: base_damage_by_player.get(player_id, 0)
        + extra_damage_by_player.get(player_id, 0)
        for player_id in player_map
    }

    for player_id, damage in total_damage_by_player.items():
        apply_life_loss(player_map[player_id], damage)

    eliminated_players = resolve_eliminations(player_map, config)

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
    )
