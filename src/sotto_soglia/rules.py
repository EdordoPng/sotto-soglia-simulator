"""Rule functions for Sotto Soglia.

The full game rules will be implemented incrementally in later phases.
"""


def find_lowest_value_cards(*args, **kwargs):
    """Find cards with the lowest revealed value.

    TODO: Implement lowest-value tie handling.
    """

    raise NotImplementedError


def calculate_base_damage(*args, **kwargs):
    """Calculate base damage for a selected card.

    TODO: Implement self-color reduction and minimum damage rules.
    """

    raise NotImplementedError


def apply_color_effects(*args, **kwargs):
    """Apply cumulative color effects to affected players.

    TODO: Implement extra damage for opponent-color cards.
    """

    raise NotImplementedError


def resolve_eliminations(*args, **kwargs):
    """Resolve player eliminations after round damage.

    TODO: Implement life and critical-wound elimination checks.
    """

    raise NotImplementedError


def resolve_final_tiebreaker(*args, **kwargs):
    """Resolve final-round simultaneous elimination tiebreakers.

    TODO: Implement critical-wound, previous-life and draw logic.
    """

    raise NotImplementedError
