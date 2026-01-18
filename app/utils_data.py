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
    tol_x = 0.01

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

    tol_x = 0.01

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


def retrieve_lle_binary_data(smiles_list: list, pressure: float):
    "retrieve binary LLE data (T-x-x)"
    if len(smiles_list) != 2:
        return None

    path = osp.join(application_path, "_data", "lle_binary.parquet")
    if not osp.exists(path):
        return None

    df = pl.read_parquet(path)
    i1, i2 = smilestoinchi(smiles_list[0]), smilestoinchi(smiles_list[1])

    # Filter
    filtered = df.filter(
        ((pl.col("inchi1") == i1) & (pl.col("inchi2") == i2))
        | ((pl.col("inchi1") == i2) & (pl.col("inchi2") == i1))
    ).filter(pl.col("P_kPa") == pressure)

    if filtered.height == 0:
        return None

    # Normalize x1 to strictly match input order
    # If file has (i1, i2) -> use mole_fraction_c1
    # If file has (i2, i1) -> use mole_fraction_c2

    data = (
        filtered.with_columns(
            pl.when(pl.col("inchi1") == i1)
            .then(pl.col("mole_fraction_c1"))
            .otherwise(pl.col("mole_fraction_c2"))
            .alias("x_c1"),
        )
        .select("T_K", "x_c1")
        .sort("T_K")
    )

    return data.to_numpy()


def retrieve_available_data_binary(smiles_list: list):
    "retrieve available binary data"
    if len(smiles_list) != 2:
        return None, None, None

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
            rf.with_columns((pl.col("x_c1").round(2)).alias("x_approx"))
            .group_by(["P_kPa", "x_approx"])
            .agg(
                pl.col("T_K").min().alias("T_min"),
                pl.col("T_K").max().alias("T_max"),
            )
            .sort(["P_kPa", "x_approx"])
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

    # LLE checking
    lle_data = None
    path_lle = osp.join(application_path, "_data", "lle_binary.parquet")
    if osp.exists(path_lle):
        df_lle = pl.read_parquet(path_lle)
        # Filter
        lf = _filter_norm(df_lle, "mole_fraction_c1", "mole_fraction_c2")
        if lf.height > 0:
            lle_data = (
                lf.group_by("P_kPa")
                .agg(
                    pl.col("T_K").min().alias("T_min"),
                    pl.col("T_K").max().alias("T_max"),
                )
                .sort("P_kPa")
                .to_numpy()
            )

    return rho_data, bubble_data, lle_data


def retrieve_available_data_ternary(smiles_list: list):
    "retrieve available ternary data"
    if len(smiles_list) != 3:
        return None, None

    i1, i2, i3 = (
        smilestoinchi(smiles_list[0]),
        smilestoinchi(smiles_list[1]),
        smilestoinchi(smiles_list[2]),
    )
    target_set = [i1, i2, i3]

    # --- RHO Data ---
    rho_data = None
    path_rho = osp.join(application_path, "_data", "rho_ternary.parquet")
    if osp.exists(path_rho):

        df = pl.read_parquet(path_rho)

        # Filter for components (exact set match)
        filter_expr = (
            pl.col("inchi1").is_in(target_set)
            & pl.col("inchi2").is_in(target_set)
            & pl.col("inchi3").is_in(target_set)
        )

        filtered = df.filter(filter_expr)

        if filtered.height > 0:
            # Map mole fractions to input order
            data = (
                filtered.with_columns(
                    [
                        pl.when(pl.col("inchi1") == i1)
                        .then(pl.col("mole_fraction_c1"))
                        .otherwise(
                            pl.when(pl.col("inchi2") == i1)
                            .then(pl.col("mole_fraction_c2"))
                            .otherwise(pl.col("mole_fraction_c3"))
                        )
                        .alias("x_mapped_1"),
                        pl.when(pl.col("inchi1") == i2)
                        .then(pl.col("mole_fraction_c1"))
                        .otherwise(
                            pl.when(pl.col("inchi2") == i2)
                            .then(pl.col("mole_fraction_c2"))
                            .otherwise(pl.col("mole_fraction_c3"))
                        )
                        .alias("x_mapped_2"),
                    ]
                )
                .with_columns(
                    [
                        pl.col("x_mapped_1").round(2).alias("x_approx_1"),
                        pl.col("x_mapped_2").round(2).alias("x_approx_2"),
                    ]
                )
                .group_by(["P_kPa", "x_approx_1", "x_approx_2"])
                .agg(
                    pl.col("T_K").min().alias("T_min"),
                    pl.col("T_K").max().alias("T_max"),
                )
                .sort(["P_kPa", "x_approx_1", "x_approx_2"])
            )

            if data.height > 0:
                rho_data = data.to_numpy()

    # --- LLE Data ---
    lle_data = None
    path_lle = osp.join(application_path, "_data", "lle_ternary.parquet")
    if osp.exists(path_lle):
        df_lle = pl.read_parquet(path_lle)
        filter_expr_lle = (
            pl.col("inchi1").is_in(target_set)
            & pl.col("inchi2").is_in(target_set)
            & pl.col("inchi3").is_in(target_set)
        )
        filtered_lle = df_lle.filter(filter_expr_lle)

        if filtered_lle.height > 0:
            # Group by P and T to find available isotherms/isobars
            lle_data = (
                filtered_lle.select("P_kPa", "T_K")
                .unique()
                .sort(["P_kPa", "T_K"])
                .to_numpy()
            )

    return rho_data, lle_data


def retrieve_rho_ternary_data(smiles_list: list, pressure: float, x1: float, x2: float):
    "retrieve ternary density data"
    if len(smiles_list) != 3:
        return None

    path_rho = osp.join(application_path, "_data", "rho_ternary.parquet")
    if not osp.exists(path_rho):
        return None

    i1, i2, i3 = (
        smilestoinchi(smiles_list[0]),
        smilestoinchi(smiles_list[1]),
        smilestoinchi(smiles_list[2]),
    )

    df = pl.read_parquet(path_rho)
    target_set = [i1, i2, i3]

    # Function to map column X based on inchi match
    def get_col_map(target_inchi, col_prefix):
        return (
            pl.when(pl.col("inchi1") == target_inchi)
            .then(pl.col(f"{col_prefix}1"))
            .otherwise(
                pl.when(pl.col("inchi2") == target_inchi)
                .then(pl.col(f"{col_prefix}2"))
                .otherwise(pl.col(f"{col_prefix}3"))
            )
        )

    # Tolerance
    tol_x = 0.01

    filtered = (
        df.filter(
            pl.col("inchi1").is_in(target_set)
            & pl.col("inchi2").is_in(target_set)
            & pl.col("inchi3").is_in(target_set)
        )
        .with_columns(
            [
                get_col_map(i1, "mole_fraction_c").alias("x_m1"),
                get_col_map(i2, "mole_fraction_c").alias("x_m2"),
                get_col_map(i3, "mole_fraction_c").alias("x_m3"),
                get_col_map(i1, "molweight").alias("mw_m1"),
                get_col_map(i2, "molweight").alias("mw_m2"),
                get_col_map(i3, "molweight").alias("mw_m3"),
            ]
        )
        .filter(
            (pl.col("P_kPa") == pressure)
            & (pl.col("x_m1").is_between(x1 - tol_x, x1 + tol_x))
            & (pl.col("x_m2").is_between(x2 - tol_x, x2 + tol_x))
        )
    )

    if filtered.height == 0:
        return None

    # molar density = mass_rho * 1000 / avg_mw
    return (
        filtered.select(
            pl.col("T_K"),
            pl.col("rho")
            * 1000.0
            / (
                pl.col("x_m1") * pl.col("mw_m1")
                + pl.col("x_m2") * pl.col("mw_m2")
                + pl.col("x_m3") * pl.col("mw_m3")
            ),
        )
        .sort("T_K")
        .to_numpy()
    )


def retrieve_lle_ternary_data(smiles_list: list, pressure: float, temperature: float):
    "retrieve ternary lle data (tie lines/binodal points)"
    if len(smiles_list) != 3:
        return None

    path_lle = osp.join(application_path, "_data", "lle_ternary.parquet")
    if not osp.exists(path_lle):
        return None

    i1, i2, i3 = (
        smilestoinchi(smiles_list[0]),
        smilestoinchi(smiles_list[1]),
        smilestoinchi(smiles_list[2]),
    )
    target_set = [i1, i2, i3]

    df = pl.read_parquet(path_lle)

    # Function to map column X based on inchi match
    def get_col_map(target_inchi, col_prefix):
        return (
            pl.when(pl.col("inchi1") == target_inchi)
            .then(pl.col(f"{col_prefix}1"))
            .otherwise(
                pl.when(pl.col("inchi2") == target_inchi)
                .then(pl.col(f"{col_prefix}2"))
                .otherwise(pl.col(f"{col_prefix}3"))
            )
        )

    tol = 0.01
    return (
        df.filter(
            pl.col("inchi1").is_in(target_set)
            & pl.col("inchi2").is_in(target_set)
            & pl.col("inchi3").is_in(target_set)
        )
        .filter(
            (pl.col("P_kPa").is_between(pressure - tol, pressure + tol))
            & (pl.col("T_K").is_between(temperature - tol, temperature + tol))
        )
        .with_columns(
            [
                get_col_map(i1, "mole_fraction_c").alias("x_m1"),
                get_col_map(i2, "mole_fraction_c").alias("x_m2"),
            ]
        )
        .select("x_m1", "x_m2")
        .to_numpy()
    )
