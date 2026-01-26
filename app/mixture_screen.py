"Mixture Screen"

from copy import copy

from gnnepcsaft.pcsaft.pcsaft_feos import critical_points_feos
from gnnepcsaft_mcp_server.utils import predict_pcsaft_parameters
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.properties import ObjectProperty  # pylint: disable=no-name-in-module
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from utils import (
    available_params,
    generate_plot,
    generate_ternary_plot,
    get_smiles_from_input,
)
from utils_data import (
    retrieve_available_data_binary,
    retrieve_available_data_ternary,
    retrieve_bubble_pressure_data,
    retrieve_lle_binary_data,
    retrieve_lle_ternary_data,
    retrieve_rho_binary_data,
    retrieve_rho_ternary_data,
    retrieve_vle_binary_data,
    retrieve_vle_ternary_data,
)
from utils_mix import mix_den, mix_lle, mix_ternary_lle, mix_vle, mix_vp


class MixtureScreen(Screen):
    "Mixture screen"


class ActionLabelCustom(ButtonBehavior, Label):  # type: ignore
    "Label that acts as a button with hover effect"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = "#0d6efd"  # Default link color (Bootstrap Primary)
        self.background_color_normal = (1, 1, 1, 0)  # Transparent
        self.background_color_hover = (0.9, 0.9, 0.9, 1)  # Light Gray

        # Determine initial background logic
        with self.canvas.before:  # type: ignore
            self.bg_color = Color(*self.background_color_normal)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_rect, pos=self._update_rect)  # type: ignore pylint: disable=no-member

        # Bind mouse position for hover effect
        Window.bind(mouse_pos=self.on_mouse_pos)

    def _update_rect(self, instance, value):  # pylint: disable=unused-argument
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_mouse_pos(self, window, pos):  # pylint: disable=unused-argument
        "function for mouse hover effect"
        if not self.get_root_window():
            return

        if self.collide_point(*self.to_widget(*pos)):
            # Hover state
            self.bg_color.rgba = self.background_color_hover
            self.color = "#0a58ca"  # Darker blue
        else:
            # Normal state
            self.bg_color.rgba = self.background_color_normal
            self.color = "#0d6efd"

    def on_press(self):
        self.bg_color.rgba = (0.8, 0.8, 0.8, 1)  # Darker gray on click

    def on_release(self):
        # Return to hover state color since mouse is likely still over it
        self.bg_color.rgba = self.background_color_hover


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

    def _generate_plot(
        self, x_data, y_datas, title, x_label, y_label, legends=None, exp_data=None
    ):
        try:
            generate_plot(x_data, y_datas, title, x_label, y_label, legends, exp_data)
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

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
        if not smiles_list:
            raise ValueError("Please provide at least one component")
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
        try:
            t_min = float(self.temp_min.text)
            t_max = 0.0
            if require_max:
                t_max = float(self.temp_max.text)
            return t_min, t_max
        except ValueError as e:
            raise ValueError("Temperature values must be numeric") from e

    def _get_pressure(self):
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

    def on_submit(self):
        "handle submit button for mixture parameters"
        self.predicted_parameters.clear_widgets()

        try:
            raw_smiles = self.smiles_or_inchi_input.text.split(" ")
            smiles_list = [
                get_smiles_from_input(s.strip()) for s in raw_smiles if s.strip()
            ]

            if not smiles_list:
                return

            if len(smiles_list) == 2:
                # Check for binary data availability
                try:
                    rho_data, bubble_data, lle_data, vle_data = (
                        retrieve_available_data_binary(smiles_list)
                    )

                    if any(
                        (exp_data is not None and len(exp_data) > 0)
                        for exp_data in [rho_data, bubble_data, lle_data, vle_data]
                    ):
                        self.predicted_parameters.add_widget(
                            Label(
                                text="Experimental Data Availability",
                                size_hint_y=None,
                                height=40,
                                color="#0d6efd",
                                font_size=20,
                                bold=True,
                            )
                        )

                    # Bubble Point Data (P-T Envelopes)
                    if bubble_data is not None and len(bubble_data) > 0:
                        dropdown_bp = DropDown()
                        for row in bubble_data:
                            # [x_approx, T_min, T_max]
                            btn = Button(
                                text=f"x={row[0]:.2f}: {row[1]:.2f}-{row[2]:.2f} K",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_binary(
                                        t_min=r[1], t_max=r[2], x1=r[0]
                                    ),
                                    dropdown_bp.dismiss(),
                                )
                            )
                            dropdown_bp.add_widget(btn)

                        main_button = Button(
                            text="Select Bubble Pt. Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown_bp.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                    # VLE Data
                    if vle_data is not None and len(vle_data) > 0:
                        dropdown_vle = DropDown()
                        for row in vle_data:
                            # [P_kPa, T_min, T_max]
                            # Display T range for P
                            btn = Button(
                                text=f"P={row[0]:.5g} kPa: {row[1]:.2f}-{row[2]:.2f} K",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_binary(
                                        pressure=r[0], t_min=r[1], t_max=r[2]
                                    ),
                                    dropdown_vle.dismiss(),
                                )
                            )
                            dropdown_vle.add_widget(btn)

                        main_button = Button(
                            text="Select VLE Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown_vle.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                    # LLE Data
                    if lle_data is not None and len(lle_data) > 0:
                        dropdown_lle = DropDown()
                        for row in lle_data:
                            # [P_kPa, T_min, T_max]
                            # Display T range for P
                            btn = Button(
                                text=f"P={row[0]:.5g} kPa: {row[1]:.2f}-{row[2]:.2f} K",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_binary(
                                        pressure=r[0], t_min=r[1], t_max=r[2]
                                    ),
                                    dropdown_lle.dismiss(),
                                )
                            )
                            dropdown_lle.add_widget(btn)

                        main_button = Button(
                            text="Select LLE Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown_lle.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                    # Density Data
                    if rho_data is not None and len(rho_data) > 0:
                        dropdown = DropDown()
                        for row in rho_data:
                            # [P_kPa, x_c1, T_min, T_max]
                            btn = Button(
                                text=f"P={row[0]:.5g} kPa, x={row[1]:.2f}",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_binary(
                                        pressure=r[0], t_min=r[2], t_max=r[3], x1=r[1]
                                    ),
                                    dropdown.dismiss(),
                                )
                            )
                            dropdown.add_widget(btn)

                        main_button = Button(
                            text="Select Liquid Density Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                except (ValueError, RuntimeError):
                    pass

            elif len(smiles_list) == 3:
                # Check for ternary data availability
                try:
                    rho_data_t, lle_data_t, vle_data_t = (
                        retrieve_available_data_ternary(smiles_list)
                    )

                    if any(
                        (exp_data is not None and len(exp_data) > 0)
                        for exp_data in [rho_data_t, lle_data_t, vle_data_t]
                    ):
                        self.predicted_parameters.add_widget(
                            Label(
                                text="Experimental Data Availability",
                                size_hint_y=None,
                                height=40,
                                color="#0d6efd",
                                font_size=20,
                                bold=True,
                            )
                        )

                    # Density Data
                    if rho_data_t is not None and len(rho_data_t) > 0:
                        dropdown_t = DropDown()
                        for row in rho_data_t:
                            # [P_kPa, x1, x2, T_min, T_max]
                            btn = Button(
                                text=f"P={row[0]:.5g} kPa, x=[{row[1]:.2f}, {row[2]:.2f}]",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_ternary(
                                        pressure=r[0],
                                        x1=r[1],
                                        x2=r[2],
                                        t_min=r[3],
                                        t_max=r[4],
                                    ),
                                    dropdown_t.dismiss(),
                                )
                            )
                            dropdown_t.add_widget(btn)

                        main_button = Button(
                            text="Select Ternary Density Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown_t.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                    # LLE Data
                    if lle_data_t is not None and len(lle_data_t) > 0:
                        dropdown_llet = DropDown()
                        for row in lle_data_t:
                            # [P_kPa, T_K]
                            btn = Button(
                                text=f"LLE: P={row[0]:.5g} kPa, T={row[1]:.2f} K",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_ternary(
                                        pressure=r[0],
                                        t_min=r[1],
                                        t_max=r[1],  # Set fixed T
                                    ),
                                    dropdown_llet.dismiss(),
                                )
                            )
                            dropdown_llet.add_widget(btn)

                        main_button = Button(
                            text="Select Ternary LLE Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown_llet.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                    # VLE Data (Ternary)
                    if vle_data_t is not None and len(vle_data_t) > 0:
                        dropdown_vlet = DropDown()
                        for row in vle_data_t:
                            # [P_kPa, T_K]
                            btn = Button(
                                text=f"VLE: P={row[0]:.5g} kPa, T={row[1]:.2f} K",
                                size_hint_y=None,
                                height=44,
                            )
                            btn.bind(  # type: ignore pylint: disable=no-member
                                on_release=lambda btn, r=row: (
                                    self._fill_inputs_ternary(
                                        pressure=r[0],
                                        t_min=r[1],
                                        t_max=r[1],  # Set fixed T
                                    ),
                                    dropdown_vlet.dismiss(),
                                )
                            )
                            dropdown_vlet.add_widget(btn)

                        main_button = Button(
                            text="Select Ternary VLE Data",
                            size_hint_y=None,
                            height=44,
                            size_hint_x=0.4,
                            pos_hint={"center_x": 0.5},
                            background_color=(0.1, 0.5, 0.8, 1),
                        )
                        main_button.bind(on_release=dropdown_vlet.open)  # type: ignore pylint: disable=no-member
                        self.predicted_parameters.add_widget(main_button)

                except (ValueError, RuntimeError):
                    pass

            self.predicted_parameters.add_widget(Label(size_hint_y=None, height=10))

            for smile in smiles_list:
                pred = predict_pcsaft_parameters(smile)
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
                comp_header.bind(size=comp_header.setter("text_size"))  # type: ignore pylint: disable=no-member
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
                    param_label.bind(size=param_label.setter("text_size"))  # type: ignore pylint: disable=no-member
                    table.add_widget(param_label)

                    param_label_value = Label(
                        text=f"{para:.5g}", color="#212529", halign="right"
                    )
                    param_label_value.bind(size=param_label_value.setter("text_size"))  # type: ignore pylint: disable=no-member
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
        try:
            smiles_list = self._get_smiles()
            n = len(smiles_list)
            fractions = self._get_fractions(n)
            kij_matrix = self._get_kij(n)
            t_min, t_max = self._get_temperatures(require_max=True)
            p_val = self._get_pressure()

            # Fetch Experimental Data
            exp_data = None
            if len(smiles_list) == 2:
                try:
                    # fractions[0] corresponds to x1 relative to smiles_list order
                    exp_array = retrieve_rho_binary_data(
                        smiles_list, p_val / 1000.0, fractions[0]
                    )
                    if exp_array is not None and len(exp_array) > 0:
                        exp_data = (exp_array[:, 0], exp_array[:, 1], "Exp. Data")
                except (ValueError, RuntimeError):
                    pass

            elif len(smiles_list) == 3:
                try:
                    # fractions[0]=x1, fractions[1]=x2
                    if len(fractions) >= 2:
                        exp_array = retrieve_rho_ternary_data(
                            smiles_list, p_val / 1000.0, fractions[0], fractions[1]
                        )
                        if exp_array is not None and len(exp_array) > 0:
                            exp_data = (exp_array[:, 0], exp_array[:, 1], "Exp. Data")
                except (ValueError, RuntimeError):
                    pass

            temperatures, densities = mix_den(
                smiles_list, fractions, kij_matrix, t_min, t_max, p_val
            )
            self._generate_plot(
                temperatures,
                densities,
                "Mixture Density vs Temperature",
                "Temperature (K)",
                "Density (mol/m³)",
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_vp(self):
        "plot mixture vapor pressure vs temperature"
        try:
            smiles_list = self._get_smiles()
            n = len(smiles_list)
            fractions = self._get_fractions(n)
            kij_matrix = self._get_kij(n)
            t_min, t_max = self._get_temperatures(require_max=True)

            # Fetch Experimental Bubble Point Data (P vs T for constant x)
            exp_data = None
            try:
                if len(smiles_list) == 2:
                    # Retrieve data for x1 = fractions[0]
                    exp_bp = retrieve_bubble_pressure_data(smiles_list, fractions[0])
                    if exp_bp is not None and len(exp_bp) > 0:
                        # exp_bp: [T, P_kPa] -> Convert kPa to Pa
                        exp_data = (
                            exp_bp[:, 0],
                            exp_bp[:, 1] * 1000.0,
                            "Exp. Bubble P",
                        )
            except (ValueError, RuntimeError):
                pass

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
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_binary_vle_txy(self):
        "plot binary VLE T-x-y"
        try:
            smiles_list = self._get_smiles()
            if len(smiles_list) != 2:
                raise ValueError(
                    f"VLE for binary mixture, got {len(smiles_list)} components instead"
                )

            n = len(smiles_list)
            kij_matrix = self._get_kij(n)
            p_val = self._get_pressure()

            # Retrieve Experimental Data
            exp_data = None
            try:
                vle_arr = retrieve_vle_binary_data(smiles_list, p_val / 1000.0)
                if vle_arr is not None and len(vle_arr) > 0:
                    # vle_arr: [T, x_c1]
                    exp_data = (vle_arr[:, 1], vle_arr[:, 0], "Exp. data")
            except (ValueError, RuntimeError):
                pass

            output = mix_vle(smiles_list, kij_matrix, p_val)

            # Check density for correct phase assignment (Liquid > Vapor)
            # to fix high-pressure inversions
            dens_l = output["density liquid"]
            dens_v = output["density vapor"]
            is_normal = sum(l > v for l, v in zip(dens_l, dens_v)) > len(dens_l) / 2

            self._generate_plot(
                list(
                    (output["x0"], output["y0"])
                    if is_normal
                    else (output["y0"], output["x0"])
                ),
                output["temperature"],
                f"VLE T-x-y for {smiles_list[0]} at {p_val} Pa",
                "x,y",
                "Temperature (K)",
                legends=["Liquid", "Vapor"],
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_binary_vle_xy(self):
        "plot binary VLE x-y"
        try:
            smiles_list = self._get_smiles()
            if len(smiles_list) != 2:
                raise ValueError(
                    f"VLE for binary mixture, got {len(smiles_list)} components instead"
                )

            n = len(smiles_list)
            kij_matrix = self._get_kij(n)
            p_val = self._get_pressure()

            output = mix_vle(smiles_list, kij_matrix, p_val)

            dens_l = output["density liquid"]
            dens_v = output["density vapor"]
            is_normal = sum(l > v for l, v in zip(dens_l, dens_v)) > len(dens_l) / 2

            self._generate_plot(
                *(
                    (output["x0"], output["y0"])
                    if is_normal
                    else (output["y0"], output["x0"])
                ),
                f"VLE x-y for {smiles_list[0]} at {p_val} Pa",
                "x",
                "y",
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_binary_lle_txx(self):
        "plot binary LLE T-x-x"
        try:
            smiles_list = self._get_smiles()
            if len(smiles_list) != 2:
                raise ValueError(
                    f"LLE for binary mixture, got {len(smiles_list)} components instead"
                )

            n = len(smiles_list)
            fractions = self._get_fractions(n)
            kij_matrix = self._get_kij(n)
            t_min, _ = self._get_temperatures(require_max=False)
            p_val = self._get_pressure()

            # Retrieve Experimental Data
            exp_data = None
            try:
                lle_arr = retrieve_lle_binary_data(smiles_list, p_val / 1000.0)
                if lle_arr is not None and len(lle_arr) > 0:
                    # lle_arr: [T, x_c1]
                    exp_data = (lle_arr[:, 1], lle_arr[:, 0], "Exp. data")
            except (ValueError, RuntimeError):
                pass

            output = mix_lle(smiles_list, fractions, kij_matrix, t_min, p_val)
            self._generate_plot(
                [output["x0"], output["y0"]],
                output["temperature"],
                f"LLE T-x-x for {smiles_list[0]} at {p_val} Pa",
                "x,x",
                "Temperature (K)",
                legends=["Phase 1", "Phase 2"],
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)

    def on_plot_ternary_vle_lle(self):
        "plot ternary VLE/LLE"
        try:
            smiles_list = self._get_smiles()
            if len(smiles_list) != 3:
                raise ValueError(
                    f"VLE/LLE for ternary mixture, got {len(smiles_list)} components instead"
                )

            n = len(smiles_list)
            kij_matrix = self._get_kij(n)
            t_min, _ = self._get_temperatures(require_max=False)
            p_val = self._get_pressure()

            # Fetch Experimental Data (Try LLE then VLE)
            exp_data = None
            try:
                # Try LLE first
                exp_arr = retrieve_lle_ternary_data(smiles_list, p_val / 1000.0, t_min)
                if exp_arr is not None and len(exp_arr) > 0:
                    exp_data = (exp_arr[:, 0], exp_arr[:, 1])
                else:
                    # Try VLE
                    exp_arr_vle = retrieve_vle_ternary_data(
                        smiles_list, p_val / 1000.0, t_min
                    )
                    if exp_arr_vle is not None and len(exp_arr_vle) > 0:
                        exp_data = (exp_arr_vle[:, 0], exp_arr_vle[:, 1])
            except (ValueError, RuntimeError):
                pass

            output = mix_ternary_lle(smiles_list, kij_matrix, t_min, p_val)

            self._generate_ternary_plot(
                [output["x0"], output["y0"]],
                [output["x1"], output["y1"]],
                title=f"VLE/LLE at {p_val} Pa, {t_min} K",
                a_label=smiles_list[0],
                b_label=smiles_list[1],
                legends=["Phase 1", "Phase 2"],
                exp_data=exp_data,
            )
        except (ValueError, RuntimeError) as e:
            self._show_error_alert(e)
