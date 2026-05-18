"""Statistics aggregation for simulation results."""

from collections.abc import Sequence

from sotto_soglia.game import GameResult
from sotto_soglia.models import Color, EliminationReason


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
                wins_by_strategy[winner.strategy_name] += 1
                winner_lives.append(winner.lives)
                winner_critical_wounds.append(winner.critical_wounds)

        return {
            "games_count": games_count,
            "average_rounds": sum(rounds) / games_count,
            "min_rounds": min(rounds),
            "max_rounds": max(rounds),
            "draw_count": draw_count,
            "draw_rate": draw_count / games_count,
            "wins_by_player_id": wins_by_player_id,
            "wins_by_color": wins_by_color,
            "wins_by_strategy": wins_by_strategy,
            "win_rate_by_player_id": {
                player_id: wins / games_count
                for player_id, wins in wins_by_player_id.items()
            },
            "win_rate_by_color": {
                color: wins / games_count
                for color, wins in wins_by_color.items()
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

    def _empty_stats(self) -> dict:
        """Return a stable empty aggregate structure."""

        return {
            "games_count": 0,
            "average_rounds": 0.0,
            "min_rounds": 0,
            "max_rounds": 0,
            "draw_count": 0,
            "draw_rate": 0.0,
            "wins_by_player_id": {},
            "wins_by_color": {color.name: 0 for color in Color},
            "wins_by_strategy": {},
            "win_rate_by_player_id": {},
            "win_rate_by_color": {color.name: 0.0 for color in Color},
            "win_rate_by_strategy": {},
            "eliminations_by_lives": 0,
            "eliminations_by_critical_wounds": 0,
            "average_winner_lives": 0.0,
            "average_winner_critical_wounds": 0.0,
        }

    def _average(self, values: Sequence[int]) -> float:
        """Return the numeric average or zero for an empty sequence."""

        if not values:
            return 0.0
        return sum(values) / len(values)
