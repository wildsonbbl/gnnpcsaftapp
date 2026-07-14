"""Plot handlers for mixture screens."""

# pylint: disable = w0212


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


def get_all_input(layout, smiles_list):
    "get input values"
    n = len(smiles_list)
    fractions = layout._get_fractions(n)
    kij_matrix = layout._get_kij(n)
    t_min, t_max = layout._get_temperatures(require_max=True)
    p_val = layout._get_pressure()
    return fractions, kij_matrix, t_min, t_max, p_val
