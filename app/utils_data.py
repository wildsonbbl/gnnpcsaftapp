"Experimental data utilitis"

import os.path as osp

import polars as pl

from gnnepcsaft_mcp_server.utils import smilestoinchi

application_path = osp.dirname(osp.abspath(__file__))


def retrieve_rho_pure_data(smiles: str, pressure: float):
    "retrieve density data for plots"

    df = pl.read_parquet(osp.join(application_path, "_data", "rho_pure.parquet"))

    return (
        df.filter(
            pl.col("inchi1") == smilestoinchi(smiles), pl.col("P_kPa") == pressure
        )
        .select(
            pl.col("T_K"),
            (pl.col("rho") * 1000 / pl.col("molweight1")),
        )
        .to_numpy()
    )


def retrieve_vp_pure_data(smiles: str, temp_min: float, temp_max: float):
    "retrieve vapor pressure data for plots"

    df = pl.read_parquet(osp.join(application_path, "_data", "vp_pure.parquet"))

    return (
        df.filter(
            pl.col("inchi1") == smilestoinchi(smiles),
            pl.col("T_K") >= temp_min,
            pl.col("T_K") <= temp_max,
        )
        .select("T_K", "VP_kPa")
        .to_numpy()
    )


def retrieve_available_data_pure(smiles: str):
    "retrieve available pure data for smiles"

    rho_pure = pl.read_parquet(osp.join(application_path, "_data", "rho_pure.parquet"))
    vp_pure = pl.read_parquet(osp.join(application_path, "_data", "vp_pure.parquet"))

    try:
        inchi = smilestoinchi(smiles)
    except ValueError:
        return None, (None, None)

    rho_filtered = rho_pure.filter(pl.col("inchi1") == inchi)
    if rho_filtered.height > 0:
        pure_data = (
            rho_filtered.select("T_K", "P_kPa")
            .group_by(pl.col("P_kPa"))
            .agg(
                pl.col("T_K").min().alias("T_min"),
                pl.col("T_K").max().alias("T_max"),
            )
            .sort(pl.col("P_kPa"))
            .to_numpy()
        )
    else:
        pure_data = None

    vp_filtered = vp_pure.filter(pl.col("inchi1") == inchi)
    if vp_filtered.height > 0:
        vp_data = vp_filtered.select("T_K").to_numpy()
        vp_range = (vp_data.min(), vp_data.max())
    else:
        vp_range = (None, None)

    return pure_data, vp_range


def retrieve_rho_binary_data(smiles_list: list, pressure: float, x1: float):
    "retrieve binary density data"
    if len(smiles_list) != 2:
        return None

    df = pl.read_parquet(osp.join(application_path, "_data", "rho_binary.parquet"))
    i1, i2 = smilestoinchi(smiles_list[0]), smilestoinchi(smiles_list[1])

    # Tolerance
    tol_x = 0.001

    # Normalize x1 to strictly match input order
    # If file has (i1, i2) -> use mole_fraction_c1
    # If file has (i2, i1) -> use mole_fraction_c2
    filtered = (
        df.filter(
            ((pl.col("inchi1") == i1) & (pl.col("inchi2") == i2))
            | ((pl.col("inchi1") == i2) & (pl.col("inchi2") == i1))
        )
        .with_columns(
            pl.when(pl.col("inchi1") == i1)
            .then(pl.col("mole_fraction_c1"))
            .otherwise(pl.col("mole_fraction_c2"))
            .alias("x_c1")
        )
        .filter(
            (pl.col("P_kPa") == pressure)
            & (pl.col("x_c1") > x1 - tol_x)
            & (pl.col("x_c1") < x1 + tol_x)
        )
    )

    if filtered.height == 0:
        return None

    return (
        filtered.select(
            pl.col("T_K"),
            pl.col("rho")
            * 1000
            / (
                pl.col("molweight1") * pl.col("mole_fraction_c1")
                + pl.col("molweight2") * (1 - pl.col("mole_fraction_c1"))
            ),
        )
        .sort("T_K")
        .to_numpy()
    )


def retrieve_bubble_pressure_data(smiles_list: list, x1: float):
    "retrieve binary bubble point pressure data (P-T at constant x)"
    if len(smiles_list) != 2:
        return None

    df = pl.read_parquet(osp.join(application_path, "_data", "vp_binary.parquet"))
    i1, i2 = smilestoinchi(smiles_list[0]), smilestoinchi(smiles_list[1])

    tol_x = 0.001

    filtered = (
        df.filter(
            ((pl.col("inchi1") == i1) & (pl.col("inchi2") == i2))
            | ((pl.col("inchi1") == i2) & (pl.col("inchi2") == i1))
        )
        .with_columns(
            pl.when(pl.col("inchi1") == i1)
            .then(pl.col("mole_fraction_c1"))
            .otherwise(pl.col("mole_fraction_c2"))
            .alias("x_c1")
        )
        .filter((pl.col("x_c1") > x1 - tol_x) & (pl.col("x_c1") < x1 + tol_x))
    )

    if filtered.height == 0:
        return None

    # Return T and P_kPa
    return filtered.select("T_K", "bubble_point_kPa").sort("T_K").to_numpy()


def retrieve_available_data_binary(smiles_list: list):
    "retrieve available binary data"
    if len(smiles_list) != 2:
        return None, None

    i1, i2 = smilestoinchi(smiles_list[0]), smilestoinchi(smiles_list[1])

    rho_bin = pl.read_parquet(osp.join(application_path, "_data", "rho_binary.parquet"))
    vp_bin = pl.read_parquet(osp.join(application_path, "_data", "vp_binary.parquet"))

    # Helper filter & normalize
    def _filter_norm(dframe, col_x1, col_x2):
        return dframe.filter(
            ((pl.col("inchi1") == i1) & (pl.col("inchi2") == i2))
            | ((pl.col("inchi1") == i2) & (pl.col("inchi2") == i1))
        ).with_columns(
            pl.when(pl.col("inchi1") == i1)
            .then(pl.col(col_x1))
            .otherwise(pl.col(col_x2))
            .alias("x_c1")
        )

    # RHO
    rf = _filter_norm(rho_bin, "mole_fraction_c1", "mole_fraction_c2")
    if rf.height > 0:
        rho_data = (
            rf.group_by(["P_kPa", "x_c1"])
            .agg(
                pl.col("T_K").min().alias("T_min"),
                pl.col("T_K").max().alias("T_max"),
            )
            .sort(["P_kPa", "x_c1"])
            .to_numpy()
        )
    else:
        rho_data = None

    # Bubble Point data (Identify isopleths by grouping approximate composition)
    vf = _filter_norm(vp_bin, "mole_fraction_c1", "mole_fraction_c2")
    if vf.height > 0:
        # Create a rounded x column to group experimental points into "isopleths"
        bubble_data = (
            vf.with_columns((pl.col("x_c1").round(2)).alias("x_approx"))
            .group_by("x_approx")
            .agg(
                pl.col("T_K").min().alias("T_min"),
                pl.col("T_K").max().alias("T_max"),
            )
            .sort("x_approx")
            .to_numpy()
        )
    else:
        bubble_data = None

    return rho_data, bubble_data
