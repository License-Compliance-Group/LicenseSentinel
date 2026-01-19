"""Unit tests for the TreeAnalyzer class."""

import pytest
from src.analyzer.tree_license_analyzer import TreeAnalyzer
from src.entities.pypi_metadata import PyPIMetadata


class TestTreeAnalyzer:
    """Tests for the TreeAnalyzer class."""

    @pytest.fixture
    def mock_lca_cls(self, mocker):
        """Mock the LicenseCompatibilityAnalyzer class internally used by TreeAnalyzer."""
        return mocker.patch('src.analyzer.tree_license_analyzer.LicenseCompatibilityAnalyzer')

    def test_run_tree_compatibility_check_empty_metadata(self, mock_lca_cls):
        """Test that empty metadata returns None."""
        res = TreeAnalyzer.run_tree_compatibility_check([], {})
        assert res is None

    def test_run_tree_compatibility_check_empty_graph(self, mock_lca_cls, mocker):
        """Test that empty graph returns None."""
        metadata = [mocker.MagicMock(spec=PyPIMetadata)]
        res = TreeAnalyzer.run_tree_compatibility_check(metadata, {})
        assert res is None

    def test_detect_incompatible_edges_compatible(self, mock_lca_cls):
        """Test detection with compatible licenses."""
        mock_lca_instance = mock_lca_cls.return_value
        mock_lca_instance.compare_licenses.return_value = ("Yes", "Compatible")

        graph = {"PkgA": ["PkgB"]}
        # Use different licenses so it doesn't skip the check
        license_by_pkg_diff = {"pkga": "mit", "pkgb": "bsd-3-clause"}

        edges = TreeAnalyzer.detect_incompatible_edges(
            graph, license_by_pkg_diff, mock_lca_instance
        )
        assert len(edges) == 0

    def test_detect_incompatible_edges_incompatible(self, mock_lca_cls):
        """Test detection with incompatible licenses."""
        mock_lca_instance = mock_lca_cls.return_value
        mock_lca_instance.compare_licenses.return_value = ("No", "Conflict")

        graph = {"PkgA": ["PkgB"]}
        license_by_pkg = {"pkga": "gpl-2.0-only", "pkgb": "proprietary"}

        edges = TreeAnalyzer.detect_incompatible_edges(
            graph, license_by_pkg, mock_lca_instance
        )
        
        assert len(edges) == 1
        edge = edges[0]
        assert edge[0] == "PkgA"
        assert edge[1] == "gpl-2.0-only"
        assert edge[2] == "PkgB"
        assert edge[4][0] == "No"

    def test_run_tree_compatibility_check_integration_mock(self, mock_lca_cls, mocker):
        """Integration test with mocked LCA to verify full flow."""
        mock_lca_instance = mock_lca_cls.return_value
        mock_lca_instance.compare_licenses.return_value = ("No", "Conflict")

        pkg_a = mocker.MagicMock(spec=PyPIMetadata)
        pkg_a.package = "PkgA"
        pkg_a.license_type = "GPL-2.0"
        
        pkg_b = mocker.MagicMock(spec=PyPIMetadata)
        pkg_b.package = "PkgB"
        pkg_b.license_type = "MIT"

        metadata = [pkg_a, pkg_b]
        graph = {"PkgA": ["PkgB"]}

        result = TreeAnalyzer.run_tree_compatibility_check(metadata, graph)
        
        mock_lca_cls.assert_called()
        
        mock_lca_instance.update_license_matrix.assert_called_once()
        
        assert result is not None
        assert len(result) == 1
        assert result[0][1] == "gpl-2.0-only"
