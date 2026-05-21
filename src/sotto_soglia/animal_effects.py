"""Animal-card metadata for Il Patto del Bosco v0.5."""

from dataclasses import dataclass
from enum import Enum

from sotto_soglia.models import Card, Color, PlayerState


class Animal(Enum):
    """Semantic animal owner for v0.5 cards.

    Color remains the technical identifier used by players and cards for now.
    """

    PANDA = "panda"
    CONIGLIO = "coniglio"
    SCIMMIA = "scimmia"
    SCOIATTOLO = "scoiattolo"


ANIMAL_BY_COLOR: dict[Color, Animal] = {
    Color.BLUE: Animal.PANDA,
    Color.RED: Animal.CONIGLIO,
    Color.GREEN: Animal.SCIMMIA,
    Color.YELLOW: Animal.SCOIATTOLO,
}

COLOR_BY_ANIMAL: dict[Animal, Color] = {
    animal: color
    for color, animal in ANIMAL_BY_COLOR.items()
}

ANIMAL_DISPLAY_NAMES: dict[Animal, str] = {
    Animal.PANDA: "Panda",
    Animal.CONIGLIO: "Coniglio",
    Animal.SCIMMIA: "Scimmia",
    Animal.SCOIATTOLO: "Scoiattolo",
}

ANIMAL_DISPLAY_COLORS: dict[Animal, str] = {
    Animal.PANDA: "green",
    Animal.CONIGLIO: "orange",
    Animal.SCIMMIA: "yellow",
    Animal.SCOIATTOLO: "brown",
}

PANDA_RIPOSO_FORZATO = "panda_riposo_forzato"
PANDA_RESPIRO_LENTO = "panda_respiro_lento"
PANDA_GRANDE_LETARGO = "panda_grande_letargo"
CONIGLIO_SCATTO_IMPROVVISO = "coniglio_scatto_improvviso"
CONIGLIO_PASSO_LEGGERO = "coniglio_passo_leggero"
CONIGLIO_GRANDE_BALZO = "coniglio_grande_balzo"
SCIMMIA_FINTA_INNOCENTE = "scimmia_finta_innocente"
SCIMMIA_BUCCIA_DI_BANANA = "scimmia_buccia_di_banana"
SCIMMIA_BANANA_RUBATA = "scimmia_banana_rubata"
SCOIATTOLO_GHIANDA_NASCOSTA = "scoiattolo_ghianda_nascosta"
SCOIATTOLO_PICCOLA_RISERVA = "scoiattolo_piccola_riserva"
SCOIATTOLO_DISPENSA_ORDINATA = "scoiattolo_dispensa_ordinata"


@dataclass(frozen=True)
class AnimalCardEffectProfile:
    """Static metadata for one v0.5 animal card."""

    animal: Animal
    printed_value: int
    has_effect: bool
    effect_id: str | None = None
    effect_name: str | None = None
    timing: str | None = None


@dataclass(frozen=True)
class AnimalEffectEvent:
    """Internal telemetry for one animal-card effect event."""

    player_id: int
    animal: str
    card_color: str
    card_value: int
    effect_id: str
    effect_name: str
    timing: str
    status: str
    target_player_id: int | None = None
    value_before: int | None = None
    value_after: int | None = None
    amount: int | None = None
    actual_amount: int | None = None
    reason: str | None = None


def _profile(
    animal: Animal,
    printed_value: int,
    effect_id: str | None = None,
    effect_name: str | None = None,
    timing: str | None = None,
) -> AnimalCardEffectProfile:
    """Build one animal-card profile."""

    return AnimalCardEffectProfile(
        animal=animal,
        printed_value=printed_value,
        has_effect=effect_id is not None,
        effect_id=effect_id,
        effect_name=effect_name,
        timing=timing,
    )


ANIMAL_CARD_EFFECTS: dict[tuple[Animal, int], AnimalCardEffectProfile] = {
    (Animal.PANDA, 1): _profile(
        Animal.PANDA,
        1,
        PANDA_RIPOSO_FORZATO,
        "Riposo Forzato",
    ),
    (Animal.PANDA, 2): _profile(Animal.PANDA, 2),
    (Animal.PANDA, 3): _profile(
        Animal.PANDA,
        3,
        PANDA_RESPIRO_LENTO,
        "Respiro Lento",
    ),
    (Animal.PANDA, 4): _profile(Animal.PANDA, 4),
    (Animal.PANDA, 5): _profile(
        Animal.PANDA,
        5,
        PANDA_GRANDE_LETARGO,
        "Grande Letargo",
    ),
    (Animal.CONIGLIO, 1): _profile(
        Animal.CONIGLIO,
        1,
        CONIGLIO_SCATTO_IMPROVVISO,
        "Scatto Improvviso",
    ),
    (Animal.CONIGLIO, 2): _profile(
        Animal.CONIGLIO,
        2,
        CONIGLIO_PASSO_LEGGERO,
        "Passo Leggero",
    ),
    (Animal.CONIGLIO, 3): _profile(Animal.CONIGLIO, 3),
    (Animal.CONIGLIO, 4): _profile(
        Animal.CONIGLIO,
        4,
        CONIGLIO_GRANDE_BALZO,
        "Grande Balzo",
    ),
    (Animal.CONIGLIO, 5): _profile(Animal.CONIGLIO, 5),
    (Animal.SCIMMIA, 1): _profile(
        Animal.SCIMMIA,
        1,
        SCIMMIA_FINTA_INNOCENTE,
        "Finta Innocente",
    ),
    (Animal.SCIMMIA, 2): _profile(
        Animal.SCIMMIA,
        2,
        SCIMMIA_BUCCIA_DI_BANANA,
        "Buccia di Banana",
    ),
    (Animal.SCIMMIA, 3): _profile(Animal.SCIMMIA, 3),
    (Animal.SCIMMIA, 4): _profile(Animal.SCIMMIA, 4),
    (Animal.SCIMMIA, 5): _profile(
        Animal.SCIMMIA,
        5,
        SCIMMIA_BANANA_RUBATA,
        "Banana Rubata",
    ),
    (Animal.SCOIATTOLO, 1): _profile(
        Animal.SCOIATTOLO,
        1,
        SCOIATTOLO_GHIANDA_NASCOSTA,
        "Ghianda Nascosta",
    ),
    (Animal.SCOIATTOLO, 2): _profile(Animal.SCOIATTOLO, 2),
    (Animal.SCOIATTOLO, 3): _profile(
        Animal.SCOIATTOLO,
        3,
        SCOIATTOLO_PICCOLA_RISERVA,
        "Piccola Riserva",
    ),
    (Animal.SCOIATTOLO, 4): _profile(
        Animal.SCOIATTOLO,
        4,
        SCOIATTOLO_DISPENSA_ORDINATA,
        "Dispensa Ordinata",
    ),
    (Animal.SCOIATTOLO, 5): _profile(Animal.SCOIATTOLO, 5),
}


def get_animal_for_color(color: Color) -> Animal:
    """Return the v0.5 animal mapped to a technical color."""

    return ANIMAL_BY_COLOR[color]


def get_display_color_for_animal(animal: Animal) -> str:
    """Return the physical game color displayed for an animal."""

    return ANIMAL_DISPLAY_COLORS[animal]


def get_display_color_for_technical_color(color: Color) -> str:
    """Return the physical display color for a legacy technical color."""

    return get_display_color_for_animal(get_animal_for_color(color))


def get_animal_card_profile(card: Card) -> AnimalCardEffectProfile | None:
    """Return metadata for an animal card, if the color/value pair is known."""

    animal = ANIMAL_BY_COLOR.get(card.color)
    if animal is None:
        return None
    return ANIMAL_CARD_EFFECTS.get((animal, card.value))


def get_animal_card_effect(card: Card) -> AnimalCardEffectProfile | None:
    """Return effect metadata only when the animal card has an effect."""

    profile = get_animal_card_profile(card)
    if profile is None or not profile.has_effect:
        return None
    return profile


def has_animal_card_effect(card: Card) -> bool:
    """Return whether a card has a v0.5 animal effect."""

    return get_animal_card_effect(card) is not None


def get_effect_id_for_card(card: Card) -> str | None:
    """Return the technical effect id for a v0.5 animal card, if any."""

    effect = get_animal_card_effect(card)
    if effect is None:
        return None
    return effect.effect_id


def is_own_animal_card_effect_active(player: PlayerState, card: Card) -> bool:
    """Return whether the card effect would activate for this player.

    This only checks ownership and metadata. It does not apply any effect.
    """

    effect = get_animal_card_effect(card)
    if effect is None:
        return False
    return ANIMAL_BY_COLOR.get(player.color) == effect.animal
