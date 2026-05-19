"""Shared UI helper functions for screens and builders."""

from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label


def show_error_alert(layout, error, show_error_popup):
    """Render an error alert in the predicted-parameters panel."""
    show_error_popup(error)
    error_message = Label(
        text=f"Error: {str(error)}",
        size_hint_y=None,
        height=50,
    )
    error_message.font_size = 16
    error_message.color = "#dc3545"
    layout.predicted_parameters.clear_widgets()
    layout.predicted_parameters.add_widget(error_message)


def get_temperatures(layout, require_max=True):
    """Parse temperature inputs from the layout fields."""
    if not layout.temp_min.text:
        raise ValueError("Min temperature required")
    if require_max and not layout.temp_max.text:
        raise ValueError("Max temperature required")
    try:
        t_min = float(layout.temp_min.text)
        t_max = 0.0
        if require_max:
            t_max = float(layout.temp_max.text)
        return t_min, t_max
    except ValueError as exc:
        raise ValueError("Temperature values must be numeric") from exc


def get_pressure(layout):
    """Parse the pressure input from the layout fields."""
    if not layout.pressure.text:
        raise ValueError("Pressure required")
    try:
        return float(layout.pressure.text)
    except ValueError as exc:
        raise ValueError("Pressure must be a numeric value") from exc


def get_npoints(layout):
    """Parse the npoints input"""
    if layout.npoints.text:
        return int(layout.npoints.text)
    return 10


def fill_pressure_temperature(layout, pressure=None, t_min=None, t_max=None):
    """Populate pressure and temperature fields from selected values."""
    if pressure is not None:
        # Data is in kPa, input expects Pa.
        layout.pressure.text = str(pressure * 1000.0)
    if t_min is not None:
        layout.temp_min.text = str(t_min)
    if t_max is not None:
        layout.temp_max.text = str(t_max)


def add_dropdown_button(layout, title, dropdown, width_ratio=0.4):
    """Add a shared dropdown button to the layout container."""
    main_button = Button(
        text=title,
        size_hint_y=None,
        height=44,
        size_hint_x=width_ratio,
        pos_hint={"center_x": 0.5},
        background_color=(0.1, 0.5, 0.8, 1),
    )
    main_button.bind(on_release=dropdown.open)  # type: ignore pylint: disable=no-member
    layout.predicted_parameters.add_widget(main_button)


def build_param_table(param_names, param_values):
    """Build a parameter table GridLayout for provided values."""
    row_height = 30
    params_count = len(param_names)
    table_height = (params_count + 1) * row_height

    table = GridLayout(
        cols=2,
        size_hint_y=None,
        height=table_height,
        spacing=[10, 5],
    )

    table.add_widget(
        Label(
            text="Parameter name",
            bold=True,
            color="#212529",
            halign="left",
        )
    )
    table.add_widget(
        Label(
            text="Parameter value",
            bold=True,
            color="#212529",
            halign="right",
        )
    )

    for name, value in zip(param_names, param_values):
        param_label = Label(text=str(name), color="#212529", halign="left")
        param_label.bind(size=param_label.setter("text_size"))  # type: ignore pylint: disable=no-member
        table.add_widget(param_label)

        param_value_label = Label(text=f"{value:.5g}", color="#212529", halign="right")
        param_value_label.bind(size=param_value_label.setter("text_size"))  # type: ignore pylint: disable=no-member
        table.add_widget(param_value_label)

    return table


def add_footer(layout):
    """Append a standard footer to the layout container."""
    footer = Label(
        text="* Not estimated",
        size_hint_y=None,
        height=30,
        color="#6c757d",
        italic=True,
    )
    layout.predicted_parameters.add_widget(footer)


def add_section_title(layout, text, color, font_size=20, height=40):
    """Append a bold section title to the layout container."""
    layout.predicted_parameters.add_widget(
        Label(
            text=text,
            size_hint_y=None,
            height=height,
            color=color,
            font_size=font_size,
            bold=True,
        )
    )


def add_availability_header(layout):
    """Append the experimental data availability header."""
    add_section_title(
        layout,
        "Experimental Data Availability",
        color="#0d6efd",
        font_size=20,
        height=40,
    )
