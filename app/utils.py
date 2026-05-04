"General utility"

import functools
import re
import threading
import time

import matplotlib.pyplot as plt
from gnnepcsaft_mcp_server.utils import inchitosmiles, smilestoinchi
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar

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


def run_with_loading(func):
    """
    Decorator to run a function in a background thread while showing a loading popup.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        buttons_state = []
        cancel_event = threading.Event()
        dismissed = False

        def collect_buttons(root):
            stack = [root]
            while stack:
                widget = stack.pop()
                if isinstance(widget, Button):
                    buttons_state.append((widget, widget.disabled))
                    widget.disabled = True
                if hasattr(widget, "children"):
                    stack.extend(widget.children)

        @mainthread
        def disable_buttons():
            app = App.get_running_app()
            root = getattr(app, "root", None)
            if root is not None:
                collect_buttons(root)

        @mainthread
        def restore_buttons():
            for widget, prev_disabled in buttons_state:
                widget.disabled = prev_disabled
            buttons_state.clear()

        # Create the popup only once on main thread
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        message_label = Label(
            text="Calculating...\nThis may take a while.",
            halign="center",
            color=(0, 0, 0, 1),
        )
        progress = ProgressBar(max=100, value=0)
        elapsed_label = Label(
            text="Elapsed: 0.0s",
            halign="center",
            color=(0, 0, 0, 1),
        )
        cancel_button = Button(
            text="Cancel",
            size_hint_y=None,
            height=36,
        )
        content.add_widget(message_label)
        content.add_widget(progress)
        content.add_widget(elapsed_label)
        content.add_widget(cancel_button)

        popup = Popup(
            title="Processing",
            content=content,
            title_color=(0, 0, 0, 1),
            background="",
            background_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(360, 280),
            auto_dismiss=False,
        )

        start_time = time.perf_counter()

        def update_ui(_dt):
            elapsed = time.perf_counter() - start_time
            elapsed_label.text = f"Elapsed: {elapsed:.1f}s"
            progress.value = (progress.value + 5) % progress.max

        @mainthread
        def safe_dismiss():
            nonlocal dismissed
            if dismissed:
                return
            dismissed = True
            update_event.cancel()
            popup.dismiss()
            restore_buttons()

        def on_cancel(_btn):
            cancel_event.set()
            message_label.text = "Cancel requested..."
            cancel_button.disabled = True
            safe_dismiss()

        cancel_button.bind(on_release=on_cancel)  # type: ignore pylint: disable=no-member

        disable_buttons()
        popup.open()
        update_event = Clock.schedule_interval(update_ui, 0.1)

        def background_task():

            func(self, *args, **kwargs)
            time.sleep(5)
            safe_dismiss()

        threading.Thread(target=background_task, daemon=True).start()

    return wrapper


@mainthread
def show_error_popup(err):
    """Show a detailed error popup with suggestions."""
    error_text = str(err)
    suggestions = []
    if isinstance(err, ValueError):
        lowered = error_text.lower()
        if "smiles" in lowered or "inchi" in lowered:
            suggestions = [
                "Verify the SMILES/InChI format",
                "Remove extra spaces or separators",
                "Try a simpler component first",
            ]
        elif "temperature" in lowered or "pressure" in lowered:
            suggestions = [
                "Enter numeric values only",
                "Check units (K, Pa)",
            ]
        elif "fraction" in lowered or "kij" in lowered:
            suggestions = [
                "Use space-separated numeric values",
                "Match number of components",
            ]

    if suggestions:
        detail = "\n".join(["Suggestions:"] + [f"- {s}" for s in suggestions])
    else:
        detail = "Suggestions:\n- Check your input values"

    error_popup = Popup(
        title="Input Error",
        content=Label(
            text=f"{error_text}\n\n{detail}",
            halign="left",
            color=(0, 0, 0, 1),
        ),
        title_color=(0, 0, 0, 1),
        background="",
        background_color=(1, 1, 1, 1),
        size_hint=(None, None),
        size=(420, 260),
        auto_dismiss=True,
    )
    error_popup.open()


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


def generate_ternary_plot(a, b, title, a_label, b_label, legends=None, exp_data=None):
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
        for a_val, b_val, l_val in zip(a, b, legends or []):
            plt.scatter(a_val, b_val, label=l_val)
    else:
        plt.scatter(a, b)

    # Plot Experimental Data
    if exp_data:
        exp_a, exp_b, exp_label = exp_data
        plt.scatter(
            exp_a,
            exp_b,
            color="black",
            marker="x",
            s=30,
            linewidths=1,
            label=exp_label,
            zorder=3,
        )

    if legends or exp_data:
        plt.legend(fontsize=8)

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
    mat_plot_figure.figure = fig

    plot_layout.previous_screen = app.root.current  # type: ignore

    app.root.transition.direction = "left"  # type: ignore
    app.root.current = "plot_screen"  # type: ignore
