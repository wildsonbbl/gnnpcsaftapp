"Mixture Screen"

from copy import copy

from gnnepcsaft.epcsaft.epcsaft_feos import critical_points_feos
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from utils import (
    available_params,
    generate_plot,
    generate_ternary_plot,
    get_smiles_from_input,
)
from utils_mix import mix_den, mix_lle, mix_ternary_lle, mix_vle, mix_vp

from gnnepcsaft_mcp_server.utils import predict_epcsaft_parameters


class MixtureScreen(Screen):
    "Mixture screen"


class MixtureLayout(BoxLayout):
    "Mixture Layout"

    smiles_or_inchi_input = ObjectProperty(None)
    fractions_input = ObjectProperty(None)
    kij_input = ObjectProperty(None)
    temp_min = ObjectProperty(None)
    temp_max = ObjectProperty(None)
    pressure = ObjectProperty(None)
    predicted_parameters = ObjectProperty(None)

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

    def _generate_plot(self, x_data, y_datas, title, x_label, y_label, legends=None):
        try:
            generate_plot(x_data, y_datas, title, x_label, y_label, legends)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def _generate_ternary_plot(self, a, b, title, a_label, b_label):
        try:
            generate_ternary_plot(a, b, title, a_label, b_label)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def _get_inputs(self):
        try:
            raw_smiles = self.smiles_or_inchi_input.text.split(";")
            smiles_list = [
                get_smiles_from_input(s.strip()) for s in raw_smiles if s.strip()
            ]

            raw_fracs = self.fractions_input.text.split(";")
            try:
                fractions = [float(f.strip()) for f in raw_fracs if f.strip()]
            except ValueError as e:
                raise ValueError(
                    "Fractions must be numeric values separated by semicolons"
                ) from e

            if len(smiles_list) != len(fractions):
                raise ValueError("Number of components and fractions must match")

            try:
                t_min = float(self.temp_min.text)
                t_max = float(self.temp_max.text)
            except ValueError as e:
                raise ValueError(
                    "Temperature min and max must be numeric values"
                ) from e

            kij_txt = self.kij_input.text.strip()
            n = len(smiles_list)
            kij_matrix = [[0.0] * n for _ in range(n)]

            self._set_kij_values(kij_txt, n, kij_matrix)

            return smiles_list, fractions, kij_matrix, t_min, t_max

        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)
            return None, None, None, None, None

    def _set_kij_values(self, kij_txt, n, kij_matrix):
        if kij_txt:
            parts = [p.strip() for p in kij_txt.split(";") if p.strip()]
            try:
                k_vals = [float(x) for x in parts]
            except ValueError as e:
                raise ValueError(
                    "Kij values must be numeric values separated by semicolons"
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
                        f"Expected {expected} Kij values (k12; k13...), got {len(parts)}"
                    )

                k_idx = 0
                for i in range(n):
                    for j in range(i + 1, n):
                        kij_matrix[i][j] = k_vals[k_idx]
                        kij_matrix[j][i] = k_vals[k_idx]
                        k_idx += 1

    def on_submit(self):
        "handle submit button for mixture parameters"
        self.predicted_parameters.clear_widgets()

        try:
            raw_smiles = self.smiles_or_inchi_input.text.split(";")
            smiles_list = [
                get_smiles_from_input(s.strip()) for s in raw_smiles if s.strip()
            ]

            if not smiles_list:
                return

            for smile in smiles_list:
                pred = predict_epcsaft_parameters(smile)
                pred += critical_points_feos(copy(pred))

                # Header for this component
                comp_header = Label(
                    text=f"Component: {smile}",
                    size_hint_y=None,
                    height=40,
                    color="#198754",
                    font_size=18,
                    bold=True,
                    halign="left",
                )
                comp_header.bind(size=comp_header.setter("text_size"))
                self.predicted_parameters.add_widget(comp_header)

                # Table
                row_height = 30
                params_count = len(available_params)
                table_height = (params_count + 1) * row_height

                table = GridLayout(
                    cols=2,
                    size_hint_y=None,
                    height=table_height,
                    spacing=[10, 5],
                )

                # Headers
                table.add_widget(
                    Label(
                        text="Parameter name", bold=True, color="#212529", halign="left"
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

                for name, para in zip(available_params, pred):
                    param_label = Label(text=str(name), color="#212529", halign="left")
                    param_label.bind(size=param_label.setter("text_size"))
                    table.add_widget(param_label)

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

        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_density(self):
        "plot mixture density vs temperature"
        smiles_list, fractions, kij_matrix, t_min, t_max = self._get_inputs()
        if not smiles_list or not fractions or not kij_matrix or not t_min or not t_max:
            return
        try:
            try:
                p_val = float(self.pressure.text)
            except ValueError as e:
                raise ValueError("Pressure must be a numeric value") from e
            temperatures, densities = mix_den(
                smiles_list, fractions, kij_matrix, t_min, t_max, p_val
            )
            self._generate_plot(
                temperatures,
                densities,
                "Mixture Density vs Temperature",
                "Temperature (K)",
                "Density (mol/m³)",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_vp(self):
        "plot mixture vapor pressure vs temperature"
        smiles_list, fractions, kij_matrix, t_min, t_max = self._get_inputs()
        if not smiles_list or not fractions or not kij_matrix or not t_min or not t_max:
            return
        try:
            temperatures, bubbles, dews = mix_vp(
                smiles_list, fractions, kij_matrix, t_min, t_max
            )
            self._generate_plot(
                temperatures,
                [bubbles, dews],
                "Mixture Phase Envelope (P-T)",
                "Temperature (K)",
                "Pressure (Pa)",
                legends=["Bubble Point", "Dew Point"],
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_binary_vle_txy(self):
        "plot binary VLE T-x-y"

        smiles_list, fractions, kij_matrix, t_min, t_max = self._get_inputs()
        if not smiles_list or not fractions or not kij_matrix or not t_min or not t_max:
            return

        try:
            if len(smiles_list) != 2:
                raise ValueError(
                    f"VLE for binary mixture, got {len(smiles_list)} components instead"
                )
            try:
                p_val = float(self.pressure.text)
            except ValueError as e:
                raise ValueError("Pressure must be a numeric value") from e
            output = mix_vle(smiles_list, kij_matrix, p_val)
            self._generate_plot(
                [output["x0"], output["y0"]],
                output["temperature"],
                f"VLE T-x-y for {smiles_list[0]} at {p_val} Pa",
                "x,y",
                "Temperature (K)",
                legends=["Liquid", "Vapor"],
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_binary_vle_xy(self):
        "plot binary VLE x-y"

        smiles_list, fractions, kij_matrix, t_min, t_max = self._get_inputs()
        if not smiles_list or not fractions or not kij_matrix or not t_min or not t_max:
            return

        try:
            if len(smiles_list) != 2:
                raise ValueError(
                    f"VLE for binary mixture, got {len(smiles_list)} components instead"
                )
            try:
                p_val = float(self.pressure.text)
            except ValueError as e:
                raise ValueError("Pressure must be a numeric value") from e
            output = mix_vle(smiles_list, kij_matrix, p_val)
            self._generate_plot(
                output["x0"],
                output["y0"],
                f"VLE x-y for {smiles_list[0]} at {p_val} Pa",
                "x",
                "y",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_binary_lle_txx(self):
        "plot binary LLE T-x-x"

        smiles_list, fractions, kij_matrix, t_min, t_max = self._get_inputs()
        if not smiles_list or not fractions or not kij_matrix or not t_min or not t_max:
            return

        try:
            if len(smiles_list) != 2:
                raise ValueError(
                    f"LLE for binary mixture, got {len(smiles_list)} components instead"
                )
            try:
                p_val = float(self.pressure.text)
            except ValueError as e:
                raise ValueError("Pressure must be a numeric value") from e
            output = mix_lle(smiles_list, fractions, kij_matrix, t_min, p_val)
            self._generate_plot(
                [output["x0"], output["y0"]],
                output["temperature"],
                f"LLE T-x-x for {smiles_list[0]} at {p_val} Pa",
                "x,x",
                "Temperature (K)",
                legends=["Phase 1", "Phase 2"],
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_ternary_lle(self):
        "plot ternary LLE"

        smiles_list, fractions, kij_matrix, t_min, t_max = self._get_inputs()
        if not smiles_list or not fractions or not kij_matrix or not t_min or not t_max:
            return

        try:
            if len(smiles_list) != 3:
                raise ValueError(
                    f"LLE for ternary mixture, got {len(smiles_list)} components instead"
                )
            try:
                p_val = float(self.pressure.text)
            except ValueError as e:
                raise ValueError("Pressure must be a numeric value") from e
            output = mix_ternary_lle(smiles_list, kij_matrix, t_min, p_val)

            self._generate_ternary_plot(
                [output["x1"], output["y1"]],
                [output["x2"], output["y2"]],
                title=f"LLE at {p_val} Pa, {t_min} K",
                a_label=smiles_list[1],
                b_label=smiles_list[2],
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)
