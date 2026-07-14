"""UI builder for pure component results."""

from dataclasses import dataclass

from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label

from app.ui_helpers import (
    add_availability_header,
    add_dropdown_button,
    add_footer,
    add_section_title,
    build_param_table,
)
from app.utils import available_params


@dataclass
class PureUIData:
    """Payload for rendering pure-component UI results."""

    rho_data: list
    vp_range: int
    st_range: int
    pred: list


# pylint: disable=w0212,r0903
class PureUIBuilder:
    """Builds the pure-component results UI for a PureLayout instance."""

    def __init__(self, layout, data: PureUIData):
        self.layout = layout
        self.rho_data = data.rho_data
        self.vp_range = data.vp_range
        self.st_range = data.st_range
        self.pred = data.pred

    def build(self):
        """Render all UI sections into the layout container."""
        self.layout.predicted_parameters.clear_widgets()

        if self._has_exp_data():
            add_availability_header(self.layout)

        self._render_surface_tension()
        self._render_vapor_pressure()
        self._render_density_dropdown()

        self.layout.predicted_parameters.add_widget(Label(size_hint_y=None, height=20))
        self._render_title()
        self._render_param_table()
        self._render_footer()

    def _render_surface_tension(self):
        if self.st_range == 0:
            return

        dropdown = DropDown()
        self._cache_dropdown(dropdown)
        btn = Button(
            text=f"ST data ({int(self.st_range)} points)",
            size_hint_y=None,
            height=44,
        )
        btn.bind(on_release=lambda btn: dropdown.dismiss())  # type: ignore pylint: disable=no-member
        dropdown.add_widget(btn)

        add_dropdown_button(self.layout, "Select Surface Tension Data", dropdown)

    def _render_vapor_pressure(self):
        if self.vp_range == 0:
            return

        dropdown = DropDown()
        self._cache_dropdown(dropdown)
        btn = Button(
            text=f"VP data ({int(self.vp_range)} points)",
            size_hint_y=None,
            height=44,
        )
        btn.bind(on_release=lambda btn: dropdown.dismiss())  # type: ignore pylint: disable=no-member
        dropdown.add_widget(btn)

        add_dropdown_button(self.layout, "Select Vapor Pressure Data", dropdown)

    def _render_density_dropdown(self):
        if self.rho_data is None or len(self.rho_data) == 0:
            return

        dropdown = DropDown()
        self._cache_dropdown(dropdown)
        for row in self.rho_data:
            btn = Button(
                text=f"P={row[0]:.5g} kPa ({int(row[1])} points)",
                size_hint_y=None,
                height=44,
            )
            btn.bind(  # type: ignore pylint: disable=no-member
                on_release=lambda btn, r=row: (
                    self.layout._fill_inputs(pressure=r[0]),
                    dropdown.dismiss(),
                )
            )
            dropdown.add_widget(btn)

        add_dropdown_button(self.layout, "Select Liquid Density Data", dropdown)

    def _render_title(self):
        add_section_title(
            self.layout,
            "Estimated PC-SAFT parameters",
            color="#198754",
            font_size=20,
            height=40,
        )

    def _render_param_table(self):
        table = build_param_table(available_params, self.pred)
        self.layout.predicted_parameters.add_widget(table)

    def _render_footer(self):
        add_footer(self.layout)

    def _cache_dropdown(self, dropdown):
        if hasattr(self.layout, "_dropdown_cache"):
            self.layout._dropdown_cache.append(dropdown)

    def _has_exp_data(self):
        return (self.rho_data is not None and len(self.rho_data) > 0) or (
            self.vp_range > 0 or self.st_range > 0
        )
