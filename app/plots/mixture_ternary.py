"""Plot handlers for mixture screens."""

from gnnepcsaft_mcp_server.utils_data import (
    retrieve_lle_ternary_data,
    retrieve_vle_ternary_data,
    retrieve_vle_ternary_tx_fixed_data,
)
from gnnepcsaft_mcp_server.utils_mix import (
    TernaryVleTxParams,
    mix_ternary_lle,
    mix_ternary_vle_tx_fixed,
)

from app.plot_requests import PlotRequest, TernaryPlotRequest


# pylint: disable = w0212
def plot_vle_lle(layout):
    """Plot ternary VLE/LLE on a ternary diagram at fixed P and T."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 3:
        raise ValueError(
            f"VLE/LLE for ternary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    kij_matrix, t_min, p_val = layout.get_kij_tmin_pressure(n)
    npoints = layout._get_npoints()
    assert p_val is not None

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

    output = mix_ternary_lle(smiles_list, kij_matrix, t_min, p_val, npoints)

    layout._generate_ternary_plot(
        TernaryPlotRequest(
            a=[output["x0"], output["y0"]],
            b=[output["x1"], output["y1"]],
            title=f"VLE/LLE at P={p_val} Pa, T={t_min} K",
            a_label=smiles_list[0],
            b_label=smiles_list[1],
            legends=["Phase 1", "Phase 2"],
            exp_data=exp_data,
        )
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
    npoints = layout._get_npoints()

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

    vle_params = TernaryVleTxParams(
        smiles_list=smiles_list,
        kij_matrix=kij_matrix,
        temperature=t_min,
        solvent_ratio=solvent_ratio,
        npoints=npoints,
        mole_fractions=exp_data and exp_data[0].tolist(),
    )
    x1_values, bubble_pressures, dew_pressures = mix_ternary_vle_tx_fixed(vle_params)

    if not x1_values:
        raise RuntimeError(
            "No valid VLE points found. Try adjusting temperature or composition"
        )

    layout._generate_plot(
        PlotRequest(
            x_data=x1_values,
            y_data=[bubble_pressures, dew_pressures],
            title=(
                f"Ternary VLE P-x at T={t_min} K\n"
                f"Fixed solvent ratio x2/(x2+x3)={solvent_ratio:.3f}"
            ),
            x_label=f"x({smiles_list[0]})",
            y_label="Pressure (Pa)",
            legends=["Bubble Point", "Dew Point"],
            exp_data=exp_data,
        )
    )
