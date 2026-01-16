import pytest
from src.analyzer import license_name_normalizer

def test_normalize_known_licenses():
    """Test standard cases like GPL, Apache, MIT."""
    assert license_name_normalizer.normalize("GPL-2.0") == "gpl-2.0-only"
    assert license_name_normalizer.normalize("gpl-3.0+") == "gpl-3.0-or-later"
    assert license_name_normalizer.normalize("Apache License 2.0") == "apache-2.0"
    assert license_name_normalizer.normalize("MIT License") == "mit"
    assert license_name_normalizer.normalize("BSD 3-Clause") == "bsd-3-clause"

def test_normalize_case_insensitive():
    """Test that input case does not affect output."""
    assert license_name_normalizer.normalize("mit license") == "mit"
    assert license_name_normalizer.normalize("APACHE LICENSE 2.0") == "apache-2.0"

def test_normalize_unknown_license():
    """Test fallback for unknown licenses."""
    assert license_name_normalizer.normalize("Unknown License xyz") == "unknown license xyz"
    assert license_name_normalizer.normalize("") == ""

def test_normalize_none_input():
    """Test error handling for None input."""
    with pytest.raises(AttributeError):
        license_name_normalizer.normalize(None)
