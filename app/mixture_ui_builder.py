"""UI builder for mixture parameter results."""

from kivy.uix.label import Label

from app.input_requests import BinaryFillRequest, TernaryFillRequest
from app.ui_helpers import add_availability_header, add_footer, build_param_table
from app.utils import available_params


# pylint: disable=w0212,r0903
class MixtureUIBuilder:
    """Builds the mixture results UI for a MixtureLayout instance."""

    def __init__(self, layout, smiles_list, output_args):
        self.layout = layout
        self.smiles_list = smiles_list
        self.output_args = output_args

    def build(self):
        """Render all UI sections into the layout container."""
        self.layout.predicted_parameters.clear_widgets()

        if len(self.smiles_list) == 2:
            self._render_binary_availability()
            self._render_binary_dropdowns()
        elif len(self.smiles_list) == 3:
            self._render_ternary_availability()
            self._render_ternary_dropdowns()

        self.layout.predicted_parameters.add_widget(Label(size_hint_y=None, height=10))
        self._render_param_tables()
        self._render_footer()

    def _render_binary_availability(self):
        rho_data = self.output_args["rho_data"]
        bubble_data = self.output_args["bubble_data"]
        lle_data = self.output_args["lle_data"]
        vle_data = self.output_args["vle_data"]
        vle_pxy_data = self.output_args["vle_pxy_data"]

        if self._has_exp_data(
            [rho_data, bubble_data, lle_data, vle_data, vle_pxy_data]
        ):
            add_availability_header(self.layout)

    def _render_ternary_availability(self):
        rho_data_t = self.output_args["rho_data_t"]
        lle_data_t = self.output_args["lle_data_t"]
        vle_data_t = self.output_args["vle_data_t"]
        vle_tx_data_t = self.output_args["vle_tx_data_t"]

        if self._has_exp_data([rho_data_t, lle_data_t, vle_data_t, vle_tx_data_t]):
            add_availability_header(self.layout)

    def _render_binary_dropdowns(self):
        rho_data = self.output_args["rho_data"]
        bubble_data = self.output_args["bubble_data"]
        lle_data = self.output_args["lle_data"]
        vle_data = self.output_args["vle_data"]
        vle_pxy_data = self.output_args["vle_pxy_data"]

        self.layout._add_dropdown(
            "Select Bubble Pt. Data",
            bubble_data,
            lambda row, dropdown: self.layout._make_binary_button(
                dropdown,
                f"x={row[0]:.4f} ({int(row[3])} points)",
                lambda: self.layout._fill_inputs_binary(BinaryFillRequest(x1=row[0])),
            ),
        )

        self.layout._add_dropdown(
            "Select Isobaric VLE Data",
            vle_data,
            lambda row, dropdown: self.layout._make_binary_button(
                dropdown,
                f"Isobar: P={row[0]:.5g} kPa ({int(row[3])} points)",
                lambda: self.layout._fill_inputs_binary(
                    BinaryFillRequest(pressure=row[0])
                ),
            ),
        )

        self.layout._add_dropdown(
            "Select Isothermal VLE Data",
            vle_pxy_data,
            lambda row, dropdown: self.layout._make_binary_button(
                dropdown,
                f"Isotherm: T={row[0]:.2f} K ({int(row[3])} points)",
                lambda: self.layout._fill_inputs_binary(
                    BinaryFillRequest(t_min=row[0])
                ),
            ),
        )

        self.layout._add_dropdown(
            "Select LLE Data",
            lle_data,
            lambda row, dropdown: self.layout._make_binary_button(
                dropdown,
                f"P={row[0]:.5g} kPa ({int(row[3])} points)",
                lambda: self.layout._fill_inputs_binary(
                    BinaryFillRequest(pressure=row[0])
                ),
            ),
        )

        self.layout._add_dropdown(
            "Select Liquid Density Data",
            rho_data,
            lambda row, dropdown: self.layout._make_binary_button(
                dropdown,
                f"P={row[0]:.5g} kPa, x={row[1]:.4f} ({int(row[4])} points)",
                lambda: self.layout._fill_inputs_binary(
                    BinaryFillRequest(pressure=row[0], x1=row[1])
                ),
            ),
        )

    def _render_ternary_dropdowns(self):
        rho_data_t = self.output_args["rho_data_t"]
        lle_data_t = self.output_args["lle_data_t"]
        vle_data_t = self.output_args["vle_data_t"]
        vle_tx_data_t = self.output_args["vle_tx_data_t"]

        self.layout._add_dropdown(
            "Select Ternary Density Data",
            rho_data_t,
            lambda row, dropdown: self.layout._make_ternary_button(
                dropdown,
                (
                    f"P={row[0]:.5g} kPa, x=[{row[1]:.4f}, {row[2]:.4f}] "
                    f"({int(row[5])} points)"
                ),
                lambda: self.layout._fill_inputs_ternary(
                    TernaryFillRequest(
                        pressure=row[0],
                        x1=row[1],
                        x2=row[2],
                    )
                ),
            ),
        )

        self.layout._add_dropdown(
            "Select Ternary LLE Data",
            lle_data_t,
            lambda row, dropdown: self.layout._make_ternary_button(
                dropdown,
                (
                    f"LLE: P={row[0]:.5g} kPa, T={row[1]:.2f} K "
                    f"({int(row[2])} points)"
                ),
                lambda: self.layout._fill_inputs_ternary(
                    TernaryFillRequest(
                        pressure=row[0],
                        t_min=row[1],
                    )
                ),
            ),
        )

        self.layout._add_dropdown(
            "Select Ternary VLE Data",
            vle_data_t,
            lambda row, dropdown: self.layout._make_ternary_button(
                dropdown,
                (
                    f"VLE: P={row[0]:.5g} kPa, T={row[1]:.2f} K "
                    f"({int(row[2])} points)"
                ),
                lambda: self.layout._fill_inputs_ternary(
                    TernaryFillRequest(
                        pressure=row[0],
                        t_min=row[1],
                    )
                ),
            ),
        )

        self.layout._add_dropdown(
            "Select Ternary VLE P-x Data",
            vle_tx_data_t,
            lambda row, dropdown: self.layout._make_ternary_button(
                dropdown,
                (
                    f"VLE P-x: T={row[0]:.2f} K, "
                    f"x2/(x2+x3)={row[1]:.2f} "
                    f"({int(row[4])} points)"
                ),
                lambda: self.layout._fill_inputs_ternary(
                    TernaryFillRequest(
                        t_min=row[0],
                        x1=0.0,
                        x2=1.0 * row[1],
                    )
                ),
            ),
        )

    def _render_param_tables(self):
        for smile, pred in self.output_args["preds"]:
            comp_header = Label(
                text=f"Component: {smile}",
                size_hint_y=None,
                height=40,
                color="#198754",
                font_size=18,
                bold=True,
                halign="center",
            )
            comp_header.bind(size=comp_header.setter("text_size"))  # type: ignore pylint: disable=no-member
            self.layout.predicted_parameters.add_widget(comp_header)

            table = build_param_table(available_params, pred)
            self.layout.predicted_parameters.add_widget(table)

    def _render_footer(self):
        add_footer(self.layout)

    @staticmethod
    def _has_exp_data(exp_sets):
        return any(exp_data is not None and len(exp_data) > 0 for exp_data in exp_sets)
