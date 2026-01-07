"""Unit tests for license analyzer functions."""
import unittest
from src.infrastructure.license_name_normalizer import normalize
from src.analyzer.license_compatibility_analyzer import LicenseCompatibilityAnalyzer


class TestNormalizeLicenseName(unittest.TestCase):
    """Test license name normalization."""

    def test_known_licenses(self):
        """Test mapping of known license strings."""
        self.assertEqual(normalize("MIT License"), "mit")
        self.assertEqual(normalize("Apache License 2.0"), "apache-2.0")
        self.assertEqual(normalize("GPL-2.0"), "gpl-2.0-only")
        self.assertEqual(normalize("BSD 3-Clause"), "bsd-3-clause")

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        self.assertEqual(normalize("mit license"), "mit")
        self.assertEqual(normalize("APACHE-2.0"), "apache-2.0")

    def test_unknown_license(self):
        """Test handling of unknown licenses.
        Should return lower-case license name"""
        self.assertEqual(normalize("Unknown License"), 'unknown license')
        self.assertEqual(normalize(""), '')
        self.assertIsNotNone(normalize(None))

    def test_spdx_like(self):
        """Test already SPDX-like licenses."""
        self.assertEqual(normalize("BSD-2-Clause"), "bsd-2-clause")


class TestLicenseCompatibilityAnalyzer(unittest.TestCase):
    """Test license compatibility analyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = LicenseCompatibilityAnalyzer()

    def test_compare_licenses_same(self):
        """Test comparing identical licenses."""
        result = self.analyzer.compare_licenses("MIT", "MIT")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Same")  # Same licenses are a special casae

    def test_compare_licenses_unknown(self):
        """Test comparing unknown licenses."""
        result = self.analyzer.compare_licenses("Unknown", "MIT")
        self.assertIsNone(result[0])    # This is a tuple (result, explanation)
                                        # We only care about the result.
    def test_calculate_compatibility(self):
        """Test calculating compatibility for multiple licenses."""
        licenses = ["MIT", "Apache-2.0"]
        self.analyzer.calculate_license_compatibility(licenses)
        result = self.analyzer.last_comparison_result
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
