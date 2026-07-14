"tests"

# pylint: disable=missing-class-docstring,missing-function-docstring,protected-access
# pylint: disable=too-few-public-methods,unused-argument,wrong-import-position
# pylint: disable=too-many-arguments
# pylint: disable=unnecessary-lambda

import sys
import unittest
from unittest.mock import MagicMock, patch

# -- MOCK DEPENDENCIES BEFORE IMPORTING APP MODULES --
# This prevents GUI/Backend libraries from trying to initialize during tests
sys.modules["kivy"] = MagicMock()
sys.modules["kivy.app"] = MagicMock()
sys.modules["kivy.clock"] = MagicMock()
sys.modules["kivy.logger"] = MagicMock()
sys.modules["kivy.properties"] = MagicMock()
sys.modules["kivy.uix"] = MagicMock()
sys.modules["kivy.uix.boxlayout"] = MagicMock()
sys.modules["kivy.uix.button"] = MagicMock()
sys.modules["kivy.uix.dropdown"] = MagicMock()
sys.modules["kivy.uix.gridlayout"] = MagicMock()
sys.modules["kivy.uix.label"] = MagicMock()
sys.modules["kivy.uix.popup"] = MagicMock()
sys.modules["kivy.uix.progressbar"] = MagicMock()
sys.modules["kivy.uix.screenmanager"] = MagicMock()
sys.modules["kivy.uix.scrollview"] = MagicMock()
sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()
sys.modules["polars"] = MagicMock()

# Mock thermodynamic backend libraries
sys.modules["gnnepcsaft"] = MagicMock()
sys.modules["gnnepcsaft.data.ogb_utils"] = MagicMock()
sys.modules["gnnepcsaft.data.rdkit_util"] = MagicMock()
sys.modules["gnnepcsaft.pcsaft"] = MagicMock()
sys.modules["gnnepcsaft.pcsaft.pcsaft_feos"] = MagicMock()
sys.modules["gnnepcsaft_mcp_server"] = MagicMock()
sys.modules["gnnepcsaft_mcp_server.utils"] = MagicMock()

# -- IMPORT MODULES TO TEST --

from app import utils, utils_mix, utils_pure
from app.mixture_ui_builder import MixtureUIBuilder
from app.plots import mixture_binary, mixture_common, mixture_ternary, plot_helpers
from app.pure_ui_builder import PureUIBuilder, PureUIData
from app.update_check import fetch_latest_release, is_newer_version
from app.utils_data import default_mixture_output_args


class FakeArray:
    """Minimal array-like for tests that require 2D slicing."""

    class _FakeVector(list):
        def __mul__(self, other):
            return [value * other for value in self]

        def __rmul__(self, other):
            return [value * other for value in self]

        def tolist(self):
            return list(self)

    def __init__(self, data):
        self._data = data

    def __len__(self):
        return len(self._data)

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            rows, col = idx
            if isinstance(rows, slice):
                return self._FakeVector([row[col] for row in self._data])
        return self._data[idx]


class TestUtils(unittest.TestCase):
    "Test utils.py"

    @patch("app.utils.inchitosmiles")
    @patch("app.utils.smilestoinchi")
    def test_get_smiles_from_input(self, mock_s2i, mock_i2s):
        """Test SMILES/InChI input handling"""
        # Case 1: Standard SMILES input
        mock_s2i.return_value = "InChI=1S/C3H8/c1-3-2/h3H2,1-2H3"
        mock_i2s.return_value = "CCC"
        input_text = "CCC"
        res = utils.get_smiles_from_input(input_text)
        self.assertEqual(res, "CCC")
        mock_s2i.assert_called_with("CCC", False, False)

        # Case 2: InChI input
        input_text = "InChI=1S/C3H8/c1-3-2/h3H2,1-2H3"
        res = utils.get_smiles_from_input(input_text)
        self.assertEqual(res, "CCC")
        mock_i2s.assert_called_with(input_text, False, False)


class TestUtilsPure(unittest.TestCase):
    "test utils_pure.py"

    @patch("app.utils_pure.predict_pcsaft_parameters")
    @patch("app.utils_pure.pure_den_feos")
    def test_pure_den(self, mock_calc, mock_predict):
        """Test Pure Density Logic"""
        # Setup mocks
        mock_predict.return_value = "dummy_params"
        mock_calc.return_value = 1000.0  # Mocked density result

        # Execute
        temps, dens = utils_pure.pure_den("water", 300, 310, 101325, 10)

        # Assert
        self.assertEqual(len(temps), 10)  # np.linspace with num=10
        self.assertEqual(len(dens), 10)
        self.assertEqual(dens[0], 1000.0)
        mock_predict.assert_called_with("water")

    @patch("app.utils_pure.predict_pcsaft_parameters")
    @patch("app.utils_pure.pure_vp_feos")
    def test_pure_vp(self, mock_calc, mock_predict):
        """Test Pure Vapor Pressure Logic"""
        mock_predict.return_value = "dummy_params"
        mock_calc.return_value = 12345.0

        temps, vps = utils_pure.pure_vp("ethanol", 300, 310, 10)

        self.assertEqual(len(temps), 10)
        self.assertEqual(vps[0], 12345.0)


class TestUtilsMix(unittest.TestCase):
    "test utils_mix.py"

    @patch("app.utils_mix.predict_pcsaft_parameters")
    @patch("app.utils_mix.mix_den_feos")
    def test_mix_den(self, mock_calc, mock_predict):
        """Test Mixture Density Logic"""
        mock_predict.side_effect = ["p1", "p2"]
        mock_calc.return_value = 800.0

        smiles = ["C1", "C2"]
        fracs = [0.5, 0.5]
        kij = [[0.0, 0.0], [0.0, 0.0]]
        params = utils_mix.MixDenParams(
            smiles_list=smiles,
            mole_fractions=fracs,
            kij_matrix=kij,
            min_temp=300,
            max_temp=310,
            pressure=100000,
            npoints=10,
        )
        temps, dens = utils_mix.mix_den(params)

        self.assertEqual(len(temps), 10)
        self.assertEqual(dens[0], 800.0)

        # Verify call arguments structure
        call_kwargs = mock_calc.call_args[1]
        self.assertIn("parameters", call_kwargs)
        self.assertIn("state", call_kwargs)
        self.assertIn("kij_matrix", call_kwargs)

    @patch("app.utils_mix.predict_pcsaft_parameters")
    @patch("app.utils_mix.mix_vle_diagram_feos")
    def test_mix_vle(self, mock_calc, mock_predict):
        """Test Mixture VLE Logic"""
        mock_predict.return_value = "p"
        expected_output = {"x0": [0.1], "y0": [0.9], "temperature": [300]}
        mock_calc.return_value = expected_output

        res = utils_mix.mix_vle(["A", "B"], [[0, 0], [0, 0]], 101325, 10)

        self.assertEqual(res, expected_output)


class TestPlotHelpers(unittest.TestCase):
    """test plot helper utilities"""

    def test_assign_phase_by_density(self):
        """Assign phases by density ordering."""
        output = {
            "x0": [0.1, 0.9],
            "y0": [0.9, 0.1],
            "density liquid": [900.0, 700.0],
            "density vapor": [10.0, 800.0],
        }

        x_liquid, y_vapor = plot_helpers.assign_phase_by_density(output)

        self.assertEqual(x_liquid, [0.1, 0.1])
        self.assertEqual(y_vapor, [0.9, 0.9])


class TestUpdateCheck(unittest.TestCase):
    """test update-check helpers"""

    def test_is_newer_version(self):
        self.assertTrue(is_newer_version("v2.0.1", "2.0.0"))
        self.assertTrue(is_newer_version("2.1.0", "2.0.9"))
        self.assertFalse(is_newer_version("2.0.0", "2.0.0"))
        self.assertFalse(is_newer_version("2.0.0", "2.1.0"))

    @patch("app.update_check.urlopen")
    def test_fetch_latest_release(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = (
            b'{"tag_name": "v2.1.0", "html_url": "https://example.com", '
            b'"name": "Release 2.1.0", "body": "notes"}'
        )
        mock_urlopen.return_value.__enter__.return_value = response

        release = fetch_latest_release()

        self.assertEqual(release.tag_name, "v2.1.0")
        self.assertEqual(release.html_url, "https://example.com")
        self.assertEqual(release.name, "Release 2.1.0")
        self.assertEqual(release.body, "notes")


class TestPlotBinaryHandlers(unittest.TestCase):
    """test binary plot handlers"""

    @patch("app.plots.mixture_binary.mix_vle")
    def test_plot_vle_xy(self, mock_mix):
        """Plot binary VLE x-y with phase assignment."""
        output = {
            "x0": [0.2],
            "y0": [0.8],
            "density liquid": [900.0],
            "density vapor": [10.0],
        }
        mock_mix.return_value = output

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_binary.plot_vle_xy(layout)

        layout._generate_plot.assert_called_once()
        (request,) = layout._generate_plot.call_args[0]
        self.assertEqual(request.x_data, [0.2])
        self.assertEqual(request.y_data, [0.8])

    @patch("app.plots.mixture_binary.retrieve_vle_binary_data")
    @patch("app.plots.mixture_binary.mix_vle")
    def test_plot_vle_txy_exp(self, mock_mix, mock_exp):
        """Plot binary VLE T-x-y with experimental overlay."""
        mock_exp.return_value = FakeArray([[300.0, 0.2]])
        mock_mix.return_value = {
            "x0": [0.2],
            "y0": [0.8],
            "density liquid": [900.0],
            "density vapor": [10.0],
            "temperature": [300.0],
        }

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_binary.plot_vle_txy(layout)

        layout._generate_plot.assert_called_once()
        (request,), _ = layout._generate_plot.call_args
        self.assertEqual(request.x_data, [[0.2], [0.8]])
        self.assertEqual(request.y_data, [300.0])
        self.assertEqual(request.exp_data, ([0.2], [300.0], "Exp. Bubble P"))

    @patch("app.plots.mixture_binary.retrieve_vle_pxy_binary_data")
    @patch("app.plots.mixture_binary.mix_vle_pxy")
    def test_plot_vle_pxy_exp(self, mock_mix, mock_exp):
        """Plot binary VLE P-x-y with experimental overlay."""
        mock_exp.return_value = FakeArray([[0.3, 200.0]])
        mock_mix.return_value = ([0.3], [1000.0], [900.0])

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_temperatures(self, require_max=False):
                return 300.0, 0.0

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

            def get_kij_tmin_pressure(self, n, require_pressure=True):
                return (
                    [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                    300.0,
                    101325.0,
                )

        layout = DummyLayout()
        mixture_binary.plot_vle_pxy(layout)

        layout._generate_plot.assert_called_once()
        (request,), _ = layout._generate_plot.call_args
        self.assertEqual(request.x_data, [0.3])
        self.assertEqual(request.y_data, [[1000.0], [900.0]])
        self.assertEqual(request.exp_data, ([0.3], [200000.0], "Exp. Bubble P"))

    @patch("app.plots.mixture_binary.retrieve_lle_binary_data")
    @patch("app.plots.mixture_binary.retrieve_vle_binary_data")
    @patch("app.plots.mixture_binary.retrieve_vlle_binary_data")
    @patch("app.plots.mixture_binary.mix_lle")
    def test_plot_lle_txx_exp(self, mock_mix, mock_exp, mock_exp2, mock_exp3):
        """Plot binary VLE/LLE T-x-y or T-x-x with experimental overlay."""
        mock_exp.return_value = FakeArray([[300.0, 0.4]])
        mock_exp2.return_value = FakeArray([[300.0, 0.4]])
        mock_exp3.return_value = FakeArray([[300.0, 0.4]])
        mock_mix.return_value = {"x0": [0.4], "y0": [0.6], "temperature": [300.0]}

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_fractions(self, n):
                return [0.4, 0.6]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_temperatures(self, require_max=False):
                return 300.0, 0.0

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_binary.plot_lle_txx(layout)

        layout._generate_plot.assert_called_once()
        (request,), _ = layout._generate_plot.call_args
        self.assertEqual(request.x_data, [[0.4], [0.6]])
        self.assertEqual(request.y_data, [300.0])
        self.assertIn(
            request.exp_data,
            [([0.4], [300.0], "Exp. VLLE Data"), ([0.4], [300.0], "Exp. VLE Data")],
        )


class TestPlotCommonHandlers(unittest.TestCase):
    """test shared plot handlers"""

    @patch("app.plots.mixture_common.mix_den")
    @patch("app.plots.mixture_common.retrieve_rho_binary_data")
    @patch("app.plots.mixture_common.retrieve_rho_ternary_data")
    def test_plot_density_multicomponent(self, mock_rho_t, mock_rho_b, mock_mix):
        """Plot density for mixtures with more than three components."""
        mock_rho_b.return_value = None
        mock_rho_t.return_value = None
        mock_mix.return_value = ([300.0, 310.0], [800.0, 790.0])

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B", "C", "D"]

            def _get_fractions(self, n):
                return [1.0 / n] * n

            def _get_kij(self, n):
                return [[0.0] * n for _ in range(n)]

            def _get_temperatures(self, require_max=True):
                return 300.0, 310.0

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_common.plot_density(layout)

        layout._generate_plot.assert_called_once()
        (request,) = layout._generate_plot.call_args[0]
        self.assertEqual(request.x_data, [300.0, 310.0])
        self.assertEqual(request.y_data, [800.0, 790.0])

    @patch("app.plots.mixture_common.mix_vp")
    @patch("app.plots.mixture_common.retrieve_bubble_pressure_data")
    def test_plot_vp_binary_no_exp(self, mock_exp, mock_mix):
        """Plot vapor pressure without experimental overlay."""
        mock_exp.return_value = None
        mock_mix.return_value = ([300.0, 310.0], [1.0, 2.0], [0.5, 1.5])

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_fractions(self, n):
                return [0.5, 0.5]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_temperatures(self, require_max=True):
                return 300.0, 310.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_common.plot_vp(layout)

        layout._generate_plot.assert_called_once()
        (request,) = layout._generate_plot.call_args[0]
        self.assertEqual(request.x_data, [300.0, 310.0])
        self.assertEqual(request.y_data, [[1.0, 2.0], [0.5, 1.5]])

    @patch("app.plots.mixture_common.mix_den")
    @patch("app.plots.mixture_common.retrieve_rho_binary_data")
    def test_plot_density_binary_exp(self, mock_exp, mock_mix):
        """Plot density with experimental overlay for binary mixtures."""
        mock_exp.return_value = FakeArray([[300.0, 900.0]])
        mock_mix.return_value = ([300.0], [800.0])

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_fractions(self, n):
                return [0.5, 0.5]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_temperatures(self, require_max=True):
                return 300.0, 310.0

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_common.plot_density(layout)

        layout._generate_plot.assert_called_once()
        (request,), _ = layout._generate_plot.call_args
        self.assertEqual(request.x_data, [300.0])
        self.assertEqual(request.y_data, [800.0])
        self.assertEqual(request.exp_data, ([300.0], [900.0], "Exp. Data"))

    @patch("app.plots.mixture_common.mix_vp")
    @patch("app.plots.mixture_common.retrieve_bubble_pressure_data")
    def test_plot_vp_binary_exp(self, mock_exp, mock_mix):
        """Plot vapor pressure with experimental overlay for binary mixtures."""
        mock_exp.return_value = FakeArray([[300.0, 2.0]])
        mock_mix.return_value = ([300.0], [1.0], [0.5])

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B"]

            def _get_fractions(self, n):
                return [0.5, 0.5]

            def _get_kij(self, n):
                return [[0.0, 0.0], [0.0, 0.0]]

            def _get_temperatures(self, require_max=True):
                return 300.0, 310.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_common.plot_vp(layout)

        layout._generate_plot.assert_called_once()
        (request,), _ = layout._generate_plot.call_args
        self.assertEqual(request.x_data, [300.0])
        self.assertEqual(request.y_data, [[1.0], [0.5]])
        self.assertEqual(request.exp_data, ([300.0], [2000.0], "Exp. Bubble P"))


class TestPlotTernaryHandlers(unittest.TestCase):
    """test ternary plot handlers"""

    @patch("app.plots.mixture_ternary.retrieve_vle_ternary_tx_fixed_data")
    @patch("app.plots.mixture_ternary.mix_ternary_vle_tx_fixed")
    def test_plot_vle_tx_fixed(self, mock_mix, mock_exp):
        """Plot ternary VLE P-x at fixed temperature and solvent ratio."""
        mock_exp.return_value = None
        mock_mix.return_value = ([0.0, 0.5, 1.0], [1.0, 2.0, 3.0], [0.5, 1.5, 2.5])

        class DummyLayout:
            def __init__(self):
                self._generate_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B", "C"]

            def _get_fractions(self, n):
                return [0.2, 0.3, 0.5]

            def _get_kij(self, n):
                return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

            def _get_temperatures(self, require_max=False):
                return 300.0, 0.0

            def _get_npoints(self):
                return 10

        layout = DummyLayout()
        mixture_ternary.plot_vle_tx_fixed(layout)

        layout._generate_plot.assert_called_once()
        (request,) = layout._generate_plot.call_args[0]
        self.assertEqual(request.x_data, [0.0, 0.5, 1.0])
        self.assertEqual(request.y_data, [[1.0, 2.0, 3.0], [0.5, 1.5, 2.5]])
        self.assertIn("x2/(x2+x3)=0.375", request.title)

    @patch("app.plots.mixture_ternary.retrieve_vle_ternary_data")
    @patch("app.plots.mixture_ternary.retrieve_lle_ternary_data")
    @patch("app.plots.mixture_ternary.mix_ternary_lle")
    def test_plot_vle_lle_prefers_lle(self, mock_mix, mock_lle, mock_vle):
        """Prefer LLE experimental data when available."""
        mock_lle.return_value = FakeArray([[0.1, 0.2]])
        mock_vle.return_value = None
        mock_mix.return_value = {
            "x0": [0.1],
            "y0": [0.2],
            "x1": [0.3],
            "y1": [0.4],
        }

        class DummyLayout:
            def __init__(self):
                self._generate_ternary_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B", "C"]

            def _get_kij(self, n):
                return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

            def _get_temperatures(self, require_max=False):
                return 300.0, 0.0

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

            def get_kij_tmin_pressure(self, n, require_pressure=True):
                return (
                    [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                    300.0,
                    101325.0,
                )

        layout = DummyLayout()
        mixture_ternary.plot_vle_lle(layout)

        layout._generate_ternary_plot.assert_called_once()
        (request,), _ = layout._generate_ternary_plot.call_args
        self.assertEqual(request.exp_data, ([0.1], [0.2], "Exp. LLE Data"))

    @patch("app.plots.mixture_ternary.retrieve_vle_ternary_data")
    @patch("app.plots.mixture_ternary.retrieve_lle_ternary_data")
    @patch("app.plots.mixture_ternary.mix_ternary_lle")
    def test_plot_vle_lle_fallback_vle(self, mock_mix, mock_lle, mock_vle):
        """Fallback to VLE experimental data when LLE is missing."""
        mock_lle.return_value = None
        mock_vle.return_value = FakeArray([[0.5, 0.6]])
        mock_mix.return_value = {
            "x0": [0.1],
            "y0": [0.2],
            "x1": [0.3],
            "y1": [0.4],
        }

        class DummyLayout:
            def __init__(self):
                self._generate_ternary_plot = MagicMock()

            def _get_smiles(self):
                return ["A", "B", "C"]

            def _get_kij(self, n):
                return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

            def _get_temperatures(self, require_max=False):
                return 300.0, 0.0

            def _get_pressure(self):
                return 101325.0

            def _get_npoints(self):
                return 10

            def get_kij_tmin_pressure(self, n, require_pressure=True):
                return (
                    [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                    300.0,
                    101325.0,
                )

        layout = DummyLayout()
        mixture_ternary.plot_vle_lle(layout)

        layout._generate_ternary_plot.assert_called_once()
        (request,), _ = layout._generate_ternary_plot.call_args
        self.assertEqual(request.exp_data, ([0.5], [0.6], "Exp. Bubble P"))


class DummyLabel:
    """Simple label stand-in for UI builder tests."""

    def __init__(self, **kwargs):
        self.text = kwargs.get("text")
        self.bind = MagicMock()

    def setter(self, name):
        return lambda *args, **kwargs: None


class DummyGrid:
    """Simple grid stand-in for UI builder tests."""

    def __init__(self, **kwargs):
        self.add_widget = MagicMock()


class TestPureUIBuilder(unittest.TestCase):
    """test pure UI builder"""

    @patch("app.ui_helpers.Label", side_effect=lambda **kwargs: DummyLabel(**kwargs))
    def test_build_adds_availability_header(self, _mock_label):
        """Show availability header when experimental data exists."""
        test_rho_data = [[101.0, 300.0, 310.0, 5]]
        test_vp_range = 0
        test_st_range = 0
        pred = [1.0] * len(utils.available_params)

        class DummyLayout:
            def __init__(self):
                self.predicted_parameters = MagicMock()
                self._dropdown_cache = []

            def _fill_inputs(self, pressure=None, t_min=None, t_max=None):
                pass

        layout = DummyLayout()
        ui_data = PureUIData(
            rho_data=test_rho_data,
            vp_range=test_vp_range,
            st_range=test_st_range,
            pred=pred,
        )
        builder = PureUIBuilder(layout, ui_data)
        builder.build()

        label_texts = [
            call.args[0].text
            for call in layout.predicted_parameters.add_widget.call_args_list
            if hasattr(call.args[0], "text")
        ]
        self.assertIn("Experimental Data Availability", label_texts)
        self.assertGreaterEqual(len(layout._dropdown_cache), 1)

    @patch("app.ui_helpers.Label", side_effect=lambda **kwargs: DummyLabel(**kwargs))
    def test_build_skips_availability_header(self, _mock_label):
        """Skip availability header when no experimental data exists."""
        test_rho_data = []
        test_vp_range = 0
        test_st_range = 0
        pred = [1.0] * len(utils.available_params)

        class DummyLayout:
            def __init__(self):
                self.predicted_parameters = MagicMock()
                self._dropdown_cache = []

            def _fill_inputs(self, pressure=None, t_min=None, t_max=None):
                pass

        layout = DummyLayout()
        ui_data = PureUIData(
            rho_data=test_rho_data,
            vp_range=test_vp_range,
            st_range=test_st_range,
            pred=pred,
        )
        builder = PureUIBuilder(layout, ui_data)
        builder.build()

        label_texts = [
            call.args[0].text
            for call in layout.predicted_parameters.add_widget.call_args_list
            if hasattr(call.args[0], "text")
        ]
        self.assertNotIn("Experimental Data Availability", label_texts)
        self.assertEqual(len(layout._dropdown_cache), 0)


class TestMixtureUIBuilder(unittest.TestCase):
    """test mixture UI builder"""

    @patch(
        "app.mixture_ui_builder.Label",
        side_effect=lambda **kwargs: DummyLabel(**kwargs),
    )
    @patch(
        "app.ui_helpers.Label",
        side_effect=lambda **kwargs: DummyLabel(**kwargs),
    )
    @patch(
        "app.ui_helpers.GridLayout",
        side_effect=lambda **kwargs: DummyGrid(),
    )
    def test_build_binary_dropdowns(self, _mock_grid, _mock_helper_label, _mock_label):
        """Render binary availability header and dropdown sections."""
        output_args = default_mixture_output_args()
        output_args.update(
            {
                "rho_px_data_b": [[101.0, 0.5, 300.0, 310.0, 5]],
                "vle_x_data_b": [[0.5, 300.0, 310.0, 5]],
                "lle_p_data_b": [[101.0, 300.0, 310.0, 5]],
                "vle_p_data_b": [[101.0, 300.0, 310.0, 5]],
                "vle_t_data_b": [[300.0, 101.0, 110.0, 5]],
                "preds": [("A", [1.0] * len(utils.available_params))],
            }
        )

        class DummyLayout:
            def __init__(self):
                self.predicted_parameters = MagicMock()
                self._dropdown_calls = []

            def _add_dropdown(self, title, rows, make_button, width_ratio=0.4):
                self._dropdown_calls.append(title)

            def _make_binary_button(self, dropdown, text, fill_action):
                return MagicMock()

            def _fill_inputs_binary(self, request):
                pass

        layout = DummyLayout()
        builder = MixtureUIBuilder(layout, ["A", "B"], output_args)
        builder.build()

        label_texts = [
            call.args[0].text
            for call in layout.predicted_parameters.add_widget.call_args_list
            if hasattr(call.args[0], "text")
        ]
        self.assertIn("Experimental Data Availability", label_texts)
        self.assertEqual(len(layout._dropdown_calls), 5)

    @patch(
        "app.mixture_ui_builder.Label",
        side_effect=lambda **kwargs: DummyLabel(**kwargs),
    )
    @patch(
        "app.ui_helpers.Label",
        side_effect=lambda **kwargs: DummyLabel(**kwargs),
    )
    @patch(
        "app.ui_helpers.GridLayout",
        side_effect=lambda **kwargs: DummyGrid(),
    )
    def test_build_ternary_dropdowns(self, _mock_grid, _mock_helper_label, _mock_label):
        """Render ternary availability header and dropdown sections."""
        output_args = default_mixture_output_args()
        output_args.update(
            {
                "rho_data_t": [[101.0, 0.2, 0.3, 300.0, 310.0, 5]],
                "lle_data_t": [[101.0, 300.0, 5]],
                "vle_data_t": [[101.0, 300.0, 5]],
                "vle_tx_data_t": [[300.0, 0.5, 101.0, 110.0, 5]],
                "preds": [("A", [1.0] * len(utils.available_params))],
            }
        )

        class DummyLayout:
            def __init__(self):
                self.predicted_parameters = MagicMock()
                self._dropdown_calls = []

            def _add_dropdown(self, title, rows, make_button, width_ratio=0.4):
                self._dropdown_calls.append(title)

            def _make_ternary_button(self, dropdown, text, fill_action):
                return MagicMock()

            def _fill_inputs_ternary(self, request):
                pass

        layout = DummyLayout()
        builder = MixtureUIBuilder(layout, ["A", "B", "C"], output_args)
        builder.build()

        label_texts = [
            call.args[0].text
            for call in layout.predicted_parameters.add_widget.call_args_list
            if hasattr(call.args[0], "text")
        ]
        self.assertIn("Experimental Data Availability", label_texts)
        self.assertEqual(len(layout._dropdown_calls), 4)


if __name__ == "__main__":
    unittest.main()
