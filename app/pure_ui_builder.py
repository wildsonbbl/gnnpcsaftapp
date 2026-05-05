"""UI builder for pure component results."""

from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from app.utils import available_params


# pylint: disable=w0212,r0903
class PureUIBuilder:
    """Builds the pure-component results UI for a PureLayout instance."""

    def __init__(self, layout, rho_data, vp_range, st_range, pred):
        self.layout = layout
        self.rho_data = rho_data
        self.vp_range = vp_range
        self.st_range = st_range
        self.pred = pred

    def build(self):
        """Render all UI sections into the layout container."""
        self.layout.predicted_parameters.clear_widgets()

        if self._has_exp_data():
            self._add_availability_header()

        self._render_surface_tension()
        self._render_vapor_pressure()
        self._render_density_dropdown()

        self.layout.predicted_parameters.add_widget(Label(size_hint_y=None, height=20))
        self._render_title()
        self._render_param_table()
        self._render_footer()

    def _render_surface_tension(self):
        if self.st_range[0] is None:
            return

        dropdown = DropDown()
        self._cache_dropdown(dropdown)
        btn = Button(
            text=f"ST data ({int(self.st_range[2])} points, T is variable)",
            size_hint_y=None,
            height=44,
        )
        btn.bind(on_release=lambda btn: dropdown.dismiss())  # type: ignore pylint: disable=no-member
        dropdown.add_widget(btn)

        self._add_dropdown_button("Select Surface Tension Data", dropdown)

    def _render_vapor_pressure(self):
        if self.vp_range[0] is None:
            return

        dropdown = DropDown()
        self._cache_dropdown(dropdown)
        btn = Button(
            text=f"VP data ({int(self.vp_range[2])} points, T is variable)",
            size_hint_y=None,
            height=44,
        )
        btn.bind(on_release=lambda btn: dropdown.dismiss())  # type: ignore pylint: disable=no-member
        dropdown.add_widget(btn)

        self._add_dropdown_button("Select Vapor Pressure Data", dropdown)

    def _render_density_dropdown(self):
        if self.rho_data is None or len(self.rho_data) == 0:
            return

        dropdown = DropDown()
        self._cache_dropdown(dropdown)
        for row in self.rho_data:
            btn = Button(
                text=f"P={row[0]:.5g} kPa ({int(row[3])} points)",
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

        self._add_dropdown_button("Select Liquid Density Data", dropdown)

    def _render_title(self):
        title = Label(
            text="Estimated PC-SAFT parameters",
            size_hint_y=None,
            height=40,
            color="#198754",
            font_size=20,
            bold=True,
        )
        self.layout.predicted_parameters.add_widget(title)

    def _render_param_table(self):
        row_height = 30
        params_count = len(available_params)
        table_height = (params_count + 1) * row_height

        table = GridLayout(
            cols=2,
            size_hint_y=None,
            height=table_height,
            spacing=[10, 5],
        )

        table.add_widget(
            Label(text="Parameter name", bold=True, color="#212529", halign="left")
        )
        table.add_widget(
            Label(text="Parameter value", bold=True, color="#212529", halign="right")
        )

        for name, para in zip(available_params, self.pred):
            param_label = Label(text=str(name), color="#212529", halign="left")
            param_label.bind(size=param_label.setter("text_size"))  # type: ignore pylint: disable=no-member
            table.add_widget(param_label)

            param_label_value = Label(
                text=f"{para:.5g}", color="#212529", halign="right"
            )
            param_label_value.bind(size=param_label_value.setter("text_size"))  # type: ignore pylint: disable=no-member
            table.add_widget(param_label_value)

        self.layout.predicted_parameters.add_widget(table)

    def _render_footer(self):
        footer = Label(
            text="* Not estimated",
            size_hint_y=None,
            height=30,
            color="#6c757d",
            italic=True,
        )
        self.layout.predicted_parameters.add_widget(footer)

    def _add_availability_header(self):
        self.layout.predicted_parameters.add_widget(
            Label(
                text="Experimental Data Availability",
                size_hint_y=None,
                height=40,
                color="#0d6efd",
                font_size=20,
                bold=True,
            )
        )

    def _add_dropdown_button(self, title, dropdown, width_ratio=0.4):
        main_button = Button(
            text=title,
            size_hint_y=None,
            height=44,
            size_hint_x=width_ratio,
            pos_hint={"center_x": 0.5},
            background_color=(0.1, 0.5, 0.8, 1),
        )
        main_button.bind(on_release=dropdown.open)  # type: ignore pylint: disable=no-member
        self.layout.predicted_parameters.add_widget(main_button)

    def _cache_dropdown(self, dropdown):
        if hasattr(self.layout, "_dropdown_cache"):
            self.layout._dropdown_cache.append(dropdown)

    def _has_exp_data(self):
        return (self.rho_data is not None and len(self.rho_data) > 0) or (
            self.vp_range[0] is not None or self.st_range[0] is not None
        )
