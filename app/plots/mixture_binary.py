"""Plot handlers for mixture screens."""

from gnnepcsaft_mcp_server.utils_data import (
    retrieve_lle_binary_data,
    retrieve_vle_binary_data,
    retrieve_vle_for_kij,
    retrieve_vle_pxy_binary_data,
    retrieve_vlle_binary_data,
)
from gnnepcsaft_mcp_server.utils_kij import optimize_binary_kij_for_vle
from gnnepcsaft_mcp_server.utils_mix import (
    MixLLEParams,
    mix_lle,
    mix_vle,
    mix_vle_pxy,
)

from app.input_requests import BinaryFillRequest
from app.plot_requests import PlotRequest
from app.plots.plot_helpers import assign_phase_by_density, get_all_input


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
    npoints = layout._get_npoints()

    exp_data = None
    try:
        vle_arr = retrieve_vle_binary_data(smiles_list, p_val / 1000.0)
        if vle_arr is not None and len(vle_arr) > 0:
            exp_data = (vle_arr[:, 1], vle_arr[:, 0], "Exp. Bubble P")
    except (ValueError, RuntimeError):
        pass

    output = mix_vle(smiles_list, kij_matrix, p_val, npoints)
    if output:
        x_liquid, y_vapor = assign_phase_by_density(output)

        layout._generate_plot(
            PlotRequest(
                x_data=[x_liquid, y_vapor],
                y_data=output["temperature"],
                title=f"VLE T-x-y for {smiles_list[0]} at P={p_val} Pa",
                x_label="x,y",
                y_label="Temperature (K)",
                legends=["Bubble Point", "Dew Point"],
                exp_data=exp_data,
            )
        )


def plot_vle_pxy(layout):
    """Plot binary VLE P-x-y at a fixed temperature."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"VLE for binary mixture, got {len(smiles_list)} components instead"
        )

    n = len(smiles_list)
    # For P-x-y we don't require an explicit pressure input; only temperature is needed
    kij_matrix, t_min, _ = layout.get_kij_tmin_pressure(n, require_pressure=False)
    npoints = layout._get_npoints()

    exp_data = None
    try:
        vle_arr = retrieve_vle_pxy_binary_data(smiles_list, t_min)
        if vle_arr is not None and len(vle_arr) > 0:
            exp_data = (
                vle_arr[:, 0],
                vle_arr[:, 1] * 1000.0,
                "Exp. Bubble P",
            )
    except (ValueError, RuntimeError):
        pass

    x0s, bps, dps = mix_vle_pxy(
        smiles_list,
        kij_matrix,
        t_min,
        npoints,
        exp_data and exp_data[0].tolist(),
    )

    layout._generate_plot(
        PlotRequest(
            x_data=x0s,
            y_data=[bps, dps],
            title=f"VLE P-x-y for {smiles_list[0]} at T={t_min} K",
            x_label="x,y",
            y_label="Pressure (Pa)",
            legends=["Bubble Point", "Dew Point"],
            exp_data=exp_data,
        )
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
    npoints = layout._get_npoints()

    output = mix_vle(smiles_list, kij_matrix, p_val, npoints)
    if output:
        x_liquid, y_vapor = assign_phase_by_density(output)

        layout._generate_plot(
            PlotRequest(
                x_data=x_liquid,
                y_data=y_vapor,
                title=f"VLE x-y for {smiles_list[0]} at P={p_val} Pa",
                x_label="x",
                y_label="y",
            )
        )


def plot_lle_txx(layout):
    """Plot binary VLE/LLE T-x-y or T-x-x using layout inputs and rendering helpers."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"VLE/LLE for binary mixture, got {len(smiles_list)} components instead"
        )

    fractions, kij_matrix, t_min, t_max, p_val = get_all_input(layout, smiles_list)

    exp_data = None
    try:
        lle_arr = retrieve_lle_binary_data(smiles_list, p_val / 1000.0)
        vle_arr = retrieve_vle_binary_data(smiles_list, p_val / 1000.0)
        vlle_arr = retrieve_vlle_binary_data(
            smiles_list=smiles_list, pressure=p_val / 1000.0
        )
        if vlle_arr is not None and len(vlle_arr):
            exp_data = (vlle_arr[:, 1], vlle_arr[:, 0], "Exp. VLLE Data")
        elif lle_arr is not None and len(lle_arr) > 0:
            exp_data = (lle_arr[:, 1], lle_arr[:, 0], "Exp. LLE Data")
        elif vle_arr is not None and len(vle_arr) > 0:
            exp_data = (vle_arr[:, 1], vle_arr[:, 0], "Exp. VLE Data")
    except (ValueError, RuntimeError):
        pass

    params = MixLLEParams(
        smiles_list=smiles_list,
        mole_fractions=fractions,
        kij_matrix=kij_matrix,
        temperature_min=t_min,
        temperature_max=t_max,
        pressure=p_val,
        npoints=layout._get_npoints(),
    )
    output = mix_lle(params)
    if output:
        layout._generate_plot(
            PlotRequest(
                x_data=[output["x0"], output["y0"]],
                y_data=output["temperature"],
                title=f"VLE/LLE T-x-y/T-x-x for {smiles_list[0]} at P={p_val} Pa",
                x_label="x,y or x,x",
                y_label="Temperature (K)",
                legends=["Phase 1", "Phase 2"],
                exp_data=exp_data,
            )
        )


def plot_vlle_txx(layout):
    """Plot binary VLLE using layout inputs and rendering helpers."""
    smiles_list = layout._get_smiles()
    if len(smiles_list) != 2:
        raise ValueError(
            f"VLLE for binary mixture, got {len(smiles_list)} components instead"
        )

    fractions, kij_matrix, t_min, t_max, p_val = get_all_input(layout, smiles_list)

    exp_data = None
    try:
        lle_arr = retrieve_lle_binary_data(smiles_list, p_val / 1000.0)
        vle_arr = retrieve_vle_binary_data(smiles_list, p_val / 1000.0)
        vlle_arr = retrieve_vlle_binary_data(
            smiles_list=smiles_list, pressure=p_val / 1000.0
        )
        if vlle_arr is not None and len(vlle_arr):
            exp_data = (vlle_arr[:, 1], vlle_arr[:, 0], "Exp. VLLE Data")
        elif lle_arr is not None and len(lle_arr) > 0:
            exp_data = (lle_arr[:, 1], lle_arr[:, 0], "Exp. LLE Data")
        elif vle_arr is not None and len(vle_arr) > 0:
            exp_data = (vle_arr[:, 1], vle_arr[:, 0], "Exp. VLE Data")
    except (ValueError, RuntimeError):
        pass

    params = MixLLEParams(
        smiles_list=smiles_list,
        mole_fractions=fractions,
        kij_matrix=kij_matrix,
        temperature_min=t_min,
        temperature_max=t_max,
        pressure=p_val,
        npoints=layout._get_npoints(),
    )
    output_lle = mix_lle(params)
    output_vle = mix_vle(
        smiles_list=smiles_list,
        kij_matrix=kij_matrix,
        pressure=p_val,
        npoints=layout._get_npoints(),
    )
    if output_lle is not None and output_vle is not None:
        layout._generate_plot(
            PlotRequest(
                x_data=[
                    output_lle["x0"],
                    output_lle["y0"],
                    output_vle["x0"],
                    output_vle["y0"],
                ],
                y_data=[
                    output_lle["temperature"],
                    output_lle["temperature"],
                    output_vle["temperature"],
                    output_vle["temperature"],
                ],
                title=f"VLLE for {smiles_list[0]} at P={p_val} Pa",
                x_label="x,y and x,x",
                y_label="Temperature (K)",
                legends=["Phase 1 LLE", "Phase 2 LLE", "Phase 1 VLE", "Phase 2 VLE"],
                exp_data=exp_data,
            )
        )


def estimate_kij(layout):
    "estimate binary kij"
    try:
        smiles_list = layout._get_smiles()
        n = len(smiles_list)
        if n != 2:
            raise ValueError(
                f"Estimate kij available for binary mixture, "
                f"got {len(smiles_list)} components instead"
            )
        kij_matrix = layout._get_kij(n)
        initial_kij = kij_matrix[0][1]
        vle = retrieve_vle_for_kij(smiles_list=smiles_list)
        if vle is not None:
            kij_value = optimize_binary_kij_for_vle(
                smiles_list=smiles_list, initial_kij=initial_kij, vle=vle
            )
            layout._fill_inputs_binary(BinaryFillRequest(kij=round(kij_value, 4)))
        else:
            raise ValueError("No vle available to optimize kij")

    except (ValueError, RuntimeError) as e:
        layout._show_error_alert(e)
