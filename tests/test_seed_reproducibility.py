from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.game import play_game


def _game_signature(result):
    round_signature = []
    for round_result in result.round_history:
        selected_cards = tuple(
            sorted(
                (
                    player_id,
                    card.color.value,
                    card.value,
                )
                for player_id, card in round_result.selected_cards.items()
            )
        )
        round_signature.append(
            (
                selected_cards,
                tuple(round_result.critical_wound_players),
                tuple(sorted(round_result.total_damage_by_player.items())),
                tuple(round_result.eliminated_players),
            )
        )

    return (
        tuple(result.winner_ids),
        result.is_draw,
        result.rounds_count,
        tuple(round_signature),
    )


def test_same_seed_produces_same_essential_game_result():
    first = play_game(game_id=1, players_count=4, seed=42)
    second = play_game(game_id=1, players_count=4, seed=42)

    assert _game_signature(first) == _game_signature(second)


def test_different_seeds_are_accepted_without_errors():
    first = play_game(game_id=1, players_count=4, seed=1)
    second = play_game(game_id=2, players_count=4, seed=2)

    assert first.winner_ids
    assert second.winner_ids
