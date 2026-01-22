"""Unit tests for license_name_normalizer module."""

import pytest
from src.infrastructure import license_name_normalizer


class TestLicenseNameNormalizerNormalize:
    """Tests for license_name_normalizer.normalize function."""

    def test_normalize_known_licenses(self):
        """Test standard cases like GPL, Apache, MIT."""
        assert license_name_normalizer.normalize("GPL-2.0") == "gpl-2.0-only"
        assert license_name_normalizer.normalize("gpl-3.0+") == "gpl-3.0-or-later"
        assert license_name_normalizer.normalize("Apache License 2.0") == "apache-2.0"
        assert license_name_normalizer.normalize("MIT License") == "mit"
        assert license_name_normalizer.normalize("BSD 3-Clause") == "bsd-3-clause"

    def test_normalize_case_insensitive(self):
        """Test that input case does not affect output."""
        assert license_name_normalizer.normalize("mit license") == "mit"
        assert license_name_normalizer.normalize("APACHE LICENSE 2.0") == "apache-2.0"

    def test_normalize_unknown_license(self):
        """Test fallback for unknown licenses."""
        assert license_name_normalizer.normalize("Unknown License xyz") == "unknown license xyz"
        assert license_name_normalizer.normalize("") == ""

    def test_normalize_none_input(self):
        """Test error handling for None input."""
        assert license_name_normalizer.normalize(None) == ''
