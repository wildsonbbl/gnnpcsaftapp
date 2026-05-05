"""Plot handlers for mixture screens."""

from app.utils_data import (
    retrieve_lle_ternary_data,
    retrieve_vle_ternary_data,
    retrieve_vle_ternary_tx_fixed_data,
)
from app.utils_mix import mix_ternary_lle, mix_ternary_vle_tx_fixed


# pylint: disable = w0212
def plot_vle_lle(layout):
    """Plot ternary VLE/LLE on a ternary diagram at fixed P and T."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 3:
        raise ValueError(
            f"VLE/LLE for ternary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    kij_matrix = layout._get_kij(n)
    t_min, _ = layout._get_temperatures(require_max=False)
    p_val = layout._get_pressure()

    exp_data = None
    try:
        exp_arr = retrieve_lle_ternary_data(smiles_list, p_val / 1000.0, t_min)
        if exp_arr is not None and len(exp_arr) > 0:
            exp_data = (exp_arr[:, 0], exp_arr[:, 1], "Exp. LLE Data")
        else:
            exp_arr_vle = retrieve_vle_ternary_data(smiles_list, p_val / 1000.0, t_min)
            if exp_arr_vle is not None and len(exp_arr_vle) > 0:
                exp_data = (
                    exp_arr_vle[:, 0],
                    exp_arr_vle[:, 1],
                    "Exp. Bubble P",
                )
    except (ValueError, RuntimeError):
        pass

    output = mix_ternary_lle(smiles_list, kij_matrix, t_min, p_val)

    layout._generate_ternary_plot(
        [output["x0"], output["y0"]],
        [output["x1"], output["y1"]],
        title=f"VLE/LLE at {p_val} Pa, {t_min} K",
        a_label=smiles_list[0],
        b_label=smiles_list[1],
        legends=["Phase 1", "Phase 2"],
        exp_data=exp_data,
    )


def plot_vle_tx_fixed(layout):
    """Plot ternary VLE P-x at fixed temperature and solvent ratio."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 3:
        raise ValueError(f"Ternary VLE P-x, got {len(smiles_list)} components instead")

    n = len(smiles_list)
    fractions = layout._get_fractions(n)
    kij_matrix = layout._get_kij(n)
    t_min, _ = layout._get_temperatures(require_max=False)

    solvent_pool = fractions[1] + fractions[2]
    if solvent_pool <= 0.0:
        raise ValueError(
            "For ternary VLE P-x, fractions for components 2 and 3 must be > 0"
        )
    solvent_ratio = fractions[1] / solvent_pool

    exp_data = None
    try:
        exp_arr = retrieve_vle_ternary_tx_fixed_data(smiles_list, t_min, solvent_ratio)
        if exp_arr is not None and len(exp_arr) > 0:
            exp_data = (exp_arr[:, 0], exp_arr[:, 1] * 1000.0, "Exp. Bubble P")
    except (ValueError, RuntimeError):
        pass

    x1_values, bubble_pressures, dew_pressures = mix_ternary_vle_tx_fixed(
        smiles_list,
        kij_matrix,
        t_min,
        solvent_ratio,
        mole_fractions=exp_data and exp_data[0].tolist(),
    )

    if not x1_values:
        raise RuntimeError(
            "No valid VLE points found. Try adjusting temperature or composition"
        )

    layout._generate_plot(
        x1_values,
        [bubble_pressures, dew_pressures],
        (
            f"Ternary VLE P-x at {t_min} K\n"
            f"Fixed solvent ratio x2/(x2+x3)={solvent_ratio:.3f}"
        ),
        f"x({smiles_list[0]})",
        "Pressure (Pa)",
        legends=["Bubble Point", "Dew Point"],
        exp_data=exp_data,
    )
