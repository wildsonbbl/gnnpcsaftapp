"""Input validation functions for thermodynamic parameters."""

def validate_temperatures(t_min, t_max, require_max=True):
    """Validate temperature inputs."""
    if t_min <= 0:
        raise ValueError(f"Min temperature must be greater than 0 K, got {t_min}")
    if require_max:
        if t_max <= 0:
            raise ValueError(f"Max temperature must be greater than 0 K, got {t_max}")
        if t_min >= t_max:
            raise ValueError(
                f"Min temperature ({t_min} K) must be less than Max temperature ({t_max} K)"
            )


def validate_pressure(pressure):
    """Validate pressure input."""
    if pressure <= 0:
        raise ValueError(f"Pressure must be a positive value, got {pressure} Pa")


def validate_fractions(fractions):
    """Validate composition fractions."""
    if not fractions:
        raise ValueError("Fractions list cannot be empty")

    for i, f in enumerate(fractions):
        if not 0 <= f <= 1:
            raise ValueError(
                f"Mole fraction at index {i} ({f}) is out of bounds [0, 1]"
            )

    total = sum(fractions)
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Mole fractions must sum to ~1.0, got {total:.3f}")
