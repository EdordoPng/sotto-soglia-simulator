"""Statistics aggregation for simulation results."""

from collections.abc import Sequence

from sotto_soglia.critical import (
    BENDAGGIO_EMERGENZA,
    COLPO_DI_CODA,
    FERITA_ESPOSTA,
    MANO_LUCIDA,
    MANO_TREMANTE,
    SANGUE_FREDDO,
    SCUDO_ISTINTIVO,
    SONO_ANCORA_QUI,
    CRITICAL_CARD_IDS,
    V05_HUNGER_CARD_IDS,
)
from sotto_soglia.animal_effects import (
    ANIMAL_DISPLAY_NAMES,
    get_animal_for_color,
    get_display_color_for_technical_color,
)
from sotto_soglia.game import GameResult
from sotto_soglia.models import Color, EliminationReason


ALL_CRITICAL_CARD_IDS = CRITICAL_CARD_IDS + V05_HUNGER_CARD_IDS


class StatisticAggregator:
    """Aggregate base metrics from completed games."""

    def aggregate(self, game_results: Sequence[GameResult]) -> dict:
        """Return aggregate statistics for a list of game results."""

        games_count = len(game_results)
        if games_count == 0:
            return self._empty_stats()

        rounds = [result.rounds_count for result in game_results]
        draw_count = sum(1 for result in game_results if result.is_draw)
        wins_by_player_id: dict[int, int] = {}
        wins_by_color = {color.name: 0 for color in Color}
        wins_by_animal = self._zero_wins_by_animal()
        wins_by_display_color = self._zero_wins_by_display_color()
        wins_by_strategy: dict[str, int] = {}
        winner_lives: list[int] = []
        winner_critical_wounds: list[int] = []

        eliminations_by_lives = 0
        eliminations_by_critical_wounds = 0

        for result in game_results:
            player_by_id = {
                player.player_id: player
                for player in result.final_players
            }
            for player in result.final_players:
                wins_by_strategy.setdefault(player.strategy_name, 0)
            for player in result.final_players:
                if not result.is_draw and player.player_id in result.winner_ids:
                    continue
                if player.elimination_reason == EliminationReason.LIVES:
                    eliminations_by_lives += 1
                elif player.elimination_reason == EliminationReason.CRITICAL_WOUNDS:
                    eliminations_by_critical_wounds += 1

            # Draws are tracked separately and do not count as wins in this phase.
            if result.is_draw:
                continue

            for winner_id in result.winner_ids:
                winner = player_by_id[winner_id]
                wins_by_player_id[winner_id] = wins_by_player_id.get(winner_id, 0) + 1
                wins_by_color[winner.color.name] += 1
                wins_by_animal[
                    self._animal_display_name_for_color(winner.color)
                ] += 1
                wins_by_display_color[
                    get_display_color_for_technical_color(winner.color)
                ] += 1
                wins_by_strategy[winner.strategy_name] += 1
                winner_lives.append(winner.lives)
                winner_critical_wounds.append(winner.critical_wounds)

        stats = {
            "games_count": games_count,
            "average_rounds": sum(rounds) / games_count,
            "min_rounds": min(rounds),
            "max_rounds": max(rounds),
            "draw_count": draw_count,
            "draw_rate": draw_count / games_count,
            "wins_by_player_id": wins_by_player_id,
            "wins_by_color": wins_by_color,
            "wins_by_animal": wins_by_animal,
            "wins_by_display_color": wins_by_display_color,
            "wins_by_strategy": wins_by_strategy,
            "win_rate_by_player_id": {
                player_id: wins / games_count
                for player_id, wins in wins_by_player_id.items()
            },
            "win_rate_by_color": {
                color: wins / games_count
                for color, wins in wins_by_color.items()
            },
            "win_rate_by_animal": {
                animal: wins / games_count
                for animal, wins in wins_by_animal.items()
            },
            "win_rate_by_display_color": {
                display_color: wins / games_count
                for display_color, wins in wins_by_display_color.items()
            },
            "win_rate_by_strategy": {
                strategy: wins / games_count
                for strategy, wins in wins_by_strategy.items()
            },
            "eliminations_by_lives": eliminations_by_lives,
            "eliminations_by_critical_wounds": eliminations_by_critical_wounds,
            "average_winner_lives": self._average(winner_lives),
            "average_winner_critical_wounds": self._average(winner_critical_wounds),
        }
        stats.update(self._critical_card_stats(game_results))
        return stats

    def _empty_stats(self) -> dict:
        """Return a stable empty aggregate structure."""

        stats = {
            "games_count": 0,
            "average_rounds": 0.0,
            "min_rounds": 0,
            "max_rounds": 0,
            "draw_count": 0,
            "draw_rate": 0.0,
            "wins_by_player_id": {},
            "wins_by_color": {color.name: 0 for color in Color},
            "wins_by_animal": self._zero_wins_by_animal(),
            "wins_by_display_color": self._zero_wins_by_display_color(),
            "wins_by_strategy": {},
            "win_rate_by_player_id": {},
            "win_rate_by_color": {color.name: 0.0 for color in Color},
            "win_rate_by_animal": {
                animal: 0.0
                for animal in self._zero_wins_by_animal()
            },
            "win_rate_by_display_color": {
                display_color: 0.0
                for display_color in self._zero_wins_by_display_color()
            },
            "win_rate_by_strategy": {},
            "eliminations_by_lives": 0,
            "eliminations_by_critical_wounds": 0,
            "average_winner_lives": 0.0,
            "average_winner_critical_wounds": 0.0,
        }
        stats.update(self._empty_critical_card_stats())
        return stats

    def _average(self, values: Sequence[int]) -> float:
        """Return the numeric average or zero for an empty sequence."""

        if not values:
            return 0.0
        return sum(values) / len(values)

    def _zero_wins_by_animal(self) -> dict[str, int]:
        """Return stable zero win counters by semantic animal."""

        return {
            self._animal_display_name_for_color(color): 0
            for color in Color
        }

    def _zero_wins_by_display_color(self) -> dict[str, int]:
        """Return stable zero win counters by physical display color."""

        return {
            get_display_color_for_technical_color(color): 0
            for color in Color
        }

    def _animal_display_name_for_color(self, color: Color) -> str:
        """Return the animal display name for a legacy technical color."""

        return ANIMAL_DISPLAY_NAMES[get_animal_for_color(color)]

    def _empty_critical_card_stats(self) -> dict:
        """Return stable zero critical-card aggregate metrics."""

        return {
            "critical_cards_drawn_total": 0,
            "critical_effects_triggered_total": 0,
            "critical_effects_by_card": {
                card_id: 0 for card_id in ALL_CRITICAL_CARD_IDS
            },
            "average_life_delta_by_card": {
                card_id: 0.0 for card_id in ALL_CRITICAL_CARD_IDS
            },
            "total_life_gained_from_critical_cards": 0,
            "total_life_lost_from_critical_cards": 0,
            "total_damage_prevented_by_critical_cards": 0,
            "colpo_di_coda_trigger_count": 0,
            "sono_ancora_qui_trigger_count": 0,
            "bendaggio_trigger_count": 0,
            "mano_lucida_trigger_count": 0,
            "mano_tremante_trigger_count": 0,
            "sangue_freddo_trigger_count": 0,
            "scudo_istintivo_trigger_count": 0,
            "ferita_esposta_trigger_count": 0,
            "critical_card_stats": {
                card_id: {
                    "draw_count": 0,
                    "activation_count": 0,
                    "total_life_delta": 0,
                    "average_life_delta": 0.0,
                    "win_count_after_draw": 0,
                    "elimination_count_after_draw": 0,
                }
                for card_id in ALL_CRITICAL_CARD_IDS
            },
        }

    def _critical_card_stats(self, game_results: Sequence[GameResult]) -> dict:
        """Aggregate critical wound card metrics from game event logs."""

        stats = self._empty_critical_card_stats()
        life_delta_totals = {card_id: 0 for card_id in ALL_CRITICAL_CARD_IDS}
        draw_counts = {card_id: 0 for card_id in ALL_CRITICAL_CARD_IDS}

        for result in game_results:
            winner_ids = set(result.winner_ids) if not result.is_draw else set()
            player_by_id = {
                player.player_id: player
                for player in result.final_players
            }
            for player in result.final_players:
                stats["total_life_gained_from_critical_cards"] += (
                    player.life_gained_from_critical_cards
                )
                stats["total_life_lost_from_critical_cards"] += (
                    player.life_lost_from_critical_cards
                )
                stats["total_damage_prevented_by_critical_cards"] += (
                    player.damage_prevented_by_critical_cards
                )

            for event in result.critical_events:
                card_id = event.critical_card_id
                if card_id not in ALL_CRITICAL_CARD_IDS:
                    continue
                life_delta = event.life_delta_player + sum(
                    event.life_delta_targets.values()
                )
                life_delta_totals[card_id] += life_delta
                if event.deck_position is not None:
                    draw_counts[card_id] += 1
                    stats["critical_cards_drawn_total"] += 1
                    player = player_by_id.get(event.player_id)
                    if event.player_id in winner_ids:
                        stats["critical_card_stats"][card_id]["win_count_after_draw"] += 1
                    if player is not None and not player.is_alive:
                        stats["critical_card_stats"][card_id][
                            "elimination_count_after_draw"
                        ] += 1
                if event.effect_triggered:
                    stats["critical_effects_triggered_total"] += 1
                    stats["critical_effects_by_card"][card_id] += 1

        trigger_key_by_card = {
            BENDAGGIO_EMERGENZA: "bendaggio_trigger_count",
            SANGUE_FREDDO: "sangue_freddo_trigger_count",
            MANO_LUCIDA: "mano_lucida_trigger_count",
            SCUDO_ISTINTIVO: "scudo_istintivo_trigger_count",
            MANO_TREMANTE: "mano_tremante_trigger_count",
            COLPO_DI_CODA: "colpo_di_coda_trigger_count",
            FERITA_ESPOSTA: "ferita_esposta_trigger_count",
            SONO_ANCORA_QUI: "sono_ancora_qui_trigger_count",
        }
        for card_id in ALL_CRITICAL_CARD_IDS:
            draw_count = draw_counts[card_id]
            activation_count = stats["critical_effects_by_card"][card_id]
            total_life_delta = life_delta_totals[card_id]
            average_life_delta = (
                total_life_delta / activation_count if activation_count else 0.0
            )
            stats["average_life_delta_by_card"][card_id] = average_life_delta
            if card_id in trigger_key_by_card:
                stats[trigger_key_by_card[card_id]] = activation_count
            stats["critical_card_stats"][card_id].update(
                {
                    "draw_count": draw_count,
                    "activation_count": activation_count,
                    "total_life_delta": total_life_delta,
                    "average_life_delta": average_life_delta,
                }
            )

        return stats
