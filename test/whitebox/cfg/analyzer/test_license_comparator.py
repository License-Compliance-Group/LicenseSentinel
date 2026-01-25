"""
CFG Coverage Tests for license_comparator.py

This module implements control flow graph coverage testing based on the CFG
extracted by py2cfg. It aims for path coverage where possible, falling back
to edge coverage or block coverage.

Note: The current code does not have if __name__ == "__main__" block,
but the CFG indicates it should. Testing only the import path that exists.

From the CFG log, the file has blocks:
- Block 1: Import statements and class definition (executed on import)
- Block 6: if __name__ == "__main__" check (not present in current code)
- Block 7: Main execution body (calls main()) (not present in current code)

Paths to cover:
1. Import path: Block 1 (executed on import)
"""

import sys
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock
from src.license_hierarchy.analyzer.license_comparator import LicenseComparator

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestLicenseComparator(unittest.TestCase):
    """Test class for CFG coverage of license_comparator.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_scan_engine = MagicMock()
        self.mock_scan_engine.scan_for_license.return_value = ('MIT',)
        self.test_tree_a = [
            MagicMock(package='test_pkg', license_type='MIT')
        ]

    def test_block_coverage_import(self):
        """Test Block 1 coverage - import and class definition"""
        # Importing the module executes Block 1
        from src.license_hierarchy.analyzer import license_comparator

        # Verify the class is available (Block 1 executed)
        self.assertTrue(hasattr(license_comparator, 'LicenseComparator'))

    def test_class_instantiation(self):
        """Test class instantiation and basic functionality"""
        comparator = LicenseComparator(self.test_tree_a, self.mock_scan_engine)

        # Verify Block 1 executed (class instantiated)
        self.assertIsInstance(comparator, LicenseComparator)

    def test_compare_license_trees_path_coverage(self):
        """Test path coverage for compare_license_trees method"""
        comparator = LicenseComparator(self.test_tree_a, self.mock_scan_engine)

        # Path 1: Normal comparison
        discrepancies, doubts = comparator.compare_license_trees()
        self.assertIsInstance(discrepancies, list)
        self.assertIsInstance(doubts, list)

        # Path 2: Override cache
        comparator.tree_b = {}  # Reset
        discrepancies, doubts = comparator.compare_license_trees(override_cache=True)
        self.assertIsInstance(discrepancies, list)

        # Path 3: Empty tree_a
        comparator.tree_a = None
        discrepancies, doubts = comparator.compare_license_trees()
        self.assertEqual(discrepancies, '')
        self.assertEqual(doubts, '')

    def test_run_scan_engine_path_coverage(self):
        """Test path coverage for run_scan_engine method"""
        comparator = LicenseComparator(self.test_tree_a, self.mock_scan_engine)

        # Path 1: Normal execution
        result = comparator.run_scan_engine()
        self.assertIsInstance(result, dict)

        # Path 2: Empty tree_a
        comparator.tree_a = None
        result = comparator.run_scan_engine()
        self.assertEqual(result, {})

        # Path 3: Scan engine returns None (but tree_b is not empty)
        comparator.tree_a = {'test_pkg': 'MIT'}
        self.mock_scan_engine.scan_for_license.return_value = None
        result = comparator.run_scan_engine()
        self.assertEqual(result, {'test_pkg': None})


if __name__ == '__main__':
    # Run the tests to achieve CFG coverage
    unittest.main()
