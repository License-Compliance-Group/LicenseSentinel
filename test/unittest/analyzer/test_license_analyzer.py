"""Unit tests for license analyzer functions."""
import unittest
from src.analyzer.main import normalize_license_name
from src.analyzer.license_compatibility_analyzer import LicenseCompatibilityAnalyzer


class TestNormalizeLicenseName(unittest.TestCase):
    """Test license name normalization."""

    def test_known_licenses(self):
        """Test mapping of known license strings."""
        self.assertEqual(normalize_license_name("MIT License"), "MIT")
        self.assertEqual(normalize_license_name("Apache License 2.0"), "Apache-2.0")
        self.assertEqual(normalize_license_name("GPL-2.0"), "GPL-2.0-only")
        self.assertEqual(normalize_license_name("BSD 3-Clause"), "BSD-3-Clause")

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        self.assertEqual(normalize_license_name("mit license"), "MIT")
        self.assertEqual(normalize_license_name("APACHE-2.0"), "Apache-2.0")

    def test_unknown_license(self):
        """Test handling of unknown licenses."""
        self.assertIsNone(normalize_license_name("Unknown License"))
        self.assertIsNone(normalize_license_name(""))

    def test_spdx_like(self):
        """Test already SPDX-like licenses."""
        self.assertEqual(normalize_license_name("BSD-2-Clause"), "BSD-2-Clause")


class TestLicenseCompatibilityAnalyzer(unittest.TestCase):
    """Test license compatibility analyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = LicenseCompatibilityAnalyzer()

    def test_compare_licenses_same(self):
        """Test comparing identical licenses."""
        result = self.analyzer.compare_licenses("MIT", "MIT")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Yes")  # Assuming same licenses are compatible

    def test_compare_licenses_unknown(self):
        """Test comparing unknown licenses."""
        result = self.analyzer.compare_licenses("Unknown", "MIT")
        self.assertIsNone(result)

    def test_calculate_compatibility(self):
        """Test calculating compatibility for multiple licenses."""
        licenses = ["MIT", "Apache-2.0"]
        result = self.analyzer.calculate_license_compatibility(licenses)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
