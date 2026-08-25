"Pure screen"

from copy import copy

from gnnepcsaft.pcsaft.pcsaft_feos import critical_points_feos
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters
from gnnepcsaft_mcp_server.utils_data import (
    _retrieve_available_data_pure,
    retrieve_rho_pure_data,
    retrieve_st_pure_data,
    retrieve_vp_pure_data,
)
from gnnepcsaft_mcp_server.utils_pure import (
    pure_den,
    pure_h_lv,
    pure_phase_diagram,
    pure_surface_tension,
    pure_vp,
)
from kivy.clock import mainthread
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.screenmanager import Screen

from app.layout_base import BaseInputLayout
from app.plot_requests import PlotRequest
from app.pure_ui_builder import PureUIBuilder, PureUIData
from app.utils import (
    generate_plot,
    get_smiles_from_input,
    run_with_loading,
    show_warning_popup,
)


class PureScreen(Screen):
    "Pure component screen"


class PureLayout(BaseInputLayout):
    "Pure Layout"

    smiles_or_inchi_input = ObjectProperty(None)

    @mainthread
    def _generate_plot(self, request: PlotRequest):
        """Helper to generate plot and switch screen"""
        try:
            generate_plot(request)
        except (RuntimeError, AssertionError) as e:
            self._show_error_alert(e)

    def _get_smiles(self):
        smiles_input = self.smiles_or_inchi_input.text
        if not smiles_input:
            raise ValueError("No component provided")
        return get_smiles_from_input(smiles_input)

    @run_with_loading
    def on_plot_density(self):
        "plot density vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, t_max = self._get_temperatures(require_max=True)
            p_val = self._get_pressure()
            npoints = self._get_npoints()

            # Fetch experimental data (convert Pa to kPa for DB lookup)
            exp_data = None
            try:
                exp_array = retrieve_rho_pure_data(smiles, p_val / 1000.0)
                if exp_array is not None and len(exp_array) > 0:
                    exp_data = (exp_array[:, 0], exp_array[:, 1], "Exp. Data")
            except (ValueError, RuntimeError) as e:
                show_warning_popup(
                    "Missing Exp. Data",
                    f"Experimental Density data not found:\n{str(e)}",
                )

            temperatures, densities = pure_den(smiles, t_min, t_max, p_val, npoints)
            self._generate_plot(
                PlotRequest(
                    x_data=temperatures,
                    y_data=densities,
                    title=f"Density vs Temperature\n({smiles})",
                    x_label="Temperature (K)",
                    y_label="Density (mol/m³)",
                    exp_data=exp_data,
                )
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_vp(self):
        "plot vapor pressure vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, t_max = self._get_temperatures(require_max=True)
            npoints = self._get_npoints()

            # Fetch experimental data
            exp_data = None
            try:
                exp_array = retrieve_vp_pure_data(smiles)
                if exp_array is not None and len(exp_array) > 0:
                    # Convert kPa to Pa for plotting
                    exp_data = (exp_array[:, 0], exp_array[:, 1] * 1000.0, "Exp. Data")
            except (ValueError, RuntimeError) as e:
                show_warning_popup(
                    "Missing Exp. Data",
                    f"Experimental Vapor Pressure data not found:\n{str(e)}",
                )

            temperatures, vps = pure_vp(smiles, t_min, t_max, npoints)
            self._generate_plot(
                PlotRequest(
                    x_data=temperatures,
                    y_data=vps,
                    title=f"Vapor Pressure vs Temperature\n({smiles})",
                    x_label="Temperature (K)",
                    y_label="Pressure (Pa)",
                    exp_data=exp_data,
                )
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_hlv(self):
        "plot enthalpy of vaporization vs temperature"
        try:
            smiles = self._get_smiles()
            t_min, t_max = self._get_temperatures(require_max=True)
            npoints = self._get_npoints()

            temperatures, hlvs = pure_h_lv(smiles, t_min, t_max, npoints)
            self._generate_plot(
                PlotRequest(
                    x_data=temperatures,
                    y_data=hlvs,
                    title=f"Enthalpy of Vap. vs Temperature\n({smiles})",
                    x_label="Temperature (K)",
                    y_label=r"$H_{vap}$ (kJ/mol)",
                )
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
            except (ValueError, RuntimeError) as e:
                show_warning_popup(
                    "Missing Exp. Data",
                    f"Experimental Surface Tension data not found:\n{str(e)}",
                )

            temperatures, st = pure_surface_tension(smiles, t_min)
            self._generate_plot(
                PlotRequest(
                    x_data=temperatures,
                    y_data=st,
                    title=f"Surface Tension vs Temperature\n({smiles})",
                    x_label="Temperature (K)",
                    y_label="Surface Tension (mN/m)",
                    exp_data=exp_data,
                )
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
                PlotRequest(
                    x_data=[rho_liq, rho_vap],
                    y_data=temperatures,
                    title=f"Phase diagram - Temperature vs Density\n({smiles})",
                    x_label="Density (mol/m³)",
                    y_label="Temperature (K)",
                    legends=["Liquid", "Vapor"],
                )
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
                PlotRequest(
                    x_data=[rho_liq, rho_vap],
                    y_data=pressures,
                    title=f"Phase diagram - Pressure vs Density\n({smiles})",
                    x_label="Density (mol/m³)",
                    y_label="Pressure (Pa)",
                    legends=["Liquid", "Vapor"],
                )
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

            available_data_pure = {"rho_range": None, "vp_range": 0, "st_range": 0}
            try:
                available_data_pure = _retrieve_available_data_pure(smiles)
            except (ValueError, RuntimeError) as e:
                show_warning_popup(
                    "Exp. Data Notice",
                    f"Could not load pure experimental data:\n{str(e)}",
                )

            pred = predict_pcsaft_parameters(smiles)
            pred += critical_points_feos(copy(pred))

            @mainthread
            def build_ui(rho_data, vp_range, st_range, pred):
                ui_data = PureUIData(
                    rho_data=rho_data,
                    vp_range=vp_range,
                    st_range=st_range,
                    pred=pred,
                )
                builder = PureUIBuilder(self, ui_data)
                builder.build()

            build_ui(
                available_data_pure["rho_range"],
                available_data_pure["vp_range"],
                available_data_pure["st_range"],
                pred,
            )

        except (RuntimeError, ValueError) as e:
            self._show_error_alert(e)
