import csv
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from sotto_soglia.critical import (
    CRITICAL_CARD_IDS,
    LEGACY_CRITICAL_DECK_PROFILE_ID,
    V05_HUNGER_CARD_IDS,
    V05_HUNGER_DECK_PROFILE_ID,
)
from sotto_soglia.config import GameConfig
from sotto_soglia.exporters import CSV_DELIMITER, export_simulation_result
from sotto_soglia.animal_effects import (
    AnimalEffectEvent,
    CONIGLIO_GRANDE_BALZO,
    CONIGLIO_PASSO_LEGGERO,
    CONIGLIO_SCATTO_IMPROVVISO,
    PANDA_GRANDE_LETARGO,
    PANDA_RESPIRO_LENTO,
    PANDA_RIPOSO_FORZATO,
    SCIMMIA_BANANA_RUBATA,
    SCIMMIA_BUCCIA_DI_BANANA,
    SCIMMIA_FINTA_INNOCENTE,
    SCOIATTOLO_DISPENSA_ORDINATA,
    SCOIATTOLO_GHIANDA_NASCOSTA,
    SCOIATTOLO_PICCOLA_RISERVA,
)
from sotto_soglia.game import GameResult
from sotto_soglia.models import Color, PlayerState
from sotto_soglia.round import RoundResult
from sotto_soglia.simulation import SimulationResult, SimulationRunner
from sotto_soglia.strategies import create_strategy


def _small_simulation():
    return SimulationRunner().run(players_count=4, games_count=5, seed=42)


ANIMAL_EFFECT_EVENT_FIELDS = [
    "game_index",
    "round_number",
    "player_id",
    "animal",
    "card_color",
    "card_display_color",
    "card_value",
    "effect_id",
    "effect_name",
    "timing",
    "status",
    "target_player_id",
    "value_before",
    "value_after",
    "amount",
    "actual_amount",
    "reason",
]

STRATEGY_DECISION_EVENT_FIELDS = [
    "game_index",
    "round_number",
    "player_id",
    "technical_color",
    "animal",
    "display_color",
    "strategy_name",
    "lives",
    "critical_wounds",
    "critical_wounds_limit",
    "alive_players_count",
    "candidate_card_color",
    "candidate_card_display_color",
    "candidate_card_animal",
    "candidate_card_value",
    "effective_comparison",
    "effective_consumption",
    "score",
    "chosen",
    "choice_rank",
    "reason_flags",
]


def test_export_creates_expected_files(tmp_path):
    simulation = _small_simulation()

    exported_files = export_simulation_result(simulation, tmp_path)

    assert exported_files["simulation_config"].exists()
    assert exported_files["aggregate_stats"].exists()
    assert exported_files["games_summary"].exists()
    assert exported_files["rounds_summary"].exists()
    assert exported_files["animal_effect_events"].exists()
    assert exported_files["strategy_decision_events"].exists()


def test_aggregate_stats_json_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["aggregate_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["games_count"] == 5
    assert "average_rounds" in data
    assert "wins_by_color" in data
    assert "win_rate_by_color" in data
    assert "wins_by_animal" in data
    assert "win_rate_by_animal" in data
    assert "wins_by_display_color" in data
    assert "win_rate_by_display_color" in data


def test_simulation_config_json_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["simulation_config"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["players_count"] == 4
    assert data["games_count"] == 5
    assert data["base_seed"] == 42
    assert data["initial_lives"] == 24
    assert data["critical_wounds_limit"] == 4
    assert data["cards_per_player"] == 3
    assert data["color_effects_enabled"] is False
    assert data["critical_card_effects_enabled"] is True
    assert data["animal_card_effects_enabled"] is True
    assert data["critical_deck_profile_id"] == V05_HUNGER_DECK_PROFILE_ID
    assert data["sono_ancora_qui_variant"] == "single_2"
    assert "generated_files" in data
    assert data["generated_files"]["games_summary"] == "games_summary.csv"
    assert data["generated_files"]["animal_effect_events"] == (
        "animal_effect_events.csv"
    )
    assert data["generated_files"]["strategy_decision_events"] == (
        "strategy_decision_events.csv"
    )
    assert data["generated_files"]["critical_events"] == "critical_events.csv"
    assert data["generated_files"]["critical_deck_orders"] == "critical_deck_orders.csv"
    assert data["generated_files"]["critical_card_stats"] == "critical_card_stats.csv"


def test_simulation_config_json_exports_animal_card_effects_enabled_true(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        config=GameConfig(
            initial_lives=24,
            critical_wounds_limit=4,
            color_effects_enabled=False,
            critical_card_effects_enabled=True,
            animal_card_effects_enabled=True,
            critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
        ),
    )
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["simulation_config"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["animal_card_effects_enabled"] is True


def test_simulation_config_json_exports_animal_card_effects_enabled_false(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        config=GameConfig(
            initial_lives=24,
            critical_wounds_limit=4,
            color_effects_enabled=False,
            critical_card_effects_enabled=True,
            animal_card_effects_enabled=False,
            critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
        ),
    )
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["simulation_config"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["animal_card_effects_enabled"] is False


def test_simulation_config_json_exports_animal_lineup(tmp_path):
    simulation = SimulationRunner().run(
        players_count=2,
        games_count=1,
        seed=42,
        config=GameConfig(
            animal_lineup=(Color.RED, Color.YELLOW),
        ),
    )
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["simulation_config"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["animal_lineup"] == ["Coniglio", "Scoiattolo"]


def test_simulation_config_json_exports_custom_cards_per_player(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        config=GameConfig(
            initial_lives=24,
            critical_wounds_limit=4,
            cards_per_player=4,
            color_effects_enabled=False,
            critical_card_effects_enabled=True,
            animal_card_effects_enabled=True,
            critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
        ),
    )
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["simulation_config"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["cards_per_player"] == 4
    assert data["animal_card_effects_enabled"] is True
    assert data["critical_card_effects_enabled"] is True
    assert data["critical_deck_profile_id"] == V05_HUNGER_DECK_PROFILE_ID
    assert data["color_effects_enabled"] is False


def test_critical_deck_orders_csv_uses_v05_hunger_deck(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["critical_deck_orders"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == simulation.games_count
    for row in rows:
        deck_order = row["critical_deck_order"].split(",")
        assert len(deck_order) == 18
        assert set(deck_order) == set(V05_HUNGER_CARD_IDS)
        assert all(deck_order.count(card_id) == 3 for card_id in V05_HUNGER_CARD_IDS)


def test_critical_card_stats_csv_includes_v05_hunger_cards_only_for_v05_deck(
    tmp_path,
):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["critical_card_stats"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    rows_by_card = {row["card_id"]: row for row in rows}
    assert set(rows_by_card) == set(V05_HUNGER_CARD_IDS)
    assert any(
        int(rows_by_card[card_id]["draw_count"]) > 0
        for card_id in V05_HUNGER_CARD_IDS
    )


def test_critical_card_stats_csv_includes_legacy_cards_only_for_legacy_deck(
    tmp_path,
):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        config=GameConfig(critical_card_effects_enabled=True),
    )
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["critical_card_stats"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    rows_by_card = {row["card_id"]: row for row in rows}
    assert simulation.critical_deck_profile_id == LEGACY_CRITICAL_DECK_PROFILE_ID
    assert set(rows_by_card) == set(CRITICAL_CARD_IDS)
    assert set(V05_HUNGER_CARD_IDS).isdisjoint(rows_by_card)


def test_critical_card_stats_csv_keeps_active_profile_cards_with_zero_draws(
    tmp_path,
):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        config=GameConfig(
            critical_card_effects_enabled=True,
            critical_deck_order=tuple(
                card_id
                for card_id in CRITICAL_CARD_IDS
                for _ in range(2)
            ),
        ),
    )
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["critical_card_stats"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    rows_by_card = {row["card_id"]: row for row in rows}
    assert set(rows_by_card) == set(CRITICAL_CARD_IDS)
    assert any(int(row["draw_count"]) == 0 for row in rows)


def test_critical_events_csv_contains_only_known_v05_hunger_cards_when_drawn(
    tmp_path,
):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["critical_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    drawn_rows = [row for row in rows if row["deck_position"]]
    assert drawn_rows
    assert {row["critical_card_id"] for row in drawn_rows}.issubset(
        set(V05_HUNGER_CARD_IDS)
    )
    assert {row["timing"] for row in drawn_rows}.issubset(
        {"immediate", "recovery", "next_round"}
    )


def test_games_summary_csv_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["games_summary"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 5
    for column in [
        "game_id",
        "seed",
        "rounds_count",
        "winner_ids",
        "is_draw",
        "strategy_names",
        "winner_colors",
        "winner_animals",
        "winner_display_colors",
        "winner_strategies",
    ]:
        assert column in rows[0]


def test_games_summary_csv_exports_winner_animals_and_display_colors(tmp_path):
    simulation = SimulationResult(
        players_count=4,
        games_count=4,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                winner_ids=[1],
                final_players=[PlayerState(player_id=1, color=Color.BLUE, lives=5)],
            ),
            GameResult(
                game_id=2,
                winner_ids=[1],
                final_players=[PlayerState(player_id=1, color=Color.RED, lives=5)],
            ),
            GameResult(
                game_id=3,
                winner_ids=[1],
                final_players=[PlayerState(player_id=1, color=Color.GREEN, lives=5)],
            ),
            GameResult(
                game_id=4,
                winner_ids=[1],
                final_players=[PlayerState(player_id=1, color=Color.YELLOW, lives=5)],
            ),
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["games_summary"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    rows_by_color = {row["winner_colors"]: row for row in rows}
    assert rows_by_color["BLUE"]["winner_animals"] == "Panda"
    assert rows_by_color["BLUE"]["winner_display_colors"] == "green"
    assert rows_by_color["RED"]["winner_animals"] == "Coniglio"
    assert rows_by_color["RED"]["winner_display_colors"] == "orange"
    assert rows_by_color["GREEN"]["winner_animals"] == "Scimmia"
    assert rows_by_color["GREEN"]["winner_display_colors"] == "yellow"
    assert rows_by_color["YELLOW"]["winner_animals"] == "Scoiattolo"
    assert rows_by_color["YELLOW"]["winner_display_colors"] == "brown"


def test_standard_export_respects_explicit_two_player_animal_lineup(tmp_path):
    simulation = SimulationRunner().run(
        players_count=2,
        games_count=5,
        seed=42,
        config=GameConfig(
            animal_lineup=(Color.RED, Color.YELLOW),
        ),
        strategies=create_strategy("v05_animal_aware"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["games_summary"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    winner_animals = {
        animal
        for row in rows
        for animal in row["winner_animals"].split("|")
        if animal
    }
    assert winner_animals <= {"Coniglio", "Scoiattolo"}
    assert "Panda" not in winner_animals

    with exported_files["aggregate_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["wins_by_animal"]["Panda"] == 0
    assert data["wins_by_animal"]["Scimmia"] == 0

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        animal_rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert {row["animal"] for row in animal_rows} <= {"Coniglio", "Scoiattolo"}
    assert {row["card_color"] for row in animal_rows} <= {"RED", "YELLOW"}
    assert {row["card_display_color"] for row in animal_rows} <= {"orange", "brown"}


def test_strategy_decision_events_csv_respects_explicit_lineup(tmp_path):
    simulation = SimulationRunner().run(
        players_count=2,
        games_count=1,
        seed=42,
        config=GameConfig(
            initial_lives=12,
            critical_wounds_limit=5,
            color_effects_enabled=False,
            critical_card_effects_enabled=True,
            animal_card_effects_enabled=True,
            critical_deck_profile_id=V05_HUNGER_DECK_PROFILE_ID,
            animal_lineup=(Color.RED, Color.YELLOW),
        ),
        strategies=create_strategy("v05_animal_aware"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["strategy_decision_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert rows
    assert {row["technical_color"] for row in rows} <= {"RED", "YELLOW"}
    assert {row["animal"] for row in rows} <= {"Coniglio", "Scoiattolo"}
    assert {row["display_color"] for row in rows} <= {"orange", "brown"}


def test_rounds_summary_csv_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["rounds_summary"].open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert rows
    for column in [
        "game_id",
        "round_number",
        "lowest_value",
        "critical_wound_players",
        "eliminated_players",
    ]:
        assert column in rows[0]


def test_animal_effect_events_csv_is_created_with_header_when_empty(tmp_path):
    simulation = SimulationResult(
        players_count=2,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[RoundResult(round_number=1)],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        rows = list(reader)

    assert reader.fieldnames == ANIMAL_EFFECT_EVENT_FIELDS
    assert rows == []


def test_strategy_decision_events_csv_is_created_with_header_when_empty(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        strategies=create_strategy("random"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["strategy_decision_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        rows = list(reader)

    assert reader.fieldnames == STRATEGY_DECISION_EVENT_FIELDS
    assert rows == []


def test_strategy_decision_events_csv_exports_v05_balanced_candidate_rows(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        strategies=create_strategy("v05_balanced"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["strategy_decision_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        rows = list(reader)

    assert reader.fieldnames == STRATEGY_DECISION_EVENT_FIELDS
    assert rows

    first_row = rows[0]
    for field in STRATEGY_DECISION_EVENT_FIELDS:
        assert field in first_row
    assert first_row["game_index"]
    assert first_row["round_number"]
    assert first_row["player_id"]
    assert first_row["strategy_name"] == "v05_balanced"
    assert first_row["technical_color"] in {"BLUE", "RED", "GREEN", "YELLOW"}
    assert first_row["animal"] in {"Panda", "Coniglio", "Scimmia", "Scoiattolo"}
    assert first_row["display_color"] in {"green", "orange", "yellow", "brown"}
    assert first_row["candidate_card_color"] in {"BLUE", "RED", "GREEN", "YELLOW"}
    assert first_row["candidate_card_display_color"] in {
        "green",
        "orange",
        "yellow",
        "brown",
    }
    assert first_row["candidate_card_animal"] in {
        "Panda",
        "Coniglio",
        "Scimmia",
        "Scoiattolo",
    }
    assert first_row["candidate_card_value"]
    assert first_row["effective_comparison"]
    assert first_row["effective_consumption"]
    assert first_row["score"]
    assert first_row["chosen"] in {"True", "False"}
    assert first_row["choice_rank"]


def test_strategy_decision_events_csv_has_valid_chosen_and_rank_groups(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        strategies=create_strategy("v05_balanced"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["strategy_decision_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    rows_by_decision = {}
    for row in rows:
        key = (row["game_index"], row["round_number"], row["player_id"])
        rows_by_decision.setdefault(key, []).append(row)

    assert rows_by_decision
    saw_pipe_separated_reason_flags = False
    for decision_rows in rows_by_decision.values():
        chosen_rows = [
            row
            for row in decision_rows
            if row["chosen"] == "True"
        ]
        assert len(chosen_rows) == 1
        assert chosen_rows[0]["choice_rank"] == "1"
        assert sorted(int(row["choice_rank"]) for row in decision_rows) == list(
            range(1, len(decision_rows) + 1)
        )
        saw_pipe_separated_reason_flags = saw_pipe_separated_reason_flags or any(
            "|" in row["reason_flags"]
            for row in decision_rows
        )

    assert saw_pipe_separated_reason_flags


def test_strategy_decision_events_csv_exports_v05_animal_aware_candidate_rows(tmp_path):
    simulation = SimulationRunner().run(
        players_count=4,
        games_count=1,
        seed=42,
        strategies=create_strategy("v05_animal_aware"),
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["strategy_decision_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter=CSV_DELIMITER)
        rows = list(reader)

    assert reader.fieldnames == STRATEGY_DECISION_EVENT_FIELDS
    assert rows
    assert {row["strategy_name"] for row in rows} == {"v05_animal_aware"}

    rows_by_decision = {}
    for row in rows:
        key = (row["game_index"], row["round_number"], row["player_id"])
        rows_by_decision.setdefault(key, []).append(row)

    assert rows_by_decision
    for decision_rows in rows_by_decision.values():
        chosen_rows = [
            row
            for row in decision_rows
            if row["chosen"] == "True"
        ]
        assert len(chosen_rows) == 1
        assert chosen_rows[0]["choice_rank"] == "1"
        assert sorted(int(row["choice_rank"]) for row in decision_rows) == list(
            range(1, len(decision_rows) + 1)
        )


def test_animal_effect_events_csv_exports_scatto_improvviso(tmp_path):
    simulation = SimulationResult(
        players_count=2,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[
                    RoundResult(
                        round_number=1,
                        animal_events=[
                            AnimalEffectEvent(
                                player_id=2,
                                animal="Coniglio",
                                card_color="RED",
                                card_value=1,
                                effect_id=CONIGLIO_SCATTO_IMPROVVISO,
                                effect_name="Scatto Improvviso",
                                timing="comparison",
                                status="applied",
                                value_before=1,
                                value_after=2,
                            )
                        ],
                    )
                ],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 1
    row = rows[0]
    assert row["game_index"] == "1"
    assert row["round_number"] == "1"
    assert row["effect_id"] == CONIGLIO_SCATTO_IMPROVVISO
    assert row["effect_name"] == "Scatto Improvviso"
    assert row["player_id"] == "2"
    assert row["card_color"] == "RED"
    assert row["card_display_color"] == "orange"
    assert row["card_value"] == "1"
    assert row["timing"] == "comparison"
    assert row["status"] == "applied"
    assert row["value_before"] == "1"
    assert row["value_after"] == "2"


def test_animal_effect_events_csv_exports_multiple_events_and_games(tmp_path):
    simulation = SimulationResult(
        players_count=2,
        games_count=2,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[
                    RoundResult(
                        round_number=1,
                        animal_events=[
                            AnimalEffectEvent(
                                player_id=1,
                                animal="Panda",
                                card_color="BLUE",
                                card_value=1,
                                effect_id=PANDA_RIPOSO_FORZATO,
                                effect_name="Riposo Forzato",
                                timing="recovery_schedule",
                                status="scheduled",
                                amount=1,
                            ),
                            AnimalEffectEvent(
                                player_id=2,
                                animal="Coniglio",
                                card_color="RED",
                                card_value=1,
                                effect_id=CONIGLIO_SCATTO_IMPROVVISO,
                                effect_name="Scatto Improvviso",
                                timing="comparison",
                                status="applied",
                                value_before=1,
                                value_after=2,
                            ),
                        ],
                    )
                ],
            ),
            GameResult(
                game_id=2,
                round_history=[
                    RoundResult(
                        round_number=2,
                        animal_events=[
                            AnimalEffectEvent(
                                player_id=1,
                                animal="Panda",
                                card_color="BLUE",
                                card_value=1,
                                effect_id=PANDA_RIPOSO_FORZATO,
                                effect_name="Riposo Forzato",
                                timing="recovery_schedule",
                                status="scheduled",
                                amount=1,
                            )
                        ],
                    )
                ],
            ),
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 3
    assert [row["game_index"] for row in rows] == ["1", "1", "2"]
    assert [row["round_number"] for row in rows] == ["1", "1", "2"]
    assert [row["card_display_color"] for row in rows] == ["green", "orange", "green"]
    riposo_rows = [
        row
        for row in rows
        if row["effect_id"] == PANDA_RIPOSO_FORZATO
    ]
    assert len(riposo_rows) == 2
    assert all(row["timing"] == "recovery_schedule" for row in riposo_rows)
    assert all(row["status"] == "scheduled" for row in riposo_rows)
    assert all(row["amount"] == "1" for row in riposo_rows)


def test_animal_effect_events_csv_exports_k2_and_k6_effects(tmp_path):
    events = [
        AnimalEffectEvent(
            player_id=1,
            animal="Panda",
            card_color="BLUE",
            card_value=1,
            effect_id=PANDA_RIPOSO_FORZATO,
            effect_name="Riposo Forzato",
            timing="recovery_schedule",
            status="scheduled",
            amount=1,
        ),
        AnimalEffectEvent(
            player_id=2,
            animal="Coniglio",
            card_color="RED",
            card_value=1,
            effect_id=CONIGLIO_SCATTO_IMPROVVISO,
            effect_name="Scatto Improvviso",
            timing="comparison",
            status="applied",
            value_before=1,
            value_after=2,
        ),
        AnimalEffectEvent(
            player_id=4,
            animal="Scoiattolo",
            card_color="YELLOW",
            card_value=1,
            effect_id=SCOIATTOLO_GHIANDA_NASCOSTA,
            effect_name="Ghianda Nascosta",
            timing="next_round_schedule",
            status="scheduled",
            amount=1,
        ),
        AnimalEffectEvent(
            player_id=4,
            animal="Scoiattolo",
            card_color="YELLOW",
            card_value=4,
            effect_id=SCOIATTOLO_DISPENSA_ORDINATA,
            effect_name="Dispensa Ordinata",
            timing="next_round_schedule",
            status="scheduled",
            amount=1,
        ),
        AnimalEffectEvent(
            player_id=2,
            animal="Coniglio",
            card_color="RED",
            card_value=2,
            effect_id=CONIGLIO_PASSO_LEGGERO,
            effect_name="Passo Leggero",
            timing="consumption",
            status="applied",
            value_before=2,
            value_after=3,
            reason="shared_printed_2",
        ),
        AnimalEffectEvent(
            player_id=2,
            animal="Coniglio",
            card_color="RED",
            card_value=4,
            effect_id=CONIGLIO_GRANDE_BALZO,
            effect_name="Grande Balzo",
            timing="comparison",
            status="applied",
            value_before=4,
            value_after=5,
        ),
        AnimalEffectEvent(
            player_id=1,
            animal="Panda",
            card_color="BLUE",
            card_value=3,
            effect_id=PANDA_RESPIRO_LENTO,
            effect_name="Respiro Lento",
            timing="consumption",
            status="applied",
            value_before=3,
            value_after=2,
            amount=1,
        ),
        AnimalEffectEvent(
            player_id=4,
            animal="Scoiattolo",
            card_color="YELLOW",
            card_value=3,
            effect_id=SCOIATTOLO_PICCOLA_RISERVA,
            effect_name="Piccola Riserva",
            timing="recovery_schedule",
            status="scheduled",
            amount=1,
        ),
    ]
    simulation = SimulationResult(
        players_count=4,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[
                    RoundResult(round_number=1, animal_events=events),
                ],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == len(events)
    assert {row["effect_id"] for row in rows} == {
        CONIGLIO_GRANDE_BALZO,
        CONIGLIO_PASSO_LEGGERO,
        CONIGLIO_SCATTO_IMPROVVISO,
        PANDA_RESPIRO_LENTO,
        PANDA_RIPOSO_FORZATO,
        SCOIATTOLO_DISPENSA_ORDINATA,
        SCOIATTOLO_GHIANDA_NASCOSTA,
        SCOIATTOLO_PICCOLA_RISERVA,
    }


def test_animal_effect_events_csv_exports_card_display_color_for_technical_colors(
    tmp_path,
):
    events = [
        AnimalEffectEvent(
            player_id=1,
            animal="Panda",
            card_color="BLUE",
            card_value=1,
            effect_id=PANDA_RIPOSO_FORZATO,
            effect_name="Riposo Forzato",
            timing="recovery_schedule",
            status="scheduled",
        ),
        AnimalEffectEvent(
            player_id=2,
            animal="Coniglio",
            card_color="RED",
            card_value=1,
            effect_id=CONIGLIO_SCATTO_IMPROVVISO,
            effect_name="Scatto Improvviso",
            timing="comparison",
            status="applied",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=1,
            effect_id=SCIMMIA_FINTA_INNOCENTE,
            effect_name="Finta Innocente",
            timing="hunger_assignment",
            status="applied",
        ),
        AnimalEffectEvent(
            player_id=4,
            animal="Scoiattolo",
            card_color="YELLOW",
            card_value=1,
            effect_id=SCOIATTOLO_GHIANDA_NASCOSTA,
            effect_name="Ghianda Nascosta",
            timing="next_round_schedule",
            status="scheduled",
        ),
    ]
    simulation = SimulationResult(
        players_count=4,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[RoundResult(round_number=1, animal_events=events)],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    rows_by_color = {row["card_color"]: row for row in rows}
    assert rows_by_color["BLUE"]["card_display_color"] == "green"
    assert rows_by_color["RED"]["card_display_color"] == "orange"
    assert rows_by_color["GREEN"]["card_display_color"] == "yellow"
    assert rows_by_color["YELLOW"]["card_display_color"] == "brown"


def test_animal_effect_events_csv_exports_grande_letargo_events(tmp_path):
    events = [
        AnimalEffectEvent(
            player_id=1,
            animal="Panda",
            card_color="BLUE",
            card_value=5,
            effect_id=PANDA_GRANDE_LETARGO,
            effect_name="Grande Letargo",
            timing="next_round_schedule",
            status="scheduled",
        ),
        AnimalEffectEvent(
            player_id=1,
            animal="Panda",
            card_color="RED",
            card_value=4,
            effect_id=PANDA_GRANDE_LETARGO,
            effect_name="Grande Letargo",
            timing="comparison",
            status="applied",
            value_before=4,
            value_after=3,
        ),
        AnimalEffectEvent(
            player_id=1,
            animal="Panda",
            card_color="RED",
            card_value=4,
            effect_id=PANDA_GRANDE_LETARGO,
            effect_name="Grande Letargo",
            timing="next_round_consume",
            status="consumed",
        ),
    ]
    simulation = SimulationResult(
        players_count=2,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[RoundResult(round_number=2, animal_events=events)],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 3
    rows_by_timing = {row["timing"]: row for row in rows}
    assert rows_by_timing["next_round_schedule"]["status"] == "scheduled"
    assert rows_by_timing["comparison"]["status"] == "applied"
    assert rows_by_timing["comparison"]["value_before"] == "4"
    assert rows_by_timing["comparison"]["value_after"] == "3"
    assert rows_by_timing["next_round_consume"]["status"] == "consumed"
    assert {row["effect_id"] for row in rows} == {PANDA_GRANDE_LETARGO}


def test_animal_effect_events_csv_exports_finta_innocente_events(tmp_path):
    events = [
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=1,
            effect_id=SCIMMIA_FINTA_INNOCENTE,
            effect_name="Finta Innocente",
            timing="hunger_assignment",
            status="applied",
            reason="other_printed_one",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=1,
            effect_id=SCIMMIA_FINTA_INNOCENTE,
            effect_name="Finta Innocente",
            timing="hunger_assignment",
            status="not_activated",
            reason="no_other_printed_one",
        ),
    ]
    simulation = SimulationResult(
        players_count=3,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[RoundResult(round_number=1, animal_events=events)],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 2
    rows_by_status = {row["status"]: row for row in rows}
    assert rows_by_status["applied"]["effect_id"] == SCIMMIA_FINTA_INNOCENTE
    assert rows_by_status["applied"]["timing"] == "hunger_assignment"
    assert rows_by_status["applied"]["reason"] == "other_printed_one"
    assert rows_by_status["not_activated"]["effect_id"] == SCIMMIA_FINTA_INNOCENTE
    assert rows_by_status["not_activated"]["timing"] == "hunger_assignment"
    assert rows_by_status["not_activated"]["reason"] == "no_other_printed_one"


def test_animal_effect_events_csv_exports_buccia_di_banana_events(tmp_path):
    events = [
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=2,
            effect_id=SCIMMIA_BUCCIA_DI_BANANA,
            effect_name="Buccia di Banana",
            timing="comparison",
            status="applied",
            target_player_id=1,
            value_before=4,
            value_after=3,
            amount=1,
            actual_amount=1,
            reason="target_selected",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=2,
            effect_id=SCIMMIA_BUCCIA_DI_BANANA,
            effect_name="Buccia di Banana",
            timing="comparison",
            status="blocked",
            target_player_id=1,
            value_before=4,
            value_after=4,
            amount=1,
            actual_amount=0,
            reason="blocked_by_respiro_calmo",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=2,
            effect_id=SCIMMIA_BUCCIA_DI_BANANA,
            effect_name="Buccia di Banana",
            timing="comparison",
            status="not_activated",
            reason="no_valid_target",
        ),
    ]
    simulation = SimulationResult(
        players_count=3,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[RoundResult(round_number=1, animal_events=events)],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 3
    rows_by_status = {row["status"]: row for row in rows}
    assert rows_by_status["applied"]["effect_id"] == SCIMMIA_BUCCIA_DI_BANANA
    assert rows_by_status["applied"]["reason"] == "target_selected"
    assert rows_by_status["applied"]["target_player_id"] == "1"
    assert rows_by_status["applied"]["value_before"] == "4"
    assert rows_by_status["applied"]["value_after"] == "3"
    assert rows_by_status["blocked"]["effect_id"] == SCIMMIA_BUCCIA_DI_BANANA
    assert rows_by_status["blocked"]["reason"] == "blocked_by_respiro_calmo"
    assert rows_by_status["blocked"]["actual_amount"] == "0"
    assert rows_by_status["not_activated"]["effect_id"] == SCIMMIA_BUCCIA_DI_BANANA
    assert rows_by_status["not_activated"]["reason"] == "no_valid_target"


def test_animal_effect_events_csv_exports_banana_rubata_events(tmp_path):
    events = [
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=5,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="extra_schedule",
            status="scheduled",
            target_player_id=1,
            amount=1,
            reason="target_selected",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=5,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="extra_apply",
            status="applied",
            target_player_id=1,
            amount=1,
            actual_amount=1,
            reason="extra_consumed",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=5,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="recovery_schedule",
            status="scheduled",
            target_player_id=1,
            amount=1,
            reason="extra_consumed",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=5,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="extra_apply",
            status="not_applied",
            target_player_id=1,
            amount=1,
            actual_amount=0,
            reason="actual_consumed_zero",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=5,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="extra_schedule",
            status="not_activated",
            reason="received_affamato",
        ),
        AnimalEffectEvent(
            player_id=3,
            animal="Scimmia",
            card_color="GREEN",
            card_value=5,
            effect_id=SCIMMIA_BANANA_RUBATA,
            effect_name="Banana Rubata",
            timing="extra_schedule",
            status="not_activated",
            reason="no_valid_target",
        ),
    ]
    simulation = SimulationResult(
        players_count=3,
        games_count=1,
        base_seed=42,
        game_results=[
            GameResult(
                game_id=1,
                round_history=[RoundResult(round_number=1, animal_events=events)],
            )
        ],
    )

    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["animal_effect_events"].open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    assert len(rows) == 6
    rows_by_key = {
        (row["timing"], row["status"], row["reason"]): row
        for row in rows
    }
    schedule = rows_by_key[("extra_schedule", "scheduled", "target_selected")]
    assert schedule["effect_id"] == SCIMMIA_BANANA_RUBATA
    assert schedule["target_player_id"] == "1"
    assert schedule["amount"] == "1"
    applied = rows_by_key[("extra_apply", "applied", "extra_consumed")]
    assert applied["actual_amount"] == "1"
    recovery = rows_by_key[("recovery_schedule", "scheduled", "extra_consumed")]
    assert recovery["target_player_id"] == "1"
    assert recovery["amount"] == "1"
    not_applied = rows_by_key[
        ("extra_apply", "not_applied", "actual_consumed_zero")
    ]
    assert not_applied["actual_amount"] == "0"
    assert rows_by_key[
        ("extra_schedule", "not_activated", "received_affamato")
    ]["effect_id"] == SCIMMIA_BANANA_RUBATA
    assert rows_by_key[
        ("extra_schedule", "not_activated", "no_valid_target")
    ]["effect_id"] == SCIMMIA_BANANA_RUBATA
