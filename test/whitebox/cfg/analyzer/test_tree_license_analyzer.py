"""
CFG Coverage Tests for tree_license_analyzer.py

This module implements control flow graph coverage testing based on the CFG
extracted by py2cfg. It aims for path coverage where possible, falling back
to edge coverage or block coverage.

From the CFG log, the file has no blocks with exits, indicating it contains
only import statements, global variables, and class/method definitions.
There are no conditional branches to test.

Paths to cover:
1. Import path: Execute imports and class definitions
"""

import sys
import os
import json
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from src.license_hierarchy.analyzer.tree_license_analyzer import TreeAnalyzer

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestTreeLicenseAnalyzer(unittest.TestCase):
    """Test class for CFG coverage of tree_license_analyzer.py"""

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
                }
            ]
        }
        with open(self.test_matrix_path, 'w+', encoding='utf-8') as f:
            json.dump(test_matrix, f)

    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_matrix_path.exists():
            self.test_matrix_path.unlink()

    def test_import_path(self):
        """Test import path - verify module loads and classes are available"""
        # Importing the module executes the import path
        from src.license_hierarchy.analyzer import tree_license_analyzer

        # Verify the class is available
        self.assertTrue(hasattr(tree_license_analyzer, 'TreeAnalyzer'))

        # Verify class methods exist
        self.assertTrue(hasattr(TreeAnalyzer, 'explain_discrepancies'))
        self.assertTrue(hasattr(TreeAnalyzer, 'explain_doubts'))
        self.assertTrue(hasattr(TreeAnalyzer, 'run_tree_compatibility_check'))
        self.assertTrue(hasattr(TreeAnalyzer, 'detect_incompatible_edges'))
        self.assertTrue(hasattr(TreeAnalyzer, 'compile_compatibility_report'))
        self.assertTrue(hasattr(TreeAnalyzer, 'find_first_incompatibility'))

    @patch('src.license_hierarchy.analyzer.tree_license_analyzer.TreeAnalyzer.logger')
    def test_explain_discrepancies_method(self, mock_logger):
        """Test explain_discrepancies class method"""
        discrepancies = [
            ('pkg1', 'MIT', ('Apache-2.0',)),
            ('pkg2', 'GPL-3.0', ('MIT', 'BSD'))
        ]

        TreeAnalyzer.explain_discrepancies(discrepancies)

        # Verify logger.error was called
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        self.assertIn('Lacking compatibility report', error_msg)

    @patch('src.license_hierarchy.analyzer.tree_license_analyzer.TreeAnalyzer.logger')
    def test_explain_doubts_method(self, mock_logger):
        """Test explain_doubts class method"""
        # Test single doubt
        doubts = [('pkg1', 'MIT', 'Unknown')]
        TreeAnalyzer.explain_doubts(doubts)
        mock_logger.warning.assert_called()

        # Reset mock
        mock_logger.reset_mock()

        # Test multi-licensing doubt
        doubts = [('pkg2', 'MIT', ('MIT', 'Apache-2.0'))]
        TreeAnalyzer.explain_doubts(doubts)
        mock_logger.warning.assert_called()

    @patch('src.license_hierarchy.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_run_tree_compatibility_check_method(self, mock_lca_class):
        """Test run_tree_compatibility_check class method"""
        from src.license_hierarchy.entities.pypi_metadata import PyPIMetadata

        # Mock LCA
        mock_lca = MagicMock()
        mock_lca.update_license_matrix.return_value = True
        mock_lca_class.return_value = mock_lca

        # Mock detect_incompatible_edges to return empty list
        with patch.object(TreeAnalyzer, 'detect_incompatible_edges', return_value=[]):
            # Test with valid data
            packages_metadata = [
                PyPIMetadata(package='test_pkg', license_type='MIT', link=None)
            ]
            graph = {'test_pkg': []}

            result = TreeAnalyzer.run_tree_compatibility_check(packages_metadata, graph)
            self.assertEqual(result, [])

        # Test with empty packages_metadata
        result = TreeAnalyzer.run_tree_compatibility_check([], {'test': []})
        self.assertIsNone(result)

        # Test with empty graph
        result = TreeAnalyzer.run_tree_compatibility_check(packages_metadata, {})
        self.assertIsNone(result)

    @patch('src.license_hierarchy.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')
    def test_detect_incompatible_edges_method(self, mock_lca_class):
        """Test detect_incompatible_edges class method"""
        # Mock LCA
        mock_lca = MagicMock()
        mock_lca.compare_licenses.return_value = ('Yes', 'Compatible')
        mock_lca_class.return_value = mock_lca

        # Test with compatible licenses
        graph = {'parent': ['child']}
        license_by_pkg = {'parent': 'MIT', 'child': 'MIT'}

        result = TreeAnalyzer.detect_incompatible_edges(graph, license_by_pkg)
        self.assertEqual(result, [])  # Same license, no incompatibility

        # Test with incompatible licenses
        mock_lca.compare_licenses.return_value = ('No', 'Incompatible')
        license_by_pkg = {'parent': 'MIT', 'child': 'GPL-3.0'}

        result = TreeAnalyzer.detect_incompatible_edges(graph, license_by_pkg)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 'parent')  # parent package
        self.assertEqual(result[0][2], 'child')   # child package

    @patch('src.license_hierarchy.analyzer.tree_license_analyzer.logger')
    def test_compile_compatibility_report_method(self, mock_logger):
        """Test compile_compatibility_report class method"""
        # Test with no incompatible edges
        TreeAnalyzer.compile_compatibility_report([])
        mock_logger.info.assert_called_with("Dependency-tree compatibility result: Yes (all edges compatible).")

        # Reset mock
        mock_logger.reset_mock()

        # Test with incompatible edges
        incompatible_edges = [('parent', 'MIT', 'child', 'GPL-3.0', ('No', 'Incompatible'))]
        TreeAnalyzer.compile_compatibility_report(incompatible_edges)
        mock_logger.warning.assert_called_with("Dependency-tree compatibility check negative.")
        # Check that both info calls were made
        self.assertEqual(mock_logger.info.call_count, 2)
        # The calls should be: "Listing problems." and the incompatibility message
        calls = mock_logger.info.call_args_list
        self.assertEqual(calls[0][0][0], 'Listing problems.')
        self.assertEqual(calls[1][0][0], 'Incompatibility: %s (%s) -> %s (%s), reason: %s')

    def test_find_first_incompatibility_method(self):
        """Test find_first_incompatibility class method"""
        mock_lca = MagicMock()

        # Test with all compatible pairs
        mock_lca.compare_licenses.return_value = ('Yes', 'Compatible')
        pkg_licenses = [('pkg1', 'MIT'), ('pkg2', 'MIT'), ('pkg3', 'Apache-2.0')]
        result = TreeAnalyzer.find_first_incompatibility(mock_lca, pkg_licenses)
        self.assertIsNone(result)

        # Test with incompatible pair
        mock_lca.compare_licenses.return_value = ('No', 'Incompatible')
        result = TreeAnalyzer.find_first_incompatibility(mock_lca, pkg_licenses)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 5)  # Should return 5-tuple


if __name__ == '__main__':
    # Run the tests to achieve CFG coverage
    unittest.main()
