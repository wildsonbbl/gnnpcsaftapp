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
        .select("T_K", "rho")
        .to_numpy()
    )


def retrieve_vp_pure_data(smiles: str, temp_min: float, temp_max: float):
    "retrieve vapor pressure data for plots"

    df = pl.read_parquet(osp.join(application_path, "_data", "rho_pure.parquet"))

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
