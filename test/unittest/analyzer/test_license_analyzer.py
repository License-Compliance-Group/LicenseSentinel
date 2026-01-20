"""Unit tests for license analyzer functions."""
import pytest
from src.analyzer.license_name_normalizer import normalize
from src.analyzer.matrix_manager import LicenseCompatibilityAnalyzer


def test_known_licenses():
    """Test mapping of known license strings."""
    assert normalize("MIT License") == "mit"
    assert normalize("Apache License 2.0") == "apache-2.0"
    assert normalize("GPL-2.0") == "gpl-2.0-only"
    assert normalize("BSD 3-Clause") == "bsd-3-clause"


def test_case_insensitive():
    """Test case insensitive matching."""
    assert normalize("mit license") == "mit"
    assert normalize("APACHE-2.0") == "apache-2.0"


def test_unknown_license():
    """Test handling of unknown licenses.
    Should return lower-case license name"""
    assert normalize("Unknown License") == 'unknown license'
    assert normalize("") == ''
    assert normalize(None) is not None


def test_spdx_like():
    """Test already SPDX-like licenses."""
    assert normalize("BSD-2-Clause") == "bsd-2-clause"


@pytest.fixture
def analyzer():
    """Set up test fixtures."""
    return LicenseCompatibilityAnalyzer()


def test_compare_licenses_same(analyzer):
    """Test comparing identical licenses."""
    result = analyzer.compare_licenses("MIT", "MIT")
    assert result is not None
    # Same licenses are a special case
    assert result[0] == "Same"


def test_compare_licenses_unknown(analyzer):
    """Test comparing unknown licenses."""
    result = analyzer.compare_licenses("Unknown", "MIT")
    assert result[0] is None  # This is a tuple (result, explanation)
    # We only care about the result.


def test_calculate_compatibility(analyzer):
    """Test calculating compatibility for multiple licenses."""
    licenses = ["MIT", "Apache-2.0"]
    analyzer.calculate_license_compatibility(licenses)
    result = analyzer.last_comparison_result
    assert result is not None
