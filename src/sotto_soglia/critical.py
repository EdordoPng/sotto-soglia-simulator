"""Critical wound card definitions and helpers."""

from dataclasses import dataclass, field
from collections.abc import Mapping
from random import Random
from typing import TYPE_CHECKING

from sotto_soglia.models import PlayerState

if TYPE_CHECKING:
    from sotto_soglia.config import GameConfig


LEGACY_CRITICAL_DECK_PROFILE_ID = "legacy"
V05_HUNGER_DECK_PROFILE_ID = "v05_hunger"

BENDAGGIO_EMERGENZA = "bendaggio_emergenza"
SANGUE_FREDDO = "sangue_freddo"
MANO_LUCIDA = "mano_lucida"
SCUDO_ISTINTIVO = "scudo_istintivo"
MANO_TREMANTE = "mano_tremante"
COLPO_DI_CODA = "colpo_di_coda"
FERITA_ESPOSTA = "ferita_esposta"
SONO_ANCORA_QUI = "sono_ancora_qui"

BRICIOLA_NASCOSTA = "briciola_nascosta"
RAZIONE_RISPARMIATA = "razione_risparmiata"
FIUTO_DA_DISPENSA = "fiuto_da_dispensa"
PANCIA_BRONTOLANTE = "pancia_brontolante"
MORSO_DELLA_FAME = "morso_della_fame"
RESPIRO_CALMO = "respiro_calmo"

V05_HUNGER_IMMEDIATE_EFFECTS = {BRICIOLA_NASCOSTA}
V05_HUNGER_NEXT_ROUND_EFFECTS = {RAZIONE_RISPARMIATA, FIUTO_DA_DISPENSA}
V05_HUNGER_UNIMPLEMENTED_EFFECTS = {
    PANCIA_BRONTOLANTE,
    MORSO_DELLA_FAME,
    RESPIRO_CALMO,
}

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

V05_HUNGER_CARD_NAMES = {
    BRICIOLA_NASCOSTA: "Briciola Nascosta",
    RAZIONE_RISPARMIATA: "Razione Risparmiata",
    FIUTO_DA_DISPENSA: "Fiuto da Dispensa",
    PANCIA_BRONTOLANTE: "Pancia Brontolante",
    MORSO_DELLA_FAME: "Morso della Fame",
    RESPIRO_CALMO: "Respiro Calmo",
}

V05_HUNGER_CARD_IDS = tuple(V05_HUNGER_CARD_NAMES)


@dataclass(frozen=True)
class CriticalDeckProfile:
    """Composition profile for a critical/hunger deck."""

    profile_id: str
    deck_name: str
    card_names: Mapping[str, str]
    copies_per_effect: int

    @property
    def card_ids(self) -> tuple[str, ...]:
        """Return card ids in profile order."""

        return tuple(self.card_names)

    @property
    def cards_count(self) -> int:
        """Return total card count for this profile."""

        return len(self.card_ids) * self.copies_per_effect


LEGACY_CRITICAL_DECK_PROFILE = CriticalDeckProfile(
    profile_id=LEGACY_CRITICAL_DECK_PROFILE_ID,
    deck_name="Mazzo Ferita Critica",
    card_names=CRITICAL_CARD_NAMES,
    copies_per_effect=2,
)

V05_HUNGER_DECK_PROFILE = CriticalDeckProfile(
    profile_id=V05_HUNGER_DECK_PROFILE_ID,
    deck_name="Mazzo Affamato",
    card_names=V05_HUNGER_CARD_NAMES,
    copies_per_effect=3,
)

CRITICAL_DECK_PROFILES = {
    LEGACY_CRITICAL_DECK_PROFILE.profile_id: LEGACY_CRITICAL_DECK_PROFILE,
    V05_HUNGER_DECK_PROFILE.profile_id: V05_HUNGER_DECK_PROFILE,
}


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


def get_critical_deck_profile(profile_id: str) -> CriticalDeckProfile:
    """Return a deck profile by id or raise a clear error."""

    try:
        return CRITICAL_DECK_PROFILES[profile_id]
    except KeyError as error:
        valid_ids = ", ".join(sorted(CRITICAL_DECK_PROFILES))
        raise ValueError(
            f"Unknown critical deck profile '{profile_id}'. "
            f"Available profiles: {valid_ids}"
        ) from error


def _resolve_critical_deck_profile(
    profile: CriticalDeckProfile | str,
) -> CriticalDeckProfile:
    """Normalize a profile object or id to a profile object."""

    if isinstance(profile, CriticalDeckProfile):
        return profile
    return get_critical_deck_profile(profile)


def build_critical_deck(
    profile: CriticalDeckProfile | str = LEGACY_CRITICAL_DECK_PROFILE,
) -> list[str]:
    """Return an unshuffled deck for the selected profile."""

    profile = _resolve_critical_deck_profile(profile)
    return [
        card_id
        for card_id in profile.card_ids
        for _ in range(profile.copies_per_effect)
    ]


def shuffle_critical_deck(
    seed: int | None = None,
    profile: CriticalDeckProfile | str = LEGACY_CRITICAL_DECK_PROFILE,
) -> list[str]:
    """Return a shuffled deck for the selected profile reproducible by seed."""

    deck = build_critical_deck(profile)
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

    if card_id in CRITICAL_CARD_NAMES:
        return CRITICAL_CARD_NAMES[card_id]
    return V05_HUNGER_CARD_NAMES[card_id]


def critical_card_timing(card_id: str) -> str:
    """Return the timing label for a critical wound card id."""

    if card_id in IMMEDIATE_EFFECTS or card_id in V05_HUNGER_IMMEDIATE_EFFECTS:
        return "immediate"
    return "next_round"


def resolve_v05_hunger_effect(
    card_id: str,
    player: PlayerState,
    config: "GameConfig",
) -> int:
    """Apply one implemented v0.5 hunger effect and return the player's life delta.

    The legacy ``lives`` field represents Scorte for the v0.5 transition, and
    ``critical_wounds`` represents Affamato cards already received.
    """

    if card_id not in V05_HUNGER_CARD_IDS:
        raise ValueError(f"Unknown v0.5 hunger effect '{card_id}'")

    if card_id in V05_HUNGER_UNIMPLEMENTED_EFFECTS:
        raise NotImplementedError(
            f"v0.5 hunger effect '{V05_HUNGER_CARD_NAMES[card_id]}' "
            f"({card_id}) is not implemented yet."
        )

    if card_id == BRICIOLA_NASCOSTA:
        before = player.lives
        player.lives = min(config.initial_lives, player.lives + 1)
        life_delta = player.lives - before
        player.life_gained_from_critical_cards += life_delta
        return life_delta

    if card_id == RAZIONE_RISPARMIATA:
        player.active_critical_effects.append(card_id)
        return 0

    if card_id == FIUTO_DA_DISPENSA:
        player.active_critical_effects.append(card_id)
        return 0

    raise NotImplementedError(f"v0.5 hunger effect '{card_id}' is not implemented yet.")
