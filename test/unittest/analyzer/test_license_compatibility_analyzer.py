"""Unit tests for LicenseCompatibilityAnalyzer"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open, Mock
from datetime import datetime
from requests import Response

from src.analyzer.license_compatibility_analyzer import (
    LicenseCompatibilityAnalyzer,
    FullCompatibilityCalc,
    CompatibilityCalcStrategy
)
from src.infrastructure.connectivity import Connectivity as io


class TestCompatibilityCalcStrategy(unittest.TestCase):
    """Unit tests for CompatibilityCalcStrategy abstract class."""

    def test_abstract_method(self):
        """Test that CompatibilityCalcStrategy cannot be instantiated."""
        # Abstract classes cannot be instantiated
        self.assertRaises(TypeError, CompatibilityCalcStrategy)


class TestFullCompatibilityCalc(unittest.TestCase):
    """Unit tests for FullCompatibilityCalc class."""

    def setUp(self):
        self.calc = FullCompatibilityCalc()

    def test_calculate_license_compatibility_same_licenses(self):
        """Test calculate_license_compatibility with same licenses."""
        result = self.calc.calculate_license_compatibility(['apache-2.0',
                                                            'apache-2.0'])
        # a 'same' return only makes any sense with a pairwise check,
        # this is a full one
        self.assertEqual(result, ("Yes", "n.a."))

    def test_calculate_license_compatibility_compatible(self):
        """Test calculate_license_compatibility with compatible licenses."""
        result = self.calc.calculate_license_compatibility(['0bsd', 'sunpro'])
        self.assertEqual(result, ("Yes", "n.a."))

    def test_calculate_license_compatibility_incompatible(self):
        """Test calculate_license_compatibility with incompatible licenses."""
        result = self.calc.calculate_license_compatibility(['ftl',
                                                            'gpl-3.0-only'])
        self.assertEqual(result[0], "No")

class TestLicenseCompatibilityAnalyzerClass(unittest.TestCase):
    """Unit tests for LicenseCompatibilityAnalyzer class."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_matrix.json")
        self.analyzer = LicenseCompatibilityAnalyzer(path=self.temp_file)
        

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        os.rmdir(self.temp_dir)

    def test_analyzer_builds(self):
        """Ensure default config of LicenseCompatibilityAnalyzer works."""
        analyzer = LicenseCompatibilityAnalyzer()
        self.assertIsNotNone(analyzer)

    def test_init_custom_path(self):
        """Test __init__ with custom path."""
        custom_path = "/custom/path/matrix.json"
        analyzer = LicenseCompatibilityAnalyzer(path=custom_path)
        self.assertEqual(analyzer.path, custom_path)

    def test_init_custom_strategy(self):
        """Test __init__ with custom strategy."""
        strategy = FullCompatibilityCalc()
        analyzer = LicenseCompatibilityAnalyzer(strategy=strategy)
        self.assertEqual(analyzer.compat_calc_strategy, strategy)

    def test_compat_calc_strategy_property(self):
        """Test compat_calc_strategy property getter and setter."""
        strategy = FullCompatibilityCalc()
        self.analyzer.compat_calc_strategy = strategy
        self.assertEqual(self.analyzer.compat_calc_strategy, strategy)

    def test_last_comparison_result_property(self):
        """Test last_comparison_result property getter and setter."""
        result = ("Yes", "n.a.")
        self.analyzer.last_comparison_result = result
        self.assertEqual(self.analyzer.last_comparison_result, result)

    def test_license_matrix_property_getter_empty(self):
        """Test license_matrix property getter when empty.
        Should retrieve online file."""
        self.analyzer.license_matrix = ""
        result = self.analyzer.license_matrix
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)
        
    @patch.object(io,'verify_internet_access', return_value=False)
    def test_license_matrix_property_getter_empty_offline(self, mock_verify):
        """Test license_matrix property getter when empty.
        Assume no connectivity, should return an empty string"""
        mock_verify.return_value = False
        self.analyzer.license_matrix = ""
        result = self.analyzer.license_matrix
        self.assertIsNotNone(result)
        self.assertEqual(result, "")

    def test_license_matrix_property_getter_cached(self):
        """Test license_matrix property getter when cached."""
        self.analyzer.license_matrix = {"key": "value"}
        result = self.analyzer.license_matrix
        self.assertEqual(result, {"key": "value"})

    def test_license_matrix_property_setter(self):
        """Test license_matrix property setter."""
        data = {"key": "value"}
        self.analyzer.license_matrix = data
        self.assertEqual(self.analyzer.license_matrix, data)

    def test_matrix_file_present_true(self):
        """Test matrix_file_present when file exists."""
        with open(self.temp_file, 'w', encoding='utf-8') as f:
            f.write("{}")
        self.assertTrue(self.analyzer.matrix_file_present())

    def test_matrix_file_present_false(self):
        """Test matrix_file_present when file does not exist."""
        self.assertFalse(self.analyzer.matrix_file_present())

    @patch('os.remove')
    def test_delete_matrix_file_exists(self, mock_remove):
        """Test delete_matrix_file when file exists."""
        with patch.object(self.analyzer, 'matrix_file_present',
                          return_value=True):
            self.analyzer.delete_matrix_file()
            mock_remove.assert_called_once_with(self.temp_file)

    def test_delete_matrix_file_not_exists(self):
        """Test delete_matrix_file when file does not exist."""
        with patch.object(self.analyzer, 'matrix_file_present',
                          return_value=False):
            self.analyzer.delete_matrix_file()
            # os.remove should not be called

    @patch('src.infrastructure.connectivity.Connectivity.\
verify_internet_access')
    @patch('src.infrastructure.connectivity.Connectivity.\
download_file')
    def test_download_wrapper_success(self, mock_download, mock_verify):
        """Test download_wrapper with successful download."""
        mock_verify.return_value = True
        mock_response = MagicMock()
        mock_download.return_value = mock_response
        result = self.analyzer.download_wrapper()
        self.assertEqual(result, mock_response)

    @patch('src.infrastructure.connectivity.Connectivity.\
verify_internet_access')
    def test_download_wrapper_no_internet(self, mock_verify):
        """Test download_wrapper with no internet."""
        mock_verify.return_value = False
        result = self.analyzer.download_wrapper()
        self.assertIsNone(result)

    @patch('src.infrastructure.connectivity.Connectivity.\
verify_internet_access')
    @patch('src.infrastructure.connectivity.Connectivity.download_file')
    def test_download_wrapper_multiple_attempts(self, mock_download,
                                                mock_verify):
        """Test download_wrapper with multiple attempts."""
        mock_verify.return_value = True
        mock_download.side_effect = [None, MagicMock()]
        result = self.analyzer.download_wrapper(attempts=2)
        self.assertIsNotNone(result)
        self.assertEqual(mock_download.call_count, 2)

    def test_check_timestamp_no_matrix(self):
        """Test check_timestamp with no license matrix."""
        self.analyzer.license_matrix = ""
        with patch.object(self.analyzer, 'update_license_matrix',
                          return_value=False):
            result = self.analyzer.check_timestamp()
            self.assertFalse(result)

    @patch('src.analyzer.license_compatibility_analyzer.\
LicenseCompatibilityAnalyzer.get_local_timestamp')
    @patch('src.analyzer.license_compatibility_analyzer.\
LicenseCompatibilityAnalyzer.get_online_timestamp')
    def test_check_timestamp_online_newer(self, mock_online, mock_local):
        """Test check_timestamp when online timestamp is newer."""
        mock_local.return_value = datetime(2023, 1, 1)
        mock_online.return_value = datetime(2023, 1, 2)
        self.analyzer.license_matrix = {"timestamp": "2023-01-01T00:00:00"}
        result = self.analyzer.check_timestamp()
        self.assertFalse(result)

    @patch('src.analyzer.license_compatibility_analyzer.\
LicenseCompatibilityAnalyzer.get_local_timestamp')
    @patch('src.analyzer.license_compatibility_analyzer.\
LicenseCompatibilityAnalyzer.get_online_timestamp')
    def test_check_timestamp_local_newer(self, mock_online, mock_local):
        """Test check_timestamp when local timestamp is newer."""
        mock_local.return_value = datetime(2023, 1, 2)
        mock_online.return_value = datetime(2023, 1, 1)
        self.analyzer.license_matrix = {"timestamp": "2023-01-02T00:00:00"}
        result = self.analyzer.check_timestamp()
        self.assertTrue(result)

    @patch('src.analyzer.license_compatibility_analyzer.\
LicenseCompatibilityAnalyzer.get_online_timestamp')
    def test_check_timestamp_none_online(self, mock_online):
        """Test check_timestamp when online timestamp is None."""
        mock_online.return_value = None
        self.analyzer.license_matrix = {"timestamp": "2023-01-01T00:00:00"}
        with patch.object(self.analyzer, 'get_local_timestamp',
                          return_value=datetime(2023, 1, 1)):
            result = self.analyzer.check_timestamp()
            self.assertTrue(result)

    def test_get_local_timestamp(self):
        """Test get_local_timestamp."""
        self.analyzer.license_matrix = {"timestamp": "2023-01-01T00:00:00"}
        result = self.analyzer.get_local_timestamp()
        self.assertEqual(result, datetime(2023, 1, 1))

    @patch('src.infrastructure.connectivity.Connectivity.download_file')
    def test_get_online_timestamp(self, mock_download):
        """Test get_online_timestamp."""
        mock_response = MagicMock()
        mock_response.text = "2023-01-01T00:00:00\n"
        mock_download.return_value = mock_response
        result = self.analyzer.get_online_timestamp()
        self.assertEqual(result, datetime(2023, 1, 1))

    @patch('src.infrastructure.connectivity.Connectivity.download_file')
    def test_get_online_timestamp_none(self, mock_download):
        """Test get_online_timestamp when download fails."""
        mock_download.return_value = None
        result = self.analyzer.get_online_timestamp()
        self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open,
           read_data='{"key": "value"}')
    @patch.object(LicenseCompatibilityAnalyzer, 'matrix_file_present',
                  return_value=True)
    # The actual patching is handled by the @patch decorator.
    # @patch creates an argument which needs to be passed into the test,
    # but doesn't need to be used in simple cases like this.
    def test_update_license_matrix_offline_success(self, _, _2):
        """Test update_license_matrix with offline success (updated file)."""
        result = self.analyzer.update_license_matrix()
        self.assertTrue(result)
        self.assertEqual(self.analyzer.license_matrix, {"key": "value"})

    @patch('builtins.open', new_callable=mock_open)
    @patch.object(LicenseCompatibilityAnalyzer, 'matrix_file_present',
                  return_value=True)
    def test_update_license_matrix_offline_json_error(self,
                                                      _, _2):
        """Test update_license_matrix with offline JSON error.
        Assume offline file is broken, should download from online"""
        with patch.object(self.analyzer, 'download_wrapper',
                          return_value=MagicMock()) as mock_download:
            response = Mock(spec=Response)
            response.status_code = 200
            response.json.return_value = '{"key": "value"}'
            mock_download.return_value = response
            with\
            patch('src.infrastructure.connectivity.Connectivity.safe_write',
                  return_value=True):
                result = self.analyzer.update_license_matrix()
                self.assertTrue(result)

    @patch.object(LicenseCompatibilityAnalyzer, 'matrix_file_present',
                  return_value=False)
    @patch.object(LicenseCompatibilityAnalyzer, 'download_wrapper',
                  return_value=None)
    def test_update_license_matrix_online_fail(self, _, _2):
        """Test update_license_matrix with online fail."""
        result = self.analyzer.update_license_matrix()
        self.assertFalse(result)

    @patch.object(LicenseCompatibilityAnalyzer, 'matrix_file_present',
                  return_value=False)
    @patch.object(LicenseCompatibilityAnalyzer, 'download_wrapper')
    @patch('src.infrastructure.connectivity.Connectivity.safe_write')
    def test_update_license_matrix_online_success(self, mock_write,
                                                  mock_download, _):
        """Test update_license_matrix with online success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.text = '{"key": "value"}'
        mock_download.return_value = mock_response
        mock_write.return_value = True
        result = self.analyzer.update_license_matrix()
        self.assertTrue(result)
        self.assertEqual(self.analyzer.license_matrix, {"key": "value"})

    @patch('src.infrastructure.connectivity.Connectivity.safe_read')
    def test_extract_raw_licenses_success(self, mock_safe_read):
        """Test extract_raw_licenses with success."""
        mock_safe_read.return_value = '{"files": [{"license_detections":\
            {"license-expression": "MIT"}}]}'
        result = self.analyzer.extract_raw_licenses("dummy_path")
        self.assertEqual(result, ["MIT"])

    @patch('src.infrastructure.connectivity.Connectivity.safe_read')
    def test_extract_raw_licenses_read_fail(self, mock_safe_read):
        """Test extract_raw_licenses when safe_read fails."""
        mock_safe_read.return_value = None
        result = self.analyzer.extract_raw_licenses("dummy_path")
        self.assertIsNone(result)

    @patch('src.infrastructure.connectivity.Connectivity.safe_read')
    def test_extract_raw_licenses_no_files(self, mock_safe_read):
        """Test extract_raw_licenses with no files in JSON."""
        mock_safe_read.return_value = '{"files": []}'
        result = self.analyzer.extract_raw_licenses("dummy_path")
        self.assertEqual(result, [])

    @patch.object(LicenseCompatibilityAnalyzer, 'license_matrix',
                  new_callable=lambda: {'licenses': [{'name': 'mit',\
                      'compatibilities': [{'name': 'bsd', 'compatibility':\
                          'Yes', 'explanation': 'n.a.'}]}]})
    def test_compare_licenses_compatible(self, mock_matrix):
        """Test compare_licenses with compatible licenses."""
        LicenseCompatibilityAnalyzer.license_matrix = mock_matrix
        result = LicenseCompatibilityAnalyzer.compare_licenses('mit', 'bsd')
        self.assertEqual(result, ('Yes', 'n.a.'))

    @patch.object(LicenseCompatibilityAnalyzer, 'license_matrix',
        new_callable=lambda: {'licenses': [{'name': 'mit',\
            'compatibilities': []}]})
    def test_compare_licenses_unknown_license_b(self, mock_matrix):
        """Test compare_licenses with unknown license B."""
        LicenseCompatibilityAnalyzer.license_matrix = mock_matrix
        result = LicenseCompatibilityAnalyzer.compare_licenses('mit', 'unknown')
        self.assertEqual(result, (None, None))

    @patch.object(LicenseCompatibilityAnalyzer, 'license_matrix',
                  new_callable=lambda: {'licenses': []})
    def test_compare_licenses_unknown_license_a(self, mock_matrix):
        """Test compare_licenses with unknown license A."""
        LicenseCompatibilityAnalyzer.license_matrix = mock_matrix
        result = LicenseCompatibilityAnalyzer.compare_licenses('unknown', 'mit')
        self.assertEqual(result, (None, None))

    def test_calculate_license_compatibility(self):
        """Test calculate_license_compatibility."""
        licenses = ['mit', 'bsd']
        expected_result = ("Yes", "n.a.")
        with patch.object(self.analyzer.compat_calc_strategy,
            'calculate_license_compatibility', return_value=expected_result):
            self.analyzer.calculate_license_compatibility(licenses)
            self.assertEqual(self.analyzer.last_comparison_result,
                             expected_result)
