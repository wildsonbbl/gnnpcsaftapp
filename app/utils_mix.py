"Mixture screen utilities"

from typing import Dict, List, Tuple

import numpy as np
from gnnepcsaft.pcsaft.pcsaft_feos import (
    mix_den_feos,
    mix_lle_diagram_feos,
    mix_lle_feos,
    mix_vle_diagram_feos,
    mix_vp_feos,
)
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters


def mix_den(
    smiles_list: List[str],
    mole_fractions: List[float],
    kij_matrix: List[List[float]],
    min_temp: float,
    max_temp: float,
    pressure: float,
) -> Tuple[List[float], List[float]]:
    "Calculate mixture density using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]
    temperatures = np.linspace(min_temp, max_temp, num=10).tolist()

    densities = [
        mix_den_feos(
            parameters=parameters_list,
            state=[T, pressure] + mole_fractions,
            kij_matrix=kij_matrix,
        )
        for T in temperatures
    ]
    return temperatures, densities


def mix_vp(
    smiles_list: List[str],
    mole_fractions: List[float],
    kij_matrix: List[List[float]],
    min_temp: float,
    max_temp: float,
) -> Tuple[List[float], List[float], List[float]]:
    "Calculate mixture vapor pressure using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]
    temperatures = np.linspace(min_temp, max_temp, num=10).tolist()

    buble_points = []
    dew_point = []
    for temp in temperatures:
        x_bubble, y_dew = mix_vp_feos(
            parameters=parameters_list,
            state=[temp, 0] + mole_fractions,
            kij_matrix=kij_matrix,
        )
        buble_points.append(x_bubble)
        dew_point.append(y_dew)
    return temperatures, buble_points, dew_point


def mix_vle(
    smiles_list: List[str],
    kij_matrix: List[List[float]],
    pressure: float,
) -> Dict[str, List[float]]:
    "Calculate mixture VLE using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]

    return mix_vle_diagram_feos(
        parameters=parameters_list, state=[pressure], kij_matrix=kij_matrix
    )


def mix_lle(
    smiles_list: List[str],
    mole_fractions: List[float],
    kij_matrix: List[List[float]],
    temperature: float,
    pressure: float,
) -> Dict[str, List[float]]:
    "Calculate mixture LLE using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]

    return mix_lle_diagram_feos(
        parameters=parameters_list,
        state=[temperature, pressure, *mole_fractions],
        kij_matrix=kij_matrix,
    )


def _get_ternary_lle_data(
    params: List[List[float]],
    state: List[float],
    kij_matrix: List[List[float]],
) -> Dict[str, List[float]]:
    t, p = state  # Temperatura (K) e pressão (Pa)

    def _grid(n_pts: int = 25):
        xi = np.linspace(1e-5, 0.999, n_pts, dtype=np.float64)
        x1_m, x2_m = np.meshgrid(xi, xi, indexing="xy")
        x3_m = 1.0 - x1_m - x2_m
        return x1_m, x2_m, x3_m, (x3_m >= 0.0)

    def _collect_tie_lines(x1_m, x2_m, x3_m, mask):
        valid_idx = np.argwhere(mask)
        ternary_data = {"x0": [], "x1": [], "x2": [], "y0": [], "y1": [], "y2": []}
        for i, j in valid_idx:
            try:
                lle = mix_lle_feos(
                    params,
                    [t, p, x1_m[i, j].item(), x2_m[i, j].item(), x3_m[i, j].item()],
                    kij_matrix,
                )
            except (RuntimeError, ValueError):
                continue
            # For LLE, y is one phase and x is the other phase
            ternary_data["x0"].extend(lle["x0"])
            ternary_data["x1"].extend(lle["x1"])
            ternary_data["x2"].extend(lle["x2"])
            ternary_data["y0"].extend(lle["y0"])
            ternary_data["y1"].extend(lle["y1"])
            ternary_data["y2"].extend(lle["y2"])
        return ternary_data

    x1, x2, x3, mask = _grid()
    return _collect_tie_lines(x1, x2, x3, mask)


def mix_ternary_lle(
    smiles_list: List[str],
    kij_matrix: List[List[float]],
    temperature: float,
    pressure: float,
) -> Dict[str, List[float]]:
    "Calculate ternary LLE/VLE using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]

    return _get_ternary_lle_data(
        params=parameters_list,
        state=[temperature, pressure],
        kij_matrix=kij_matrix,
    )
