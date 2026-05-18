"""Critical wound card definitions and helpers."""

from dataclasses import dataclass, field
from random import Random


BENDAGGIO_EMERGENZA = "bendaggio_emergenza"
SANGUE_FREDDO = "sangue_freddo"
MANO_LUCIDA = "mano_lucida"
SCUDO_ISTINTIVO = "scudo_istintivo"
MANO_TREMANTE = "mano_tremante"
COLPO_DI_CODA = "colpo_di_coda"
FERITA_ESPOSTA = "ferita_esposta"
SONO_ANCORA_QUI = "sono_ancora_qui"

SONO_ANCORA_QUI_SINGLE_1 = "single_1"
SONO_ANCORA_QUI_SINGLE_2 = "single_2"
SONO_ANCORA_QUI_UP_TO_2_TARGETS = "up_to_2_targets"
SONO_ANCORA_QUI_VARIANTS = (
    SONO_ANCORA_QUI_SINGLE_1,
    SONO_ANCORA_QUI_SINGLE_2,
    SONO_ANCORA_QUI_UP_TO_2_TARGETS,
)

IMMEDIATE_EFFECTS = {BENDAGGIO_EMERGENZA, SONO_ANCORA_QUI}
NEXT_ROUND_EFFECTS = {
    SANGUE_FREDDO,
    MANO_LUCIDA,
    SCUDO_ISTINTIVO,
    MANO_TREMANTE,
    COLPO_DI_CODA,
    FERITA_ESPOSTA,
}

CRITICAL_CARD_NAMES = {
    BENDAGGIO_EMERGENZA: "Bendaggio d'Emergenza",
    SANGUE_FREDDO: "Sangue Freddo",
    MANO_LUCIDA: "Mano Lucida",
    SCUDO_ISTINTIVO: "Scudo Istintivo",
    MANO_TREMANTE: "Mano Tremante",
    COLPO_DI_CODA: "Colpo di Coda",
    FERITA_ESPOSTA: "Ferita Esposta",
    SONO_ANCORA_QUI: "Sono ancora qui",
}

CRITICAL_CARD_IDS = tuple(CRITICAL_CARD_NAMES)


@dataclass
class CriticalCardEvent:
    """One event caused by a critical wound card."""

    game_id: int
    round_number: int
    draw_order: int | None
    player_id: int
    critical_card_id: str
    critical_card_name: str
    timing: str
    effect_triggered: bool
    target_player_id: int | str | None = None
    life_delta_player: int = 0
    life_delta_targets: dict[int, int] = field(default_factory=dict)
    prevented_damage: int = 0
    deck_position: int | None = None
    player_lives_after: int = 0
    player_critical_wounds_after: int = 0


def build_critical_deck() -> list[str]:
    """Return the unshuffled 16-card critical wound deck."""

    return [
        card_id
        for card_id in CRITICAL_CARD_IDS
        for _ in range(2)
    ]


def shuffle_critical_deck(seed: int | None = None) -> list[str]:
    """Return a shuffled critical wound deck reproducible by seed."""

    deck = build_critical_deck()
    Random(seed).shuffle(deck)
    return deck


def validate_critical_deck_order(order: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Validate a fixed deck order and return normalized card ids."""

    if isinstance(order, str):
        card_ids = tuple(card_id.strip() for card_id in order.split(",") if card_id.strip())
    else:
        card_ids = tuple(order)

    if len(card_ids) != 16:
        raise ValueError("--critical-deck-order must contain exactly 16 card ids")

    unknown_ids = sorted({card_id for card_id in card_ids if card_id not in CRITICAL_CARD_IDS})
    if unknown_ids:
        raise ValueError(
            "--critical-deck-order contains unknown card ids: "
            + ", ".join(unknown_ids)
        )

    invalid_counts = {
        card_id: card_ids.count(card_id)
        for card_id in CRITICAL_CARD_IDS
        if card_ids.count(card_id) != 2
    }
    if invalid_counts:
        details = ", ".join(
            f"{card_id}={count}"
            for card_id, count in sorted(invalid_counts.items())
        )
        raise ValueError(
            "--critical-deck-order must contain exactly 2 copies of each effect "
            f"({details})"
        )

    return card_ids


def critical_card_name(card_id: str) -> str:
    """Return the printable name for a critical wound card id."""

    return CRITICAL_CARD_NAMES[card_id]


def critical_card_timing(card_id: str) -> str:
    """Return the timing label for a critical wound card id."""

    return "immediate" if card_id in IMMEDIATE_EFFECTS else "next_round"
