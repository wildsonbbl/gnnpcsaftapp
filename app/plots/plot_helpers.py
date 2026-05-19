"""Plot handlers for mixture screens."""


def assign_phase_by_density(output):
    """Assign liquid and vapor compositions based on density ordering."""
    dens_l = output["density liquid"]
    dens_v = output["density vapor"]
    x_liquid = []
    y_vapor = []

    for x_liq, y_vap, rho_liq, rho_vap in zip(
        output["x0"], output["y0"], dens_l, dens_v
    ):
        if rho_liq > rho_vap:
            x_liquid.append(x_liq)
            y_vapor.append(y_vap)
        else:
            x_liquid.append(y_vap)
            y_vapor.append(x_liq)

    return x_liquid, y_vapor


# pylint: disable=protected-access
def get_kij_tmin_pressure(layout, n, require_pressure=True):
    """Fetch kij matrix, min temperature, and optionally pressure from layout.

    Parameters
    - layout: layout instance
    - n: number of components
    - require_pressure: if True, will read and return pressure; otherwise returns None
    """
    kij_matrix = layout._get_kij(n)
    t_min, _ = layout._get_temperatures(require_max=False)
    p_val = None
    if require_pressure:
        p_val = layout._get_pressure()
    return kij_matrix, t_min, p_val
