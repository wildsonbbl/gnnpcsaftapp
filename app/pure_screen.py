"Pure screen"

from copy import copy

from gnnepcsaft.epcsaft.epcsaft_feos import critical_points_feos
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from utils import available_params, generate_plot, get_smiles_from_input
from utils_pure import (
    pure_den,
    pure_h_lv,
    pure_phase_diagram,
    pure_surface_tension,
    pure_vp,
)

from gnnepcsaft_mcp_server.utils import predict_epcsaft_parameters


class PureScreen(Screen):
    "Pure component screen"


class PureLayout(BoxLayout):
    "Pure Layout"

    smiles_or_inchi_input = ObjectProperty(None)
    temp_min = ObjectProperty(None)
    temp_max = ObjectProperty(None)
    pressure = ObjectProperty(None)
    predicted_parameters = ObjectProperty(None)

    def _generate_plot(self, x_data, y_data, title, x_label, y_label, legends=None):
        """Helper to generate plot and switch screen"""
        try:
            generate_plot(x_data, y_data, title, x_label, y_label, legends)
        except (RuntimeError, AssertionError) as e:
            self._show_error_alert(e)

    def _get_common_inputs(self):
        smiles_input = self.smiles_or_inchi_input.text
        try:
            try:
                t_min = float(self.temp_min.text)
                t_max = float(self.temp_max.text)
            except ValueError as e:
                raise ValueError(
                    "Temperature min and max must be numeric values"
                ) from e
            smiles = get_smiles_from_input(smiles_input)
            return smiles, t_min, t_max
        except (ValueError, TypeError) as e:
            self._show_error_alert(e)
            return None, None, None

    def _show_error_alert(self, e):
        error_message = Label(
            text=f"Error: {str(e)}",
            size_hint_y=None,
            height=50,
        )
        error_message.font_size = 16
        error_message.color = "#dc3545"
        self.predicted_parameters.clear_widgets()
        self.predicted_parameters.add_widget(error_message)

    def on_plot_density(self):
        "plot density vs temperature"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            try:
                p_val = float(self.pressure.text)
            except ValueError as e:
                raise ValueError("Pressure must be a numeric value") from e
            temperatures, densities = pure_den(smiles, t_min, t_max, p_val)
            self._generate_plot(
                temperatures,
                densities,
                f"Density vs Temperature\n({smiles})",
                "Temperature (K)",
                "Density (mol/m³)",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_vp(self):
        "plot vapor pressure vs temperature"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            temperatures, vps = pure_vp(smiles, t_min, t_max)
            self._generate_plot(
                temperatures,
                vps,
                f"Vapor Pressure vs Temperature\n({smiles})",
                "Temperature (K)",
                "Pressure (Pa)",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_hlv(self):
        "plot enthalpy of vaporization vs temperature"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            temperatures, hlvs = pure_h_lv(smiles, t_min, t_max)
            self._generate_plot(
                temperatures,
                hlvs,
                f"Enthalpy of Vap. vs Temperature\n({smiles})",
                "Temperature (K)",
                r"$H_{vap}$ (kJ/mol)",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_surface_tension(self):
        "plot surface tension vs temperature"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            temperatures, st = pure_surface_tension(smiles, t_min)
            self._generate_plot(
                temperatures,
                st,
                f"Surface Tension vs Temperature\n({smiles})",
                "Temperature (K)",
                "Surface Tension (mN/m)",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_phase_diagram_t_rho(self):
        "plot phase diagram for temperature vs density"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            temperatures, _, rho_liq, rho_vap = pure_phase_diagram(smiles, t_min)
            self._generate_plot(
                [rho_liq, rho_vap],
                temperatures,
                f"Phase diagram - Temperature vs Density\n({smiles})",
                "Density (mol/m³)",
                "Temperature (K)",
                legends=["Liquid", "Vapor"],
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_phase_diagram_p_rho(self):
        "plot phase diagram for pressure vs density"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            _, pressures, rho_liq, rho_vap = pure_phase_diagram(smiles, t_min)
            self._generate_plot(
                [rho_liq, rho_vap],
                pressures,
                f"Phase diagram - Pressure vs Density\n({smiles})",
                "Density (mol/m³)",
                "Pressure (Pa)",
                legends=["Liquid", "Vapor"],
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_submit(self):
        "handle submit button for pure component parameters"
        smiles_or_inchi_input = self.smiles_or_inchi_input.text
        self.predicted_parameters.clear_widgets()

        try:
            smiles = get_smiles_from_input(smiles_or_inchi_input)
            pred = predict_epcsaft_parameters(smiles)
            pred += critical_points_feos(copy(pred))

            # Title
            title = Label(
                text="Estimated PC-SAFT parameters",
                size_hint_y=None,  # changed
                height=40,  # changed
                color="#198754",  # Bootstrap text-success
                font_size=20,
                bold=True,
            )
            self.predicted_parameters.add_widget(title)

            # Table container (Grid)
            # Calculate required height based on number of rows (header + data)
            row_height = 30
            params_count = len(available_params)
            table_height = (params_count + 1) * row_height

            table = GridLayout(
                cols=2,
                size_hint_y=None,
                height=table_height,
                spacing=[10, 5],
            )

            # Headers - Using dark gray for contrast on white
            table.add_widget(
                Label(text="Parameter name", bold=True, color="#212529", halign="left")
            )
            table.add_widget(
                Label(
                    text="Parameter value", bold=True, color="#212529", halign="right"
                )
            )

            # Rows
            for name, para in zip(available_params, pred):
                # Parameter Name
                param_label = Label(text=str(name), color="#212529", halign="left")
                param_label.bind(
                    size=param_label.setter("text_size")
                )  # Ensure text aligns within widget
                table.add_widget(param_label)

                # Parameter Value
                param_label_value = Label(
                    text=f"{para:.4f}", color="#212529", halign="right"
                )
                param_label_value.bind(size=param_label_value.setter("text_size"))
                table.add_widget(param_label_value)

            self.predicted_parameters.add_widget(table)

            # Footer
            footer = Label(
                text="* Not estimated",
                size_hint_y=None,
                height=30,
                color="#6c757d",
                italic=True,
            )
            self.predicted_parameters.add_widget(footer)

        except ValueError as e:
            self._show_error_alert(e)
