"Pure screen"

from copy import copy

from gnnepcsaft.pcsaft.pcsaft_feos import critical_points_feos
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters
from kivy.clock import mainthread
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.pure_ui_builder import PureUIBuilder
from app.utils import (
    generate_plot,
    get_smiles_from_input,
    run_with_loading,
    show_error_popup,
)
from app.utils_data import (
    retrieve_available_data_pure,
    retrieve_rho_pure_data,
    retrieve_st_pure_data,
    retrieve_vp_pure_data,
)
from app.utils_pure import (
    pure_den,
    pure_h_lv,
    pure_phase_diagram,
    pure_surface_tension,
    pure_vp,
)


class PureScreen(Screen):
    "Pure component screen"


class PureLayout(BoxLayout):
    "Pure Layout"

    smiles_or_inchi_input = ObjectProperty(None)
    temp_min = ObjectProperty(None)
    temp_max = ObjectProperty(None)
    pressure = ObjectProperty(None)
    predicted_parameters = ObjectProperty(None)
    _dropdown_cache = []

    @mainthread
    def _generate_plot(
        self, x_data, y_data, title, x_label, y_label, legends=None, exp_data=None
    ):
        """Helper to generate plot and switch screen"""
        try:
            generate_plot(x_data, y_data, title, x_label, y_label, legends, exp_data)
        except (RuntimeError, AssertionError) as e:
            self._show_error_alert(e)

    def _get_smiles(self):
        smiles_input = self.smiles_or_inchi_input.text
        if not smiles_input:
            raise ValueError("No component provided")
        return get_smiles_from_input(smiles_input)

    def _get_temperatures(self, require_max=True):
        if not self.temp_min.text:
            raise ValueError("Min temperature required")
        if require_max and not self.temp_max.text:
            raise ValueError("Max temperature required")
        try:
            t_min = float(self.temp_min.text)
            t_max = 0.0
            if require_max:
                t_max = float(self.temp_max.text)
            return t_min, t_max
        except ValueError as e:
            raise ValueError("Temperature inputs must be numeric values") from e

    def _get_pressure(self):
        if not self.pressure.text:
            raise ValueError("Pressure required")
        try:
            return float(self.pressure.text)
        except ValueError as e:
            raise ValueError("Pressure must be a numeric value") from e

    @mainthread
    def _show_error_alert(self, e):
        show_error_popup(e)
        error_message = Label(
            text=f"Error: {str(e)}",
            size_hint_y=None,
            height=50,
        )
        error_message.font_size = 16
        error_message.color = "#dc3545"
        self.predicted_parameters.clear_widgets()
        self.predicted_parameters.add_widget(error_message)

    def _fill_inputs(self, pressure=None, t_min=None, t_max=None):
        "Helper to populate inputs with clicked values"
        if pressure is not None:
            # Data is in kPa, Input expects Pa. Convert: * 1000
            self.pressure.text = str(pressure * 1000.0)
        if t_min is not None:
            self.temp_min.text = str(t_min)
        if t_max is not None:
            self.temp_max.text = str(t_max)

    @run_with_loading
    def on_plot_density(self):
        "plot density vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, t_max = self._get_temperatures(require_max=True)
            p_val = self._get_pressure()

            # Fetch experimental data (convert Pa to kPa for DB lookup)
            exp_data = None
            try:
                exp_array = retrieve_rho_pure_data(smiles, p_val / 1000.0)
                if exp_array is not None and len(exp_array) > 0:
                    exp_data = (exp_array[:, 0], exp_array[:, 1], "Exp. Data")
            except (ValueError, RuntimeError):
                pass  # Ignore exp data errors

            temperatures, densities = pure_den(smiles, t_min, t_max, p_val)
            self._generate_plot(
                temperatures,
                densities,
                f"Density vs Temperature\n({smiles})",
                "Temperature (K)",
                "Density (mol/m³)",
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_vp(self):
        "plot vapor pressure vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, t_max = self._get_temperatures(require_max=True)

            # Fetch experimental data
            exp_data = None
            try:
                exp_array = retrieve_vp_pure_data(smiles)
                if exp_array is not None and len(exp_array) > 0:
                    # Convert kPa to Pa for plotting
                    exp_data = (exp_array[:, 0], exp_array[:, 1] * 1000.0, "Exp. Data")
            except (ValueError, RuntimeError):
                pass

            temperatures, vps = pure_vp(smiles, t_min, t_max)
            self._generate_plot(
                temperatures,
                vps,
                f"Vapor Pressure vs Temperature\n({smiles})",
                "Temperature (K)",
                "Pressure (Pa)",
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_hlv(self):
        "plot enthalpy of vaporization vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, t_max = self._get_temperatures(require_max=True)

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

    @run_with_loading
    def on_plot_surface_tension(self):
        "plot surface tension vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, _ = self._get_temperatures(require_max=False)

            # Fetch experimental data
            exp_data = None
            try:
                exp_array = retrieve_st_pure_data(smiles)
                if exp_array is not None and len(exp_array) > 0:
                    # Convert N/m to mN/m for plotting
                    exp_data = (exp_array[:, 0], exp_array[:, 1] * 1e3, "Exp. Data")
            except (ValueError, RuntimeError):
                pass

            temperatures, st = pure_surface_tension(smiles, t_min)
            self._generate_plot(
                temperatures,
                st,
                f"Surface Tension vs Temperature\n({smiles})",
                "Temperature (K)",
                "Surface Tension (mN/m)",
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_phase_diagram_t_rho(self):
        "plot phase diagram for temperature vs density"
        try:
            smiles = self._get_smiles()
            t_min, _ = self._get_temperatures(require_max=False)

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

    @run_with_loading
    def on_plot_phase_diagram_p_rho(self):
        "plot phase diagram for pressure vs density"
        try:
            smiles = self._get_smiles()
            t_min, _ = self._get_temperatures(require_max=False)

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

    @run_with_loading
    def on_submit(self):
        "handle submit button for pure component parameters"
        smiles_or_inchi_input = self.smiles_or_inchi_input.text

        @mainthread
        def clear_widgets():
            self.predicted_parameters.clear_widgets()
            self._dropdown_cache = []

        clear_widgets()

        try:
            smiles = get_smiles_from_input(smiles_or_inchi_input)

            # Display Available Data
            rho_data = []
            vp_range = [None] * 5
            st_range = [None] * 5
            try:
                rho_data, vp_range, st_range = retrieve_available_data_pure(smiles)
            except (ValueError, RuntimeError):
                pass  # Fail silently if data retrieval errors, proceed to prediction

            pred = predict_pcsaft_parameters(smiles)
            pred += critical_points_feos(copy(pred))

            @mainthread
            def build_ui(rho_data, vp_range, st_range, pred):
                builder = PureUIBuilder(self, rho_data, vp_range, st_range, pred)
                builder.build()

            build_ui(rho_data, vp_range, st_range, pred)

        except (RuntimeError, ValueError) as e:
            self._show_error_alert(e)
