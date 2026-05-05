"Mixture screen utilities"

from typing import Dict, List, Optional, Tuple

import numpy as np
from gnnepcsaft.pcsaft.pcsaft_feos import (
    critical_points_feos,
    mix_den_feos,
    mix_lle_diagram_feos,
    mix_lle_feos,
    mix_vle_diagram_feos,
    mix_vp_feos,
    pure_vp_feos,
)
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters
from kivy.logger import Logger


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
        if x_bubble > y_dew:
            buble_points.append(x_bubble)
            dew_point.append(y_dew)
        else:
            buble_points.append(y_dew)
            dew_point.append(x_bubble)

    return temperatures, buble_points, dew_point


def mix_vle(
    smiles_list: List[str],
    kij_matrix: List[List[float]],
    pressure: float,
) -> Dict[str, List[float]]:
    "Calculate mixture VLE (T-x-y) using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]

    return mix_vle_diagram_feos(
        parameters=parameters_list, state=[pressure], kij_matrix=kij_matrix
    )


def mix_vle_pxy(
    smiles_list: List[str],
    kij_matrix: List[List[float]],
    temperature: float,
    mole_fractions: Optional[List[float]] = None,
) -> Tuple[List[float], List[float], List[float]]:
    "Calculate mixture VLE (P-x-y) using PC-SAFT EOS"
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]
    x0s = np.linspace(0.0, 1.0, num=52, dtype=np.float64).tolist()
    if mole_fractions:
        x0s.extend(mole_fractions)
        x0s = sorted(x0s)

    bps = []
    dps = []
    xs = []

    x0_tc, x0_pc, _ = critical_points_feos(parameters=parameters_list[0])
    x1_tc, x1_pc, _ = critical_points_feos(parameters=parameters_list[1])

    if temperature >= x1_tc and temperature >= x0_tc:
        raise ValueError(
            f"Temperature {temperature} K is above the critical temperature "
            f"of both components, which is {x0_tc:.2f} K and {x1_tc:.2f} K. "
            f"VLE calculation is not meaningful.",
        )

    vp0 = None
    vp1 = None
    try:
        if temperature < x0_tc:
            vp0 = pure_vp_feos(parameters=parameters_list[0], state=[temperature])
    except RuntimeError:
        vp0 = None
    try:
        if temperature < x1_tc:
            vp1 = pure_vp_feos(parameters=parameters_list[1], state=[temperature])
    except RuntimeError:
        vp1 = None

    if vp0 is None and vp1 is None:
        raise ValueError(
            f"Unable to compute pure vapor pressures at {temperature} K for either component; "
            "VLE calculation is not meaningful.",
        )

    # Determina o componente mais volátil pelo valor
    # da pressão de vapor ou pelo estado supercrítico (T > Tc)
    more_volatile_is_first = True
    if vp0 is not None and vp1 is not None:
        if vp0 < vp1:
            more_volatile_is_first = False
    elif vp0 is None and vp1 is not None:
        # Componente 0 está acima da Tc (não tem VP), logo é efetivamente um gás/mais volátil
        more_volatile_is_first = True
    elif vp1 is None and vp0 is not None:
        # Componente 1 está acima da Tc (não tem VP), logo é efetivamente um gás/mais volátil
        more_volatile_is_first = False

    if not more_volatile_is_first:
        raise ValueError(
            f"More volatile component ({smiles_list[1]}) must be listed first in P-x-y calculation",
        )

    min_pc = min(x0_pc, x1_pc)
    max_pc = max(x0_pc, x1_pc)

    # Adicionar ponto puro em x0=0.0 apenas se for seguro calcular VP do componente 1
    if temperature < x1_tc and vp1 is not None:
        xs.append(0.0)
        bps.append(vp1)
        dps.append(vp1)

    for x0 in x0s:
        try:
            bp, dp = mix_vp_feos(
                parameters=parameters_list,
                state=[temperature, np.nan, x0, 1 - x0],
                kij_matrix=kij_matrix,
            )
            # Reject points whose pressures exceed both components' critical pressures
            if bp > max_pc or dp > max_pc:
                Logger.warning(
                    "mix_vle_pxy: breaking from point above both Pc at x0=%.4f: bp=%.2f, dp=%.2f",
                    x0,
                    bp,
                    dp,
                )
                break

            # If pressure is between the smaller and larger Pc, keep point but warn
            if bp > min_pc or dp > min_pc:
                Logger.warning(
                    "mix_vle_pxy: point above one component Pc at x0=%.4f: bp=%.2f, dp=%.2f",
                    x0,
                    bp,
                    dp,
                )
            if bp > dp:
                bps.append(bp)
                dps.append(dp)
            else:
                bps.append(dp)
                dps.append(bp)
            xs.append(x0)
        except RuntimeError as e:
            Logger.debug("mix_vle_pxy: Runtime Error at x0=%.4f: %s", x0, e)
            continue
        except BaseException as e:  # pylint: disable=W0718
            exception_type = type(e).__name__
            if exception_type == "PanicException":
                Logger.warning("mix_vle_pxy: PanicException at x0=%.4f: %s", x0, e)
                continue
            Logger.exception(
                "mix_vle_pxy: unexpected %s at x0=%.4f",
                exception_type,
                x0,
            )
            raise

    return xs, bps, dps


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
            if lle["density liquid"][0] > lle["density vapor"][0]:
                ternary_data["x0"].extend(lle["x0"])
                ternary_data["x1"].extend(lle["x1"])
                ternary_data["x2"].extend(lle["x2"])
                ternary_data["y0"].extend(lle["y0"])
                ternary_data["y1"].extend(lle["y1"])
                ternary_data["y2"].extend(lle["y2"])
            else:
                ternary_data["x0"].extend(lle["y0"])
                ternary_data["x1"].extend(lle["y1"])
                ternary_data["x2"].extend(lle["y2"])
                ternary_data["y0"].extend(lle["x0"])
                ternary_data["y1"].extend(lle["x1"])
                ternary_data["y2"].extend(lle["x2"])
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


def mix_ternary_vle_tx_fixed(
    smiles_list: List[str],
    kij_matrix: List[List[float]],
    temperature: float,
    solvent_ratio: float,
    n_points: int = 52,
    mole_fractions: Optional[List[float]] = None,
) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate ternary isothermal VLE curve (P-x) at fixed solvent ratio.

    solvent_ratio = x2 / (x2 + x3). The first component is scanned in composition.
    """
    parameters_list = [predict_pcsaft_parameters(smiles) for smiles in smiles_list]

    tcs_pcs = [critical_points_feos(parameters=p) for p in parameters_list]
    tcs = [tc for tc, _, _ in tcs_pcs]
    pcs = [pc for _, pc, _ in tcs_pcs]

    if all(temperature >= tc for tc in tcs):
        raise ValueError(
            f"Temperature {temperature} K is above the critical temperature of all components; "
            "VLE calculation is not meaningful.",
        )

    vps = []
    for idx, tc in enumerate(tcs):
        try:
            if temperature < tc:
                vps.append(
                    pure_vp_feos(parameters=parameters_list[idx], state=[temperature])
                )
            else:
                vps.append(None)
        except RuntimeError:
            vps.append(None)

    if all(vp is None for vp in vps):
        raise ValueError(
            f"Unable to compute pure vapor pressures at {temperature} K for any component; "
            "VLE calculation is not meaningful.",
        )

    # Componente mais volatil deve ser o primeiro. Usa VP quando disponivel;
    # componentes supercriticos sao tratados como mais volateis.
    def _volatility_rank(vp, tc):
        if vp is not None:
            return vp
        if temperature >= tc:
            return float("inf")
        return float("-inf")

    ranks = [_volatility_rank(vps[i], tcs[i]) for i in range(3)]
    most_volatile_index = int(np.argmax(ranks))
    if most_volatile_index != 0:
        raise ValueError(
            f"More volatile component ({smiles_list[most_volatile_index]}) must be listed first "
            "in ternary P-x calculation",
        )

    if not 0.0 < solvent_ratio < 1.0:
        raise ValueError(
            f"For ternary P-x, solvent ratio must be between 0 and 1, got ratio = {solvent_ratio}"
        )

    x1_grid = np.linspace(0.0, 1.0, num=n_points, dtype=np.float64).tolist()
    if mole_fractions:
        x1_grid.extend(mole_fractions)
        x1_grid = sorted(x1_grid)

    x1_values = []
    bubble_pressures = []
    dew_pressures = []

    for x1 in x1_grid:
        remaining = 1.0 - x1
        x2 = remaining * solvent_ratio
        x3 = remaining * (1.0 - solvent_ratio)

        if x2 <= 0.0 or x3 <= 0.0:
            continue

        try:
            bubble_p, dew_p = mix_vp_feos(
                parameters=parameters_list,
                state=[temperature, 0.0, float(x1), float(x2), float(x3)],
                kij_matrix=kij_matrix,
            )
        except RuntimeError as e:
            Logger.debug(
                "mix_ternary_vle_tx_fixed: Runtime Error at x1=%.4f, x2=%.4f, x3=%.4f: %s",
                x1,
                x2,
                x3,
                e,
            )
            continue
        except BaseException as e:  # pylint: disable=W0718
            exception_type = type(e).__name__
            if exception_type == "PanicException":
                Logger.warning(
                    "mix_ternary_vle_tx_fixed: PanicException at x1=%.4f, x2=%.4f, x3=%.4f: %s",
                    x1,
                    x2,
                    x3,
                    e,
                )
                continue
            Logger.exception(
                "mix_ternary_vle_tx_fixed: unexpected %s at x1=%.4f, x2=%.4f, x3=%.4f",
                exception_type,
                x1,
                x2,
                x3,
            )
            raise

        max_pc = max(pcs)
        min_pc = min(pcs)
        if bubble_p > max_pc or dew_p > max_pc:
            Logger.warning(
                "mix_ternary_vle_tx_fixed: breaking from "
                "point above all Pc at x1=%.4f: bp=%.2f, dp=%.2f",
                x1,
                bubble_p,
                dew_p,
            )
            break
        if bubble_p > min_pc or dew_p > min_pc:
            Logger.warning(
                "mix_ternary_vle_tx_fixed: point above at least "
                "one Pc at x1=%.4f: bp=%.2f, dp=%.2f",
                x1,
                bubble_p,
                dew_p,
            )

        if (
            np.isfinite(bubble_p)
            and np.isfinite(dew_p)
            and bubble_p > 0.0
            and dew_p > 0.0
        ):
            x1_values.append(float(x1))
            if bubble_p > dew_p:
                bubble_pressures.append(float(bubble_p))
                dew_pressures.append(float(dew_p))
            else:
                bubble_pressures.append(float(dew_p))
                dew_pressures.append(float(bubble_p))

    return x1_values, bubble_pressures, dew_pressures
