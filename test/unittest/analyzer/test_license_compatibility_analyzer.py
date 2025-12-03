"""Unit tests for LicenseCompatibilityAnalyzer"""
from src.analyzer.license_compatibility_analyzer \
import LicenseCompatibilityAnalyzer


class TestLicenseCompatibilityAnalyzerClass():
    """Unit tests for LicenseCompatibilityAnalyzer class."""
    def test_analyzer_builds(self):
        """Ensure default config of LicenseCompatibilityAnalyzer works."""
        analyzer = LicenseCompatibilityAnalyzer()
        assert analyzer is not None
