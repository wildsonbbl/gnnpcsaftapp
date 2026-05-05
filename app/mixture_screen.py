"Mixture Screen"

from copy import copy

from gnnepcsaft.pcsaft.pcsaft_feos import critical_points_feos
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters
from kivy.clock import mainthread
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.mixture_ui_builder import MixtureUIBuilder
from app.plots import mixture_binary, mixture_common, mixture_ternary
from app.utils import (
    generate_plot,
    generate_ternary_plot,
    get_smiles_from_input,
    run_with_loading,
    show_error_popup,
)
from app.utils_data import (
    retrieve_available_data_binary,
    retrieve_available_data_ternary,
)


class MixtureScreen(Screen):
    "Mixture screen"


# pylint: disable=E1133
class MixtureLayout(BoxLayout):
    "Mixture Layout"

    smiles_or_inchi_input = ObjectProperty(None)
    fractions_input = ObjectProperty(None)
    kij_input = ObjectProperty(None)
    temp_min = ObjectProperty(None)
    temp_max = ObjectProperty(None)
    pressure = ObjectProperty(None)
    predicted_parameters = ObjectProperty(None)
    _dropdown_cache = []

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

    @mainthread
    def _generate_plot(
        self, x_datas, y_datas, title, x_label, y_label, legends=None, exp_data=None
    ):
        try:
            generate_plot(x_datas, y_datas, title, x_label, y_label, legends, exp_data)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @mainthread
    def _generate_ternary_plot(
        self, a, b, title, a_label, b_label, legends=None, exp_data=None
    ):
        try:
            generate_ternary_plot(a, b, title, a_label, b_label, legends, exp_data)
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
        return fractions

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
            raise ValueError("Temperature values must be numeric") from e

    def _get_pressure(self):
        if not self.pressure.text:
            raise ValueError("Pressure required")
        try:
            return float(self.pressure.text)
        except ValueError as e:
            raise ValueError("Pressure must be a numeric value") from e

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

    def _get_available_data(self, smiles_list):
        output_args = {
            "rho_data": None,
            "bubble_data": None,
            "lle_data": None,
            "vle_data": None,
            "vle_pxy_data": None,
            "rho_data_t": None,
            "lle_data_t": None,
            "vle_data_t": None,
            "vle_tx_data_t": None,
            "preds": [],
        }

        if len(smiles_list) == 2:
            try:
                (
                    output_args["rho_data"],
                    output_args["bubble_data"],
                    output_args["lle_data"],
                    output_args["vle_data"],
                    output_args["vle_pxy_data"],
                ) = retrieve_available_data_binary(smiles_list)
            except (ValueError, RuntimeError):
                pass
        elif len(smiles_list) == 3:
            try:
                (
                    output_args["rho_data_t"],
                    output_args["lle_data_t"],
                    output_args["vle_data_t"],
                    output_args["vle_tx_data_t"],
                ) = retrieve_available_data_ternary(smiles_list)
            except (ValueError, RuntimeError):
                pass

        return output_args

    def _add_dropdown(self, title, rows, make_button, width_ratio=0.4):
        if rows is None or len(rows) == 0:
            return

        dropdown = DropDown()
        self._dropdown_cache.append(dropdown)
        dropdown_btns = [make_button(row, dropdown) for row in rows]
        for btn in dropdown_btns:
            dropdown.add_widget(btn)

        main_button = Button(
            text=title,
            size_hint_y=None,
            height=44,
            size_hint_x=width_ratio,
            pos_hint={"center_x": 0.5},
            background_color=(0.1, 0.5, 0.8, 1),
        )
        main_button.bind(on_release=dropdown.open)  # type: ignore pylint: disable=no-member
        self.predicted_parameters.add_widget(main_button)

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

    def _fill_inputs_binary(self, pressure=None, t_min=None, t_max=None, x1=None):
        "Helper to populate inputs with clicked values"
        if pressure is not None:
            self.pressure.text = str(pressure * 1000.0)  # kPa to Pa
        if t_min is not None:
            self.temp_min.text = str(t_min)
        if t_max is not None:
            self.temp_max.text = str(t_max)
        if x1 is not None:
            self.fractions_input.text = f"{x1:.2f} {1.0 - x1:.2f}"

    def _fill_inputs_ternary(
        self, pressure=None, t_min=None, t_max=None, x1=None, x2=None
    ):
        "Helper to populate inputs with clicked values for ternary"
        if pressure is not None:
            self.pressure.text = str(pressure * 1000.0)
        if t_min is not None:
            self.temp_min.text = str(t_min)
        if t_max is not None:
            self.temp_max.text = str(t_max)
        if x1 is not None and x2 is not None:
            x3 = max(0.0, 1.0 - x1 - x2)
            self.fractions_input.text = f"{x1:.2f} {x2:.2f} {x3:.2f}"

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

            for smile in smiles_list:
                pred = predict_pcsaft_parameters(smile)
                pred += critical_points_feos(copy(pred))
                output_args["preds"].append((smile, pred))

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
            smiles_list = self._get_smiles()
            mixture_common.plot_density(self, smiles_list)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    @run_with_loading
    def on_plot_vp(self):
        "plot mixture vapor pressure vs temperature"
        try:
            smiles_list = self._get_smiles()
            mixture_common.plot_vp(self, smiles_list)
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
        "plot binary LLE T-x-x"
        try:
            mixture_binary.plot_lle_txx(self)
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
