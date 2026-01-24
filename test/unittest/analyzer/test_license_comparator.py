"""Unit tests for LicenseComparator class."""

import pytest
from src.license_sentinel.analyzer.license_comparator import LicenseComparator
from src.license_sentinel.entities.scan_engine import ScanEngine
from src.license_sentinel.entities.pypi_metadata import PyPIMetadata


class TestLicenseComparatorCompareTrees:
    """Tests for LicenseComparator.compare_license_trees method."""

    @pytest.fixture
    def mock_scan_engine(self, mocker):
        """Fixture for mocking the ScanEngine dependency."""
        return mocker.MagicMock(spec=ScanEngine)

    @pytest.fixture
    def pypi_metadata_factory(self, mocker):
        """Helper fixture to create PyPIMetadata objects quickly."""
        def _create(pkg_name, license_type):
            meta = mocker.MagicMock(spec=PyPIMetadata)
            meta.package = pkg_name
            meta.license_type = license_type
            return meta
        return _create

    def test_init_and_process(self, mock_scan_engine, pypi_metadata_factory):
        """Test initialization and automatic license normalization."""
        meta = pypi_metadata_factory("PkgA", "MIT License")
        comparator = LicenseComparator([meta], mock_scan_engine)

        assert "PkgA" in comparator.tree_a
        assert comparator.tree_a["PkgA"] == "mit"

    def test_compare_license_trees_match(self, mock_scan_engine, pypi_metadata_factory):
        """Test scenario where PyPI and ScanCode licenses match."""
        meta = pypi_metadata_factory("PkgA", "MIT")
        mock_scan_engine.scan_for_license.return_value = ["mit"]

        comparator = LicenseComparator([meta], mock_scan_engine)
        disc, doubts = comparator.compare_license_trees()

        assert len(disc) == 0
        assert len(doubts) == 0

    def test_compare_license_trees_mismatch(self, mock_scan_engine, pypi_metadata_factory):
        """Test discrepancy: PyPI says one thing, ScanCode finds another."""
        meta = pypi_metadata_factory("PkgA", "MIT")
        mock_scan_engine.scan_for_license.return_value = ["gpl-2.0"]

        comparator = LicenseComparator([meta], mock_scan_engine)
        disc, doubts = comparator.compare_license_trees(override_cache=True)

        assert len(disc) == 1
        # Check discrepancy format: (Package, PyPI_Lic, (Scan_Lic,))
        # GPL-x-unspecified is treated as GPL-x-only in all usecases
        assert disc[0] == ("PkgA", "mit", ("gpl-2.0-only",))

    def test_compare_license_trees_multiple_match(self, mock_scan_engine, pypi_metadata_factory):
        """Test ambiguity/doubt where one of the found licenses matches PyPI."""
        meta = pypi_metadata_factory("PkgA", "MIT")
        mock_scan_engine.scan_for_license.return_value = ["apache-2.0", "mit"]

        comparator = LicenseComparator([meta], mock_scan_engine)
        disc, doubts = comparator.compare_license_trees(override_cache=True)

        assert len(disc) == 0
        assert len(doubts) == 1
        assert doubts[0][0] == "PkgA"
        assert doubts[0][1] == "mit"
        assert "apache-2.0" in doubts[0][2]

    def test_compare_license_trees_missing_in_scan(self, mock_scan_engine, pypi_metadata_factory):
        """Test error handling when scan returns empty list."""
        meta = pypi_metadata_factory("PkgA", "MIT")
        mock_scan_engine.scan_for_license.return_value = []

        comparator = LicenseComparator([meta], mock_scan_engine)

        _, doubts = comparator.compare_license_trees()
        assert doubts[0][2] == 'unknown'

    def test_compare_license_trees_single_unknown(self, mock_scan_engine, pypi_metadata_factory):
        """Test scenario where scanner returns 'Unknown'."""
        meta = pypi_metadata_factory("PkgA", "MIT")
        mock_scan_engine.scan_for_license.return_value = ["Unknown"]

        comparator = LicenseComparator([meta], mock_scan_engine)
        disc, doubts = comparator.compare_license_trees()

        assert len(doubts) == 1
        assert doubts[0][0] == "PkgA"
