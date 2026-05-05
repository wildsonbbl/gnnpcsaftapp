"""Plot handlers for mixture screens."""

from app.plots.plot_helpers import assign_phase_by_density
from app.utils_data import (
    retrieve_lle_binary_data,
    retrieve_vle_binary_data,
    retrieve_vle_pxy_binary_data,
)
from app.utils_mix import mix_lle, mix_vle, mix_vle_pxy


# pylint: disable = w0212
def plot_vle_txy(layout):
    """Plot binary VLE T-x-y using layout inputs and rendering helpers."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"VLE for binary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    kij_matrix = layout._get_kij(n)
    p_val = layout._get_pressure()

    exp_data = None
    try:
        vle_arr = retrieve_vle_binary_data(smiles_list, p_val / 1000.0)
        if vle_arr is not None and len(vle_arr) > 0:
            exp_data = (vle_arr[:, 1], vle_arr[:, 0], "Exp. Bubble P")
    except (ValueError, RuntimeError):
        pass

    output = mix_vle(smiles_list, kij_matrix, p_val)
    x_liquid, y_vapor = assign_phase_by_density(output)

    layout._generate_plot(
        [x_liquid, y_vapor],
        output["temperature"],
        f"VLE T-x-y for {smiles_list[0]} at {p_val} Pa",
        "x,y",
        "Temperature (K)",
        legends=["Bubble Point", "Dew Point"],
        exp_data=exp_data,
    )


def plot_vle_pxy(layout):
    """Plot binary VLE P-x-y at a fixed temperature."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"VLE for binary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    kij_matrix = layout._get_kij(n)
    t_min, _ = layout._get_temperatures(require_max=False)

    exp_data = None
    try:
        vle_arr = retrieve_vle_pxy_binary_data(smiles_list, t_min)
        if vle_arr is not None and len(vle_arr) > 0:
            exp_data = (
                vle_arr[:, 1],
                vle_arr[:, 0] * 1000.0,
                "Exp. Bubble P",
            )
    except (ValueError, RuntimeError):
        pass

    x0s, bps, dps = mix_vle_pxy(
        smiles_list, kij_matrix, t_min, exp_data and exp_data[0].tolist()
    )

    layout._generate_plot(
        x0s,
        [bps, dps],
        f"VLE P-x-y for {smiles_list[0]} at {t_min} K",
        "x,y",
        "Pressure (Pa)",
        legends=["Bubble Point", "Dew Point"],
        exp_data=exp_data,
    )


def plot_vle_xy(layout):
    """Plot binary VLE x-y diagram at fixed pressure."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"VLE for binary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    kij_matrix = layout._get_kij(n)
    p_val = layout._get_pressure()

    output = mix_vle(smiles_list, kij_matrix, p_val)
    x_liquid, y_vapor = assign_phase_by_density(output)

    layout._generate_plot(
        x_liquid,
        y_vapor,
        f"VLE x-y for {smiles_list[0]} at {p_val} Pa",
        "x",
        "y",
    )


def plot_lle_txx(layout):
    """Plot binary LLE T-x-x using layout inputs and rendering helpers."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"LLE for binary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    fractions = layout._get_fractions(n)
    kij_matrix = layout._get_kij(n)
    t_min, _ = layout._get_temperatures(require_max=False)
    p_val = layout._get_pressure()

    exp_data = None
    try:
        lle_arr = retrieve_lle_binary_data(smiles_list, p_val / 1000.0)
        if lle_arr is not None and len(lle_arr) > 0:
            exp_data = (lle_arr[:, 1], lle_arr[:, 0], "Exp. LLE Data")
    except (ValueError, RuntimeError):
        pass

    output = mix_lle(smiles_list, fractions, kij_matrix, t_min, p_val)
    layout._generate_plot(
        [output["x0"], output["y0"]],
        output["temperature"],
        f"LLE T-x-x for {smiles_list[0]} at {p_val} Pa",
        "x,x",
        "Temperature (K)",
        legends=["Phase 1", "Phase 2"],
        exp_data=exp_data,
    )
