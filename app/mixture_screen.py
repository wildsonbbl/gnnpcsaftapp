"Mixture Screen"

from copy import copy

from gnnepcsaft.pcsaft.pcsaft_feos import critical_points_feos
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters
from gnnepcsaft_mcp_server.utils_data import (
    _retrieve_available_data_binary,
    _retrieve_available_data_ternary,
    default_mixture_output_args,
)
from kivy.clock import mainthread
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.screenmanager import Screen

from app.input_requests import BinaryFillRequest, TernaryFillRequest
from app.layout_base import BaseInputLayout
from app.mixture_ui_builder import MixtureUIBuilder
from app.plot_requests import PlotRequest, TernaryPlotRequest
from app.plots import mixture_binary, mixture_common, mixture_ternary
from app.ui_helpers import (
    add_dropdown_button,
    fill_pressure_temperature,
)
from app.utils import (
    generate_plot,
    generate_ternary_plot,
    get_smiles_from_input,
    run_with_loading,
    show_warning_popup,
)
from app.validators import validate_fractions


class MixtureScreen(Screen):
    "Mixture screen"


# pylint: disable=E1133
class MixtureLayout(BaseInputLayout):
    "Mixture Layout"

    smiles_or_inchi_input = ObjectProperty(None)
    fractions_input = ObjectProperty(None)
    kij_input = ObjectProperty(None)

    @mainthread
    def _generate_plot(self, request: PlotRequest):
        try:
            generate_plot(request)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @mainthread
    def _generate_ternary_plot(self, request: TernaryPlotRequest):
        try:
            generate_ternary_plot(request)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def _get_smiles(self):
        raw_smiles = self.smiles_or_inchi_input.text.split(" ")
        smiles_list = [
            get_smiles_from_input(s.strip()) for s in raw_smiles if s.strip()
        ]
        if not smiles_list or len(smiles_list) < 2:
            raise ValueError("Please provide at least two components")
        return smiles_list

    def _get_fractions(self, n):
        raw_fracs = self.fractions_input.text.split(" ")
        try:
            fractions = [float(f.strip()) for f in raw_fracs if f.strip()]
        except ValueError as e:
            raise ValueError(
                "Fractions must be numeric values separated by empty space"
            ) from e

        if len(fractions) != n:
            raise ValueError("Number of components and fractions must match")
        validate_fractions(fractions)
        return fractions

    def _get_kij(self, n):
        kij_txt = self.kij_input.text.strip()
        kij_matrix = [[0.0] * n for _ in range(n)]
        self._set_kij_values(kij_txt, n, kij_matrix)
        return kij_matrix

    def _set_kij_values(self, kij_txt, n, kij_matrix):
        if kij_txt:
            parts = [p.strip() for p in kij_txt.split(" ") if p.strip()]
            try:
                k_vals = [float(x) for x in parts]
            except ValueError as e:
                raise ValueError(
                    "Kij values must be numeric values separated by empty space"
                ) from e
            if len(parts) == 1:
                for i in range(n):
                    for j in range(n):
                        if i != j:
                            kij_matrix[i][j] = k_vals[0]
            else:
                # List of values (k12; k13; k23...)
                expected = (n * (n - 1)) // 2
                if len(parts) != expected:
                    raise ValueError(
                        f"Expected {expected} kij values (k12 k13 ...), got {len(parts)}"
                    )

                k_idx = 0
                for i in range(n):
                    for j in range(i + 1, n):
                        kij_matrix[i][j] = k_vals[k_idx]
                        kij_matrix[j][i] = k_vals[k_idx]
                        k_idx += 1

    def get_kij_tmin_pressure(self, n, require_pressure=True):
        """Fetch kij matrix, min temperature, and optionally pressure from layout.

        Parameters
        - n: number of components
        - require_pressure: if True, will read and return pressure; otherwise returns None
        """
        kij_matrix = self._get_kij(n)
        t_min, _ = self._get_temperatures(require_max=False)
        p_val = None
        if require_pressure:
            p_val = self._get_pressure()
        return kij_matrix, t_min, p_val

    def _get_available_data(self, smiles_list):
        output_args = default_mixture_output_args()

        if len(smiles_list) == 2:
            try:
                output_args.update(_retrieve_available_data_binary(smiles_list))
            except (ValueError, RuntimeError) as e:
                show_warning_popup(
                    "Exp. Data Notice",
                    f"Could not load binary experimental data:\n{str(e)}",
                )
        elif len(smiles_list) == 3:
            try:
                output_args.update(_retrieve_available_data_ternary(smiles_list))
            except (ValueError, RuntimeError) as e:
                show_warning_popup(
                    "Exp. Data Notice",
                    f"Could not load ternary experimental data:\n{str(e)}",
                )

        return output_args

    def _add_dropdown(self, title, rows, make_button, width_ratio=0.4):
        if rows is None or len(rows) == 0:
            return

        dropdown = DropDown()
        self._dropdown_cache.append(dropdown)
        dropdown_btns = [make_button(row, dropdown) for row in rows]
        for btn in dropdown_btns:
            dropdown.add_widget(btn)

        add_dropdown_button(self, title, dropdown, width_ratio=width_ratio)

    def _make_binary_button(self, dropdown, text, fill_action):
        btn = Button(
            text=text,
            size_hint_y=None,
            height=44,
        )
        btn.bind(  # type: ignore pylint: disable=no-member
            on_release=lambda btn: (fill_action(), dropdown.dismiss())
        )
        return btn

    def _make_ternary_button(self, dropdown, text, fill_action):
        return self._make_binary_button(dropdown, text, fill_action)

    @mainthread
    def _fill_inputs_binary(self, request: BinaryFillRequest):
        """Helper to populate inputs with clicked values."""
        fill_pressure_temperature(
            self,
            pressure=request.pressure,
            t_min=request.t_min,
            t_max=request.t_max,
        )
        if request.x1 is not None:
            self.fractions_input.text = f"{request.x1:.4f} {1.0 - request.x1:.4f}"

        if request.kij is not None:
            self.kij_input.text = str(request.kij)

    def _fill_inputs_ternary(self, request: TernaryFillRequest):
        """Helper to populate inputs with clicked values for ternary."""
        fill_pressure_temperature(
            self,
            pressure=request.pressure,
            t_min=request.t_min,
            t_max=request.t_max,
        )
        if request.x1 is not None and request.x2 is not None:
            x3 = max(0.0, 1.0 - request.x1 - request.x2)
            self.fractions_input.text = f"{request.x1:.4f} {request.x2:.4f} {x3:.4f}"

    @run_with_loading
    def on_submit(self):
        "handle submit button for mixture parameters"

        @mainthread
        def clear_widgets():
            self.predicted_parameters.clear_widgets()
            self._dropdown_cache = []

        clear_widgets()

        try:
            smiles_list = self._get_smiles()
            output_args = self._get_available_data(smiles_list)

            preds = []
            for smile in smiles_list:
                pred = predict_pcsaft_parameters(smile)
                pred += critical_points_feos(copy(pred))
                preds.append((smile, pred))
            output_args["preds"] = preds

            @mainthread
            def build_ui():
                builder = MixtureUIBuilder(self, smiles_list, output_args)
                builder.build()

            build_ui()

        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_density(self):
        "plot mixture density vs temperature"
        try:
            mixture_common.plot_density(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_vp(self):
        "plot mixture vapor pressure vs temperature"
        try:
            mixture_common.plot_vp(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_binary_vle_txy(self):
        "plot binary VLE T-x-y"
        try:
            mixture_binary.plot_vle_txy(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_binary_vle_pxy(self):
        "plot binary VLE P-x-y"
        try:
            mixture_binary.plot_vle_pxy(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_binary_vle_xy(self):
        "plot binary VLE x-y"
        try:
            mixture_binary.plot_vle_xy(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_binary_lle_txx(self):
        "plot binary VLE/LLE T-x-y or T-x-x"
        try:
            mixture_binary.plot_lle_txx(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_binary_vlle_txx(self):
        "plot binary VLLE"
        try:
            mixture_binary.plot_vlle_txx(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_ternary_vle_lle(self):
        "plot ternary VLE/LLE"
        try:
            mixture_ternary.plot_vle_lle(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_ternary_vle_tx_fixed(self):
        "plot ternary VLE P-x at fixed T and fixed solvent ratio"
        try:
            mixture_ternary.plot_vle_tx_fixed(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_estimate_kij(self):
        "estimate binary kij"
        try:
            mixture_binary.estimate_kij(self)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)
