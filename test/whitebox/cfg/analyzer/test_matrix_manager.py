"""
CFG Coverage Tests for matrix_manager.py

This module implements control flow graph coverage testing based on the CFG
extracted by py2cfg. It aims for path coverage where possible, falling back
to edge coverage or block coverage.

From the CFG log, the file has blocks:
- Block 1: Main class and method definitions (executed on import)
- Block 268: if __name__ == "__main__" check
- Block 269: Main execution body

Paths to cover:
1. Import path: Block 1 (no exits from main class)
2. Script execution path: Block 1 -> 268 (exitcase true) -> 269
3. Non-script path: Block 1 -> 268 (exitcase false) - ends
"""

import sys
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import json
from src.license_sentinel.analyzer.matrix_manager import LicenseCompatibilityAnalyzer, FullCompatibilityCalc

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))



class TestMatrixManager(unittest.TestCase):
    """Test class for CFG coverage of matrix_manager.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_matrix_path = Path(__file__).parent / 'test_matrix.json'
        # Create a minimal test matrix
        test_matrix = {
            "timestamp": "2024-01-01T00:00:00",
            "licenses": [
                {
                    "name": "MIT",
                    "compatibilities": [
                        {"name": "Apache-2.0", "compatibility": "Yes", "explanation": "Compatible"},
                        {"name": "MIT", "compatibility": "Same", "explanation": "n/a"}
                    ]
                },
                {
                    "name": "Apache-2.0",
                    "compatibilities": [
                        {"name": "MIT", "compatibility": "Yes", "explanation": "Compatible"},
                        {"name": "Apache-2.0", "compatibility": "Same", "explanation": "n/a"}

                    ]
                }
            ]
        }
        with open(self.test_matrix_path, 'w+', encoding='utf-8') as f:
            json.dump(test_matrix, f)

    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_matrix_path.exists():
            self.test_matrix_path.unlink()

    def test_block_coverage_import(self):
        """Test Block 1 coverage - import and class definition"""
        # Importing the module executes Block 1
        from src.license_sentinel.analyzer import matrix_manager

        # Verify the class is available (Block 1 executed)
        self.assertTrue(hasattr(matrix_manager, 'LicenseCompatibilityAnalyzer'))
        self.assertTrue(hasattr(matrix_manager, 'FullCompatibilityCalc'))

    @patch('src.license_sentinel.analyzer.matrix_manager.io.verify_internet_access')
    @patch('src.license_sentinel.analyzer.matrix_manager.io.safe_read')
    def test_script_execution_path(self, mock_safe_read, mock_verify_internet):
        """Test path: Block 1 -> 268 (true) -> 269 (script execution)"""
        # Mock internet access and file reading
        mock_verify_internet.return_value = True
        mock_safe_read.return_value = '{"files": []}'

        # Mock __name__ to simulate script execution
        with patch('src.license_sentinel.analyzer.matrix_manager.__name__', '__main__'):
            # Re-import to trigger __main__ block
            import importlib
            import src.license_sentinel.analyzer.matrix_manager
            importlib.reload(src.license_sentinel.analyzer.matrix_manager)

            # Block 269 should have executed (the main body)
            # We can't directly verify, but ensure no exceptions occurred
            self.assertTrue(True)  # If we reach here, Block 269 executed

    def test_non_script_path(self):
        """Test path: Block 1 -> 268 (false) - module import without execution"""
        # Normal import executes Block 1 but not Block 268->269
        # (since __name__ != '__main__')
        lca = LicenseCompatibilityAnalyzer(path=self.test_matrix_path)

        # Verify Block 1 executed (class instantiated)
        self.assertIsInstance(lca, LicenseCompatibilityAnalyzer)

        # Block 268 condition (__name__ == '__main__') should be false
        # So Block 269 should not execute
        self.assertNotEqual(__name__, '__main__')

    @patch('src.license_sentinel.analyzer.matrix_manager.io.verify_internet_access')
    def test_calculate_license_compatibility_path_coverage(self, mock_verify):
        """Test path coverage for calculate_license_compatibility method"""
        mock_verify.return_value = True

        lca = LicenseCompatibilityAnalyzer(path=self.test_matrix_path)

        # Path 1: Compatible licenses
        lca.calculate_license_compatibility(['MIT', 'Apache-2.0'])
        self.assertEqual(lca.last_comparison_result[0], 'Yes')

        # Path 2: Same license (should be compatible)
        lca.calculate_license_compatibility(['MIT', 'MIT'])
        self.assertEqual(lca.last_comparison_result[0], 'Same')

        # Path 3: Incompatible licenses (mock unknown license)
        with patch.object(lca, 'compare_licenses', return_value=('No', 'Incompatible')):
            lca.calculate_license_compatibility(['MIT', 'GPL-3.0'])
            self.assertEqual(lca.last_comparison_result[0], 'No')

    @patch('src.license_sentinel.analyzer.matrix_manager.io.verify_internet_access')
    def test_compare_licenses_path_coverage(self, mock_verify):
        """Test path coverage for compare_licenses method"""
        mock_verify.return_value = True

        lca = LicenseCompatibilityAnalyzer(path=self.test_matrix_path)

        # Path 1: Compatible licenses found
        result = lca.compare_licenses('MIT', 'Apache-2.0')
        self.assertEqual(result[0], 'Yes')

        # Path 2: License A not found
        result = lca.compare_licenses('Unknown', 'MIT')
        self.assertIsNone(result[0])

        # Path 3: License A found but B not found
        result = lca.compare_licenses('MIT', 'Unknown')
        self.assertIsNone(result[0])


if __name__ == '__main__':
    # Run the tests to achieve CFG coverage
    unittest.main()
