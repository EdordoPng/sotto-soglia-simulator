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
    SCIMMIA_FINTA_INNOCENTE,
    SCOIATTOLO_DISPENSA_ORDINATA,
    SCOIATTOLO_GHIANDA_NASCOSTA,
    SCOIATTOLO_PICCOLA_RISERVA,
)
from sotto_soglia.game import GameResult
from sotto_soglia.round import RoundResult
from sotto_soglia.simulation import SimulationResult, SimulationRunner


def _small_simulation():
    return SimulationRunner().run(players_count=4, games_count=5, seed=42)


ANIMAL_EFFECT_EVENT_FIELDS = [
    "game_index",
    "round_number",
    "player_id",
    "animal",
    "card_color",
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


def test_export_creates_expected_files(tmp_path):
    simulation = _small_simulation()

    exported_files = export_simulation_result(simulation, tmp_path)

    assert exported_files["simulation_config"].exists()
    assert exported_files["aggregate_stats"].exists()
    assert exported_files["games_summary"].exists()
    assert exported_files["rounds_summary"].exists()
    assert exported_files["animal_effect_events"].exists()


def test_aggregate_stats_json_is_valid(tmp_path):
    simulation = _small_simulation()
    exported_files = export_simulation_result(simulation, tmp_path)

    with exported_files["aggregate_stats"].open(encoding="utf-8") as file:
        data = json.load(file)

    assert data["games_count"] == 5
    assert "average_rounds" in data
    assert "win_rate_by_color" in data


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
        "winner_strategies",
    ]:
        assert column in rows[0]


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
            value_after=1,
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
