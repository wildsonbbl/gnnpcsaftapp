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
