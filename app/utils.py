"General utility"

import functools
import re
import threading
import time
from dataclasses import dataclass

import matplotlib.pyplot as plt
from gnnepcsaft.data.ogb_utils import smiles2graph
from gnnepcsaft.data.rdkit_util import assoc_number, inchitosmiles, smilestoinchi
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.logger import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView

from app.plot_requests import PlotRequest, TernaryPlotRequest

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


@dataclass
class _LoadingUi:
    popup: Popup
    message_label: Label
    progress: ProgressBar
    elapsed_label: Label
    cancel_button: Button


@dataclass
class _LoadingContext:
    buttons_state: list
    cancel_event: threading.Event
    ui: _LoadingUi
    update_event: object
    start_time: float
    dismissed: bool = False


def _collect_buttons(root, buttons_state):
    stack = [root]
    while stack:
        widget = stack.pop()
        if isinstance(widget, Button):
            buttons_state.append((widget, widget.disabled))
            widget.disabled = True
        if hasattr(widget, "children"):
            stack.extend(widget.children)


@mainthread
def _disable_buttons(buttons_state):
    app = App.get_running_app()
    root = getattr(app, "root", None)
    if root is not None:
        _collect_buttons(root, buttons_state)


def _restore_buttons(buttons_state):
    for widget, prev_disabled in buttons_state:
        widget.disabled = prev_disabled
    buttons_state.clear()


def _build_loading_popup():
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
    # content.add_widget(cancel_button)

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
    return _LoadingUi(
        popup=popup,
        message_label=message_label,
        progress=progress,
        elapsed_label=elapsed_label,
        cancel_button=cancel_button,
    )


def _start_progress(elapsed_label, progress, start_time):
    def update_ui(_dt):
        elapsed = time.perf_counter() - start_time
        elapsed_label.text = f"Elapsed: {elapsed:.1f}s"
        progress.value = (progress.value + 5) % progress.max

    return Clock.schedule_interval(update_ui, 0.1)


@mainthread
def _safe_dismiss(context: _LoadingContext):
    if context.dismissed:
        return
    context.dismissed = True
    context.update_event.cancel()  # type: ignore
    context.ui.popup.dismiss()
    _restore_buttons(context.buttons_state)


def _create_loading_context():
    buttons_state = []
    ui = _build_loading_popup()
    start_time = time.perf_counter()
    update_event = _start_progress(ui.elapsed_label, ui.progress, start_time)
    context = _LoadingContext(
        buttons_state=buttons_state,
        cancel_event=threading.Event(),
        ui=ui,
        update_event=update_event,
        start_time=start_time,
    )
    return context


def run_with_loading(func):
    """
    Decorator to run a function in a background thread while showing a loading popup.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        context = _create_loading_context()

        def on_cancel(_btn):
            context.cancel_event.set()
            context.ui.message_label.text = "Cancel requested..."
            context.ui.cancel_button.disabled = True
            _safe_dismiss(context)
            Logger.debug("Operation cancelled successfully")

        context.ui.cancel_button.bind(  # type: ignore pylint: disable=no-member
            on_release=on_cancel
        )

        _disable_buttons(context.buttons_state)
        context.ui.popup.open()

        def background_task():
            try:
                func(self, *args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                exception_type = type(exc).__name__
                if exception_type == "PanicException":
                    err = ValueError(
                        "PC-SAFT calculation failed (Rust panic). "
                        "Limit values (e.g. check Critical Points)."
                    )
                    show_error_popup(err)
                else:
                    Logger.exception("Unexpected Error: %s", exception_type)
                    show_error_popup(ValueError(f"Calculation failed: {str(exc)}"))
            _safe_dismiss(context)

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
            if "temperature" in lowered:
                suggestions.append(
                    "For binary LLE, min/max temperature are "
                    "used as range values for calculations",
                )
        elif "fraction" in lowered or "kij" in lowered:
            suggestions = [
                "Use space-separated numeric values",
                "Match number of components",
            ]
            if "fraction" in lowered:
                suggestions.append(
                    "For binary LLE, mole fractions are "
                    "used as starting value for calculations",
                )
        elif "pc-saft" in lowered and "failed" in lowered:
            suggestions = [
                "Adjust temperatures to be within meaningful values",
                "Reduce pressure if very high or increase if very low",
                "Adjust mole fractions to avoid extremes (0 or 1)",
            ]

    if suggestions:
        detail = "\n".join(["Suggestions:"] + [f"- {s}" for s in suggestions])
    else:
        detail = "Suggestions:\n- Check your input values"

    message = Label(
        text=f"{error_text}\n\n{detail}",
        halign="left",
        valign="top",
        color=(0, 0, 0, 1),
        size_hint=(1, None),
    )

    scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
    scroll.add_widget(message)

    def update_message_layout(_instance, _value=None):
        # Wrap text to the scrollview width so it does not overflow horizontally.
        content_width = max(scroll.width - 20, 1)
        message.text_size = (content_width, None)
        message.texture_update()
        message.height = message.texture_size[1]

    scroll.bind(size=update_message_layout)  # type: ignore pylint: disable=no-member
    message.bind(texture_size=lambda _w, size: setattr(message, "height", size[1]))  # type: ignore pylint: disable=no-member
    Clock.schedule_once(update_message_layout, 0)

    error_popup = Popup(
        title="Input Error",
        content=scroll,
        title_color=(0, 0, 0, 1),
        background="",
        background_color=(1, 1, 1, 1),
        size_hint=(None, None),
        size=(420, 260),
        auto_dismiss=True,
    )
    error_popup.open()


@mainthread
def show_warning_popup(title, message_text):
    """Shows a UI warning popup without aborting flow."""
    message = Label(
        text=message_text,
        halign="left",
        valign="top",
        color=(0, 0, 0, 1),
        size_hint=(1, None),
    )
    scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
    scroll.add_widget(message)

    def update_message_layout(_instance, _value=None):
        content_width = max(scroll.width - 20, 1)
        message.text_size = (content_width, None)
        message.texture_update()
        message.height = message.texture_size[1]

    scroll.bind(size=update_message_layout)  # type: ignore pylint: disable=no-member
    message.bind(texture_size=lambda _w, size: setattr(message, "height", size[1]))  # type: ignore pylint: disable=no-member
    Clock.schedule_once(update_message_layout, 0)

    popup = Popup(
        title=title,
        content=scroll,
        title_color=(0, 0, 0, 1),
        background="",
        background_color=(1, 0.9, 0.6, 1),
        size_hint=(None, None),
        size=(360, 200),
        auto_dismiss=True,
    )
    popup.open()


def get_smiles_from_input(input_text):
    "check if input is SMILES or InChI and convert to SMILES if needed"
    inchi_check = re.search("^InChI=", input_text)
    if inchi_check:
        smiles = inchitosmiles(input_text, False, False)
        inchi = smilestoinchi(smiles, False, False)
    else:
        inchi = smilestoinchi(input_text, False, False)
        smiles = inchitosmiles(inchi, False, False)
    smiles2graph(smiles)
    assoc_number(inchi)
    return smiles


def generate_plot(request: PlotRequest):
    """Helper to generate plot and switch screen."""

    if not request.x_data or not request.y_data:
        return

    plt.close("all")
    plt.figure(figsize=(5.5, 4.5), dpi=100)
    plt.clf()  # Clear previous figure

    # Reduce font sizes for mobile
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)

    if (
        isinstance(request.y_data[0], list)
        and isinstance(request.x_data[0], list)
        and request.legends is not None
    ):
        i = 0
        for y_data, x_data, legend in zip(
            request.y_data, request.x_data, request.legends
        ):
            plt.plot(
                x_data,
                y_data,
                marker=MARKERS[i % len(MARKERS)],
                linestyle="-",
                markersize=4,
                label=legend,
            )
            if request.legends:
                plt.legend(fontsize=8)
            i += 1
    elif isinstance(request.y_data[0], list):
        # Multiple lines (e.g., Bubble/Dew points)
        for i, y_data in enumerate(request.y_data):
            label = (
                request.legends[i]
                if request.legends and i < len(request.legends)
                else None
            )
            plt.plot(
                request.x_data,
                y_data,
                marker=MARKERS[i % len(MARKERS)],
                linestyle="-",
                markersize=4,
                label=label,
            )
        if request.legends:
            plt.legend(fontsize=8)
    elif isinstance(request.x_data[0], list):
        # Multiple lines (e.g., Phase diagram points)
        for i, x_data in enumerate(request.x_data):
            label = (
                request.legends[i]
                if request.legends and i < len(request.legends)
                else None
            )
            plt.plot(
                x_data,
                request.y_data,
                marker=MARKERS[i % len(MARKERS)],
                linestyle="-",
                markersize=4,
                label=label,
            )
        if request.legends:
            plt.legend(fontsize=8)
    else:
        # Single line
        plt.plot(
            request.x_data,
            request.y_data,
            marker="o",
            linestyle="-",
            markersize=4,
        )

    # Plot Experimental Data if available
    if request.exp_data:
        _plot_experimental_data(request.exp_data)

    plt.title(request.title, fontsize=10, pad=10)
    plt.xlabel(request.x_label, fontsize=9)
    plt.ylabel(request.y_label, fontsize=9)
    plt.grid(True, linestyle="--", alpha=0.6)

    # Increase padding to ensure labels are not cut off
    plt.tight_layout(pad=2.5)

    plt.show(block=False)
    Clock.schedule_interval(_pump_matplotlib, 1 / 60)


def generate_ternary_plot(request: TernaryPlotRequest):
    """Helper to generate right triangle ternary plot and switch screen."""

    plt.close("all")
    fig = plt.figure(figsize=(5.5, 4.5), dpi=100)
    fig.clf()  # Clear previous figure

    # Reduce font sizes for mobile
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)

    # Right Triangle Frame
    plt.plot([0, 1, 0, 0], [0, 0, 1, 0], "k-", linewidth=1.5)

    # Plot Data
    if request.a and isinstance(request.a[0], list):
        for a_val, b_val, l_val in zip(request.a, request.b, request.legends or []):
            plt.scatter(a_val, b_val, label=l_val)
    else:
        plt.scatter(request.a, request.b)

    # Plot Experimental Data
    if request.exp_data:
        exp_a, exp_b, exp_label = request.exp_data
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

    if request.legends or request.exp_data:
        plt.legend(fontsize=8)

    plt.title(request.title, fontsize=10, pad=10)
    plt.xlabel(request.a_label, fontsize=9)
    plt.ylabel(request.b_label, fontsize=9)

    plt.grid(True, linestyle="--", alpha=0.6)
    plt.xlim(-0.1, 1.1)
    plt.ylim(-0.1, 1.1)
    plt.gca().set_aspect("equal", adjustable="box")

    # Increase padding to ensure labels are not cut off
    plt.tight_layout(pad=2.5)

    plt.show(block=False)
    Clock.schedule_interval(_pump_matplotlib, 1 / 60)


def _plot_experimental_data(exp_data):
    # Check if exp_data is a list of datasets (multiple series)
    # Structure: [(x1, y1, 'label1'), (x2, y2, 'label2')]
    if (
        isinstance(exp_data, list)
        and len(exp_data) > 0
        and isinstance(exp_data[0], (list, tuple))
        and len(exp_data[0]) == 3
        and not isinstance(exp_data[0][0], (int, float))
    ):
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


def _pump_matplotlib(_):
    "pump matplotlib to update figure"
    # Check if the figure window is still open to prevent errors
    if plt.fignum_exists(1):
        fig = plt.gcf()
        fig.canvas.draw_idle()  # Request a redraw
        fig.canvas.flush_events()  # Process mouse movements, sliders, zooms
        return True
    return False  # Stops the Kivy clock if the plot window is closed
