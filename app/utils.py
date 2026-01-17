"General utility"

import re

import matplotlib.pyplot as plt
from kivy.app import App

from gnnepcsaft_mcp_server.utils import inchitosmiles, smilestoinchi

available_params = [
    "Segment number",
    "Segment diameter (Å)",
    "Dispersion energy (K)",
    "Association volume",
    "Association energy (K)",
    "Dipole moment (D)*",
    "Nº association site A",
    "Nº association site B",
    "Molecular weight (g/mol)",
    "Critical temperature (K)",
    "Critical pressure (Pa)",
    "Critical density (mol/m³)",
]


MARKERS = ("o", "v", "s", "<", ">", "*", "^", "p", "P", "D")


def get_smiles_from_input(input_text):
    "check if input is SMILES or InChI and convert to SMILES if needed"
    inchi_check = re.search("^InChI=", input_text)
    if inchi_check:
        smiles = inchitosmiles(input_text)
    else:
        smilestoinchi(input_text)
        smiles = input_text
    return smiles


def generate_plot(
    x_datas, y_datas, title, x_label, y_label, legends=None, exp_data=None
):
    """Helper to generate plot and switch screen"""

    if not x_datas or not y_datas:
        return

    # Optimized for mobile (390px width)
    plt.figure(figsize=(3.5, 4.5), dpi=100)
    plt.clf()  # Clear previous figure

    # Reduce font sizes for mobile
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)

    if isinstance(y_datas[0], list):
        # Multiple lines (e.g., Bubble/Dew points)
        for i, y_data in enumerate(y_datas):
            label = legends[i] if legends and i < len(legends) else None
            plt.plot(
                x_datas,
                y_data,
                marker=MARKERS[i],
                linestyle="-",
                markersize=4,
                label=label,
            )
        if legends:
            plt.legend(fontsize=8)
    elif isinstance(x_datas[0], list):
        # Multiple lines (e.g., Phase diagram points)
        for i, x_data in enumerate(x_datas):
            label = legends[i] if legends and i < len(legends) else None
            plt.plot(
                x_data,
                y_datas,
                marker=MARKERS[i],
                linestyle="-",
                markersize=4,
                label=label,
            )
        if legends:
            plt.legend(fontsize=8)
    else:
        # Single line
        plt.plot(x_datas, y_datas, marker="o", linestyle="-", markersize=4)

    # Plot Experimental Data if available
    if exp_data:
        # Check if exp_data is a list of datasets (multiple series)
        # Structure: [(x1, y1, 'label1'), (x2, y2, 'label2')]
        if (
            isinstance(exp_data, list)
            and len(exp_data) > 0
            and isinstance(exp_data[0], (list, tuple))
            and len(exp_data[0]) == 3
            and not isinstance(exp_data[0][0], (int, float))
        ):
            # Defined colors/markers for multiple exp sets if needed, or cycle
            exp_markers = ["x", "+", "1", "2"]
            for idx, dataset in enumerate(exp_data):
                ex, ey, el = dataset
                marker = exp_markers[idx % len(exp_markers)]
                plt.scatter(
                    ex,
                    ey,
                    color="black",
                    marker=marker,
                    s=30,
                    linewidths=1,
                    label=el,
                    zorder=3,
                )
        else:
            # Single dataset case
            exp_x, exp_y, exp_lbl = exp_data
            plt.scatter(
                exp_x,
                exp_y,
                color="black",
                marker="x",
                s=30,
                linewidths=1,
                label=exp_lbl,
                zorder=3,
            )
        plt.legend(fontsize=8)

    plt.title(title, fontsize=10, pad=10)
    plt.xlabel(x_label, fontsize=9)
    plt.ylabel(y_label, fontsize=9)
    plt.grid(True, linestyle="--", alpha=0.6)

    # Increase padding to ensure labels are not cut off
    plt.tight_layout(pad=2.5)

    # Interactive Plot Logic
    app = App.get_running_app()
    plot_screen = app.root.get_screen("plot_screen")  # type: ignore
    plot_layout = plot_screen.ids.plot_layout

    mat_plot_figure = plot_layout.ids.mat_plot_figure
    mat_plot_figure.figure = plt.gcf()

    plot_layout.previous_screen = app.root.current  # type: ignore

    app.root.transition.direction = "left"  # type: ignore
    app.root.current = "plot_screen"  # type: ignore


def generate_ternary_plot(a, b, title, a_label, b_label):
    "Helper to generate right triangle ternary plot and switch screen"

    # Optimized for mobile (390px width)
    fig = plt.figure(figsize=(3.5, 4.5), dpi=100)
    fig.clf()  # Clear previous figure

    # Reduce font sizes for mobile
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)

    # Right Triangle Frame
    plt.plot([0, 1, 0, 0], [0, 0, 1, 0], "k-", linewidth=1.5)

    # Plot Data
    if a and isinstance(a[0], list):
        for i, val in enumerate(a):
            plt.scatter(val, b[i])
    else:
        plt.scatter(a, b)

    plt.title(title, fontsize=10, pad=10)
    plt.xlabel(a_label, fontsize=9)
    plt.ylabel(b_label, fontsize=9)

    plt.grid(True, linestyle="--", alpha=0.6)
    plt.xlim(-0.1, 1.1)
    plt.ylim(-0.1, 1.1)
    plt.gca().set_aspect("equal", adjustable="box")

    # Increase padding to ensure labels are not cut off
    plt.tight_layout(pad=2.5)

    # Interactive Plot Logic
    app = App.get_running_app()
    plot_screen = app.root.get_screen("plot_screen")  # type: ignore
    plot_layout = plot_screen.ids.plot_layout

    mat_plot_figure = plot_layout.ids.mat_plot_figure
    mat_plot_figure.figure = fig.figure

    plot_layout.previous_screen = app.root.current  # type: ignore

    app.root.transition.direction = "left"  # type: ignore
    app.root.current = "plot_screen"  # type: ignore
