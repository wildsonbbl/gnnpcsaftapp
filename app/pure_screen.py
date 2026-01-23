"Pure screen"

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
from utils import available_params, generate_plot, get_smiles_from_input
from utils_data import (
    retrieve_available_data_pure,
    retrieve_rho_pure_data,
    retrieve_st_pure_data,
    retrieve_vp_pure_data,
)
from utils_pure import (
    pure_den,
    pure_h_lv,
    pure_phase_diagram,
    pure_surface_tension,
    pure_vp,
)


class PureScreen(Screen):
    "Pure component screen"


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


class PureLayout(BoxLayout):
    "Pure Layout"

    smiles_or_inchi_input = ObjectProperty(None)
    temp_min = ObjectProperty(None)
    temp_max = ObjectProperty(None)
    pressure = ObjectProperty(None)
    predicted_parameters = ObjectProperty(None)

    def _generate_plot(
        self, x_data, y_data, title, x_label, y_label, legends=None, exp_data=None
    ):
        """Helper to generate plot and switch screen"""
        try:
            generate_plot(x_data, y_data, title, x_label, y_label, legends, exp_data)
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

    def _fill_inputs(self, pressure=None, t_min=None, t_max=None):
        "Helper to populate inputs with clicked values"
        if pressure is not None:
            # Data is in kPa, Input expects Pa. Convert: * 1000
            self.pressure.text = str(pressure * 1000.0)
        if t_min is not None:
            self.temp_min.text = str(t_min)
        if t_max is not None:
            self.temp_max.text = str(t_max)

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

    def on_plot_vp(self):
        "plot vapor pressure vs temperature"
        smiles, t_min, t_max = self._get_common_inputs()
        if not smiles or not t_min or not t_max:
            return
        try:
            # Fetch experimental data
            exp_data = None
            try:
                exp_array = retrieve_vp_pure_data(smiles, t_min, t_max)
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
            # Fetch experimental data
            exp_data = None
            try:
                exp_array = retrieve_st_pure_data(smiles, t_min, t_max)
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

            # Display Available Data
            try:
                rho_data, vp_range, st_range = retrieve_available_data_pure(smiles)

                if (rho_data is not None and len(rho_data) > 0) or (
                    vp_range[0] is not None or st_range[0] is not None
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

                # Surface Tension
                if st_range[0] is not None:
                    dropdown_st = DropDown()
                    btn = Button(
                        text=f"ST: {st_range[0]:.2f} - {st_range[1]:.2f} K",
                        size_hint_y=None,
                        height=44,
                    )
                    btn.bind(  # type: ignore pylint: disable=no-member
                        on_release=lambda btn: (
                            self._fill_inputs(t_min=st_range[0], t_max=st_range[1]),
                            dropdown_st.dismiss(),
                        )
                    )
                    dropdown_st.add_widget(btn)

                    main_button = Button(
                        text="Select Surface Tension Data",
                        size_hint_y=None,
                        height=44,
                        size_hint_x=0.4,
                        pos_hint={"center_x": 0.5},
                        background_color=(0.1, 0.5, 0.8, 1),
                    )
                    main_button.bind(on_release=dropdown_st.open)  # type: ignore pylint: disable=no-member
                    self.predicted_parameters.add_widget(main_button)

                # Vapor Pressure
                if vp_range[0] is not None:
                    dropdown_vp = DropDown()
                    btn = Button(
                        text=f"VP: {vp_range[0]:.2f} - {vp_range[1]:.2f} K",
                        size_hint_y=None,
                        height=44,
                    )
                    btn.bind(  # type: ignore pylint: disable=no-member
                        on_release=lambda btn: (
                            self._fill_inputs(t_min=vp_range[0], t_max=vp_range[1]),
                            dropdown_vp.dismiss(),
                        )
                    )
                    dropdown_vp.add_widget(btn)

                    main_button = Button(
                        text="Select Vapor Pressure Data",
                        size_hint_y=None,
                        height=44,
                        size_hint_x=0.4,
                        pos_hint={"center_x": 0.5},
                        background_color=(0.1, 0.5, 0.8, 1),
                    )
                    main_button.bind(on_release=dropdown_vp.open)  # type: ignore pylint: disable=no-member
                    self.predicted_parameters.add_widget(main_button)

                # Density
                if rho_data is not None and len(rho_data) > 0:
                    dropdown = DropDown()
                    for row in rho_data:
                        # row: [Pressure (kPa), T_min, T_max]
                        btn = Button(
                            text=f"P={row[0]:.5g} kPa: {row[1]:.2f} - {row[2]:.2f} K",
                            size_hint_y=None,
                            height=44,
                        )
                        btn.bind(  # type: ignore pylint: disable=no-member
                            on_release=lambda btn, r=row: (
                                self._fill_inputs(
                                    pressure=r[0], t_min=r[1], t_max=r[2]
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

                self.predicted_parameters.add_widget(Label(size_hint_y=None, height=20))
            except (ValueError, RuntimeError):
                pass  # Fail silently if data retrieval errors, proceed to prediction

            pred = predict_pcsaft_parameters(smiles)
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
                param_label.bind(  # type: ignore pylint: disable=no-member
                    size=param_label.setter("text_size")  # type: ignore pylint: disable=no-member
                )  # Ensure text aligns within widget
                table.add_widget(param_label)

                # Parameter Value
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

        except ValueError as e:
            self._show_error_alert(e)
