"Mixture screen utilities"

from typing import List, Tuple

import numpy as np
from gnnepcsaft.epcsaft.epcsaft_feos import mix_den_feos, mix_vp_feos

from gnnepcsaft_mcp_server.utils import predict_epcsaft_parameters


def mix_den(
    smiles_list: List[str],
    mole_fractions: List[float],
    kij_matrix: List[List[float]],
    min_temp: float,
    max_temp: float,
    pressure: float,
) -> Tuple[List[float], List[float]]:
    "Calculate mixture density using PC-SAFT EOS"
    parameters_list = [predict_epcsaft_parameters(smiles) for smiles in smiles_list]
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
    parameters_list = [predict_epcsaft_parameters(smiles) for smiles in smiles_list]
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
