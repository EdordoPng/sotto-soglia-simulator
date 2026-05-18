"""Command-line interface for the Sotto Soglia simulator."""

import argparse

from sotto_soglia.game import play_game


def main() -> None:
    """Parse CLI arguments and run simple game executions."""

    parser = argparse.ArgumentParser(description="Sotto Soglia simulation runner.")
    parser.add_argument("--players", type=int, default=4, help="Number of players.")
    parser.add_argument("--games", type=int, default=1, help="Number of games to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")

    args = parser.parse_args()

    if args.games < 1:
        raise ValueError("--games must be at least 1")

    results = []
    for game_index in range(args.games):
        game_seed = None if args.seed is None else args.seed + game_index
        result = play_game(
            game_id=game_index + 1,
            players_count=args.players,
            seed=game_seed,
        )
        results.append(result)

        outcome = "draw" if result.is_draw else f"winner(s): {result.winner_ids}"
        print(
            f"Game {result.game_id}: rounds={result.rounds_count}, "
            f"{outcome}, seed={result.seed}"
        )

    print(f"Games executed: {len(results)}")
    print("Statistical runner and exports are not implemented yet.")
