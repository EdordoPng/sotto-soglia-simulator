"""Command-line interface for the Sotto Soglia simulator."""

import argparse


def main() -> None:
    """Parse CLI arguments and show the current scaffold status."""

    parser = argparse.ArgumentParser(description="Sotto Soglia simulation runner.")
    parser.add_argument("--players", type=int, default=4, help="Number of players.")
    parser.add_argument("--games", type=int, default=1, help="Number of games to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility.")

    args = parser.parse_args()

    print(f"Players: {args.players}")
    print(f"Games: {args.games}")
    print(f"Seed: {args.seed}")
    print("Simulation engine not implemented yet. Project scaffold is ready.")
