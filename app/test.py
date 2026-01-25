"tests"

import sys
import unittest
from unittest.mock import MagicMock, patch

# -- MOCK DEPENDENCIES BEFORE IMPORTING APP MODULES --
# This prevents GUI/Backend libraries from trying to initialize during tests
sys.modules["kivy"] = MagicMock()
sys.modules["kivy.app"] = MagicMock()
sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()
sys.modules["polars"] = MagicMock()

# Mock thermodynamic backend libraries
sys.modules["gnnepcsaft"] = MagicMock()
sys.modules["gnnepcsaft.pcsaft"] = MagicMock()
sys.modules["gnnepcsaft.pcsaft.pcsaft_feos"] = MagicMock()
sys.modules["gnnepcsaft_mcp_server"] = MagicMock()
sys.modules["gnnepcsaft_mcp_server.utils"] = MagicMock()

# -- IMPORT MODULES TO TEST --

import utils
import utils_mix
import utils_pure


class TestUtils(unittest.TestCase):
    "Test utils.py"

    @patch("utils.inchitosmiles")
    @patch("utils.smilestoinchi")
    def test_get_smiles_from_input(self, mock_s2i, mock_i2s):
        """Test SMILES/InChI input handling"""
        # Case 1: Standard SMILES input
        input_text = "CCC"
        res = utils.get_smiles_from_input(input_text)
        self.assertEqual(res, "CCC")
        mock_s2i.assert_called_with("CCC")  # Should attempt validation via conversion

        # Case 2: InChI input
        mock_i2s.return_value = "CCC_converted"
        inchi_text = "InChI=1S/C3H8/c1-3-2/h3H2,1-2H3"
        res = utils.get_smiles_from_input(inchi_text)
        self.assertEqual(res, "CCC_converted")
        mock_i2s.assert_called_with(inchi_text)


class TestUtilsPure(unittest.TestCase):
    "test utils_pure.py"

    @patch("utils_pure.predict_pcsaft_parameters")
    @patch("utils_pure.pure_den_feos")
    def test_pure_den(self, mock_calc, mock_predict):
        """Test Pure Density Logic"""
        # Setup mocks
        mock_predict.return_value = "dummy_params"
        mock_calc.return_value = 1000.0  # Mocked density result

        # Execute
        temps, dens = utils_pure.pure_den("water", 300, 310, 101325)

        # Assert
        self.assertEqual(len(temps), 10)  # np.linspace default num=10
        self.assertEqual(len(dens), 10)
        self.assertEqual(dens[0], 1000.0)
        mock_predict.assert_called_with("water")

    @patch("utils_pure.predict_pcsaft_parameters")
    @patch("utils_pure.pure_vp_feos")
    def test_pure_vp(self, mock_calc, mock_predict):
        """Test Pure Vapor Pressure Logic"""
        mock_predict.return_value = "dummy_params"
        mock_calc.return_value = 12345.0

        temps, vps = utils_pure.pure_vp("ethanol", 300, 310)

        self.assertEqual(len(temps), 10)
        self.assertEqual(vps[0], 12345.0)


class TestUtilsMix(unittest.TestCase):
    "test utils_mix.py"

    @patch("utils_mix.predict_pcsaft_parameters")
    @patch("utils_mix.mix_den_feos")
    def test_mix_den(self, mock_calc, mock_predict):
        """Test Mixture Density Logic"""
        mock_predict.side_effect = ["p1", "p2"]
        mock_calc.return_value = 800.0

        smiles = ["C1", "C2"]
        fracs = [0.5, 0.5]
        kij = [[0.0, 0.0], [0.0, 0.0]]
        temps, dens = utils_mix.mix_den(smiles, fracs, kij, 300, 310, 100000)

        self.assertEqual(len(temps), 10)
        self.assertEqual(dens[0], 800.0)

        # Verify call arguments structure
        call_kwargs = mock_calc.call_args[1]
        self.assertIn("parameters", call_kwargs)
        self.assertIn("state", call_kwargs)
        self.assertIn("kij_matrix", call_kwargs)

    @patch("utils_mix.predict_pcsaft_parameters")
    @patch("utils_mix.mix_vle_diagram_feos")
    def test_mix_vle(self, mock_calc, mock_predict):
        """Test Mixture VLE Logic"""
        mock_predict.return_value = "p"
        expected_output = {"x0": [0.1], "y0": [0.9], "temperature": [300]}
        mock_calc.return_value = expected_output

        res = utils_mix.mix_vle(["A", "B"], [[0, 0], [0, 0]], 101325)

        self.assertEqual(res, expected_output)


if __name__ == "__main__":
    unittest.main()
