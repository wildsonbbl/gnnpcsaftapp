"""Shared plot handlers for mixture screens."""

from app.plot_requests import PlotRequest
from app.utils_data import (
    retrieve_bubble_pressure_data,
    retrieve_rho_binary_data,
    retrieve_rho_ternary_data,
)
from app.utils_mix import MixDenParams, MixVpParams, mix_den, mix_vp


# pylint: disable = w0212
def plot_density(layout, smiles_list):
    """Plot mixture density vs temperature for any component count."""
    n = len(smiles_list)
    fractions = layout._get_fractions(n)
    kij_matrix = layout._get_kij(n)
    t_min, t_max = layout._get_temperatures(require_max=True)
    p_val = layout._get_pressure()
    npoints = layout._get_npoints()

    exp_data = None
    try:
        if len(smiles_list) == 2:
            exp_array = retrieve_rho_binary_data(
                smiles_list, p_val / 1000.0, fractions[0]
            )
            if exp_array is not None and len(exp_array) > 0:
                exp_data = (exp_array[:, 0], exp_array[:, 1], "Exp. Data")
        elif len(smiles_list) == 3 and len(fractions) >= 2:
            exp_array = retrieve_rho_ternary_data(
                smiles_list, p_val / 1000.0, fractions[0], fractions[1]
            )
            if exp_array is not None and len(exp_array) > 0:
                exp_data = (exp_array[:, 0], exp_array[:, 1], "Exp. Data")
    except (ValueError, RuntimeError):
        pass

    mix_den_params = MixDenParams(
        smiles_list=smiles_list,
        mole_fractions=fractions,
        kij_matrix=kij_matrix,
        min_temp=t_min,
        max_temp=t_max,
        pressure=p_val,
        npoints=npoints,
    )
    temperatures, densities = mix_den(mix_den_params)
    layout._generate_plot(
        PlotRequest(
            x_data=temperatures,
            y_data=densities,
            title=f"Density at P={p_val} Pa and mole fractions={fractions}",
            x_label="Temperature (K)",
            y_label="Density (mol/m³)",
            exp_data=exp_data,
        )
    )


# pylint: disable = w0212
def plot_vp(layout, smiles_list):
    """Plot mixture vapor pressure vs temperature for any component count."""
    n = len(smiles_list)
    fractions = layout._get_fractions(n)
    kij_matrix = layout._get_kij(n)
    t_min, t_max = layout._get_temperatures(require_max=True)
    npoints = layout._get_npoints()

    exp_data = None
    try:
        if len(smiles_list) == 2:
            exp_bp = retrieve_bubble_pressure_data(smiles_list, fractions[0])
            if exp_bp is not None and len(exp_bp) > 0:
                exp_data = (
                    exp_bp[:, 0],
                    exp_bp[:, 1] * 1000.0,
                    "Exp. Bubble P",
                )
    except (ValueError, RuntimeError):
        pass

    mix_vp_params = MixVpParams(
        smiles_list=smiles_list,
        mole_fractions=fractions,
        kij_matrix=kij_matrix,
        min_temp=t_min,
        max_temp=t_max,
        npoints=npoints,
    )
    temperatures, bubbles, dews = mix_vp(mix_vp_params)
    layout._generate_plot(
        PlotRequest(
            x_data=temperatures,
            y_data=[bubbles, dews],
            title=f"VLE at mole fractions={fractions}",
            x_label="Temperature (K)",
            y_label="Pressure (Pa)",
            legends=["Bubble Point", "Dew Point"],
            exp_data=exp_data,
        )
    )
