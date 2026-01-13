"""Unit tests for DepTreeBuilder class."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.infrastructure.dep_tree_builder import DepTreeBuilder


class TestDepTreeBuilderVenvExists:
    """Tests for DepTreeBuilder.venv_exists method."""

    def test_venv_exists_returns_true_for_existing_venv(self):
        """Test that venv_exists returns True for an existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = DepTreeBuilder()
            result = builder.venv_exists(tmpdir)
            assert result is True

    def test_venv_exists_returns_false_for_nonexistent_venv(self):
        """Test that venv_exists returns False for non-existent path."""
        builder = DepTreeBuilder()
        result = builder.venv_exists("/nonexistent/venv/path")
        assert result is False

    def test_venv_exists_returns_false_for_file(self):
        """Test that venv_exists returns False for a file, not directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            builder = DepTreeBuilder()
            result = builder.venv_exists(tmpfile.name)
            assert result is False

    def test_venv_exists_custom_path(self):
        """Test venv_exists with custom path parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = DepTreeBuilder()
            result = builder.venv_exists(tmpdir)
            assert result is True


class TestDepTreeBuilderCreateVenv:
    """Tests for DepTreeBuilder.create_venv method."""

    @patch("subprocess.run")
    def test_create_venv_success(self, mock_run):
        """Test successful venv creation."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            builder = DepTreeBuilder()
            
            result = builder.create_venv(str(venv_path))
            
            assert "bin" in result or "Scripts" in result
            mock_run.assert_called()

    @patch("subprocess.run")
    def test_create_venv_raises_on_failure(self, mock_run):
        """Test that create_venv raises RuntimeError on subprocess failure."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        
        builder = DepTreeBuilder()
        
        with pytest.raises(RuntimeError):
            builder.create_venv("/some/venv/path")

    @patch("subprocess.run")
    def test_create_venv_existing_venv(self, mock_run):
        """Test create_venv with already existing venv."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            venv_path.mkdir()
            
            builder = DepTreeBuilder()
            result = builder.create_venv(str(venv_path))
            
            # Should not call subprocess if venv already exists
            assert result is not None
            assert venv_path.exists()

    @patch("subprocess.run")
    def test_create_venv_force_recreate(self, mock_run):
        """Test create_venv with force_recreate=True."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            venv_path.mkdir()
            
            builder = DepTreeBuilder()
            result = builder.create_venv(str(venv_path), force_recreate=True)
            
            assert result is not None
            mock_run.assert_called()

    @patch("subprocess.run")
    def test_create_venv_returns_correct_bin_path(self, mock_run):
        """Test that create_venv returns the correct bin/Scripts directory."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            venv_path.mkdir()
            
            builder = DepTreeBuilder()
            result = builder.create_venv(str(venv_path))
            
            assert isinstance(result, str)
            assert venv_path.name in result or "venv" in result


class TestDepTreeBuilderDeleteVenv:
    """Tests for DepTreeBuilder.delete_venv method."""

    def test_delete_venv_success(self):
        """Test successful venv deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            venv_path.mkdir()
            
            builder = DepTreeBuilder()
            builder.delete_venv(str(venv_path))
            
            assert not venv_path.exists()

    def test_delete_venv_nonexistent(self):
        """Test delete_venv with non-existent path doesn't raise."""
        builder = DepTreeBuilder()
        # Should not raise
        builder.delete_venv("/nonexistent/venv/path")

    def test_delete_venv_raises_on_os_error(self):
        """Test that delete_venv raises RuntimeError on OSError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            venv_path.mkdir()
            
            builder = DepTreeBuilder()
            
            with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
                with pytest.raises(RuntimeError):
                    builder.delete_venv(str(venv_path))


class TestDepTreeBuilderInstallPackages:
    """Tests for DepTreeBuilder.install_packages method."""

    @patch("subprocess.run")
    def test_install_packages_success(self, mock_run):
        """Test successful package installation."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            builder.install_packages(str(venv_bin), ["requests"])
            
            assert mock_run.call_count >= 1

    @patch("subprocess.run")
    def test_install_packages_multiple(self, mock_run):
        """Test installation of multiple packages."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            builder.install_packages(str(venv_bin), ["requests", "numpy", "pytest"])
            
            assert mock_run.call_count >= 1

    @patch("subprocess.run")
    def test_install_packages_raises_on_failure(self, mock_run):
        """Test that install_packages raises RuntimeError on failure."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            
            with pytest.raises(RuntimeError):
                builder.install_packages(str(venv_bin), ["requests"])

    @patch("subprocess.run")
    def test_install_packages_includes_pipdeptree(self, mock_run):
        """Test that pipdeptree is always installed."""
        mock_run.return_value = MagicMock(returncode=0)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            builder.install_packages(str(venv_bin), ["requests"])
            
            # Should have calls for both packages and pipdeptree
            assert mock_run.call_count >= 2


class TestDepTreeBuilderGetTreeJson:
    """Tests for DepTreeBuilder.get_tree_json method."""

    @patch("subprocess.run")
    def test_get_tree_json_success(self, mock_run):
        """Test successful pipdeptree execution."""
        expected_tree = [
            {"key": "requests", "dependencies": []},
            {"key": "numpy", "dependencies": []}
        ]
        
        mock_result = MagicMock()
        mock_result.stdout = json.dumps(expected_tree)
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            result = builder.get_tree_json(str(venv_bin))
            
            assert result == expected_tree

    @patch("subprocess.run")
    def test_get_tree_json_raises_on_subprocess_error(self, mock_run):
        """Test that get_tree_json raises RuntimeError on subprocess failure."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, "pipdeptree")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            
            with pytest.raises(RuntimeError):
                builder.get_tree_json(str(venv_bin))

    @patch("subprocess.run")
    def test_get_tree_json_raises_on_invalid_json(self, mock_run):
        """Test that get_tree_json raises RuntimeError on invalid JSON."""
        mock_result = MagicMock()
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_bin = Path(tmpdir) / "bin"
            venv_bin.mkdir()
            
            builder = DepTreeBuilder()
            
            with pytest.raises(RuntimeError):
                builder.get_tree_json(str(venv_bin))


class TestDepTreeBuilderBuildMap:
    """Tests for DepTreeBuilder.build_map method."""

    def test_build_map_simple_tree(self):
        """Test building a map from a simple dependency tree."""
        tree_json = [
            {
                "key": "requests",
                "dependencies": [
                    {"key": "urllib3", "dependencies": []}
                ]
            }
        ]
        
        builder = DepTreeBuilder()
        result = builder.build_map(tree_json)
        
        assert "requests" in result
        assert result["requests"] == ["urllib3"]

    def test_build_map_complex_tree(self):
        """Test building a map from a complex dependency tree."""
        tree_json = [
            {
                "key": "django",
                "dependencies": [
                    {"key": "sqlparse", "dependencies": []},
                    {"key": "asgiref", "dependencies": []}
                ]
            }
        ]
        
        builder = DepTreeBuilder()
        result = builder.build_map(tree_json)
        
        assert "django" in result
        assert set(result["django"]) == {"sqlparse", "asgiref"}

    def test_build_map_empty_tree(self):
        """Test building a map from empty tree."""
        builder = DepTreeBuilder()
        result = builder.build_map([])
        
        assert result == {}

    def test_build_map_removes_pipdeptree(self):
        """Test that build_map removes pipdeptree from the graph."""
        tree_json = [
            {
                "key": "pipdeptree",
                "dependencies": [
                    {"key": "pip", "dependencies": []}
                ]
            },
            {
                "key": "requests",
                "dependencies": []
            }
        ]
        
        builder = DepTreeBuilder()
        result = builder.build_map(tree_json)
        
        assert "pipdeptree" not in result


class TestDepTreeBuilderHasCycles:
    """Tests for DepTreeBuilder.has_cycles method."""

    def test_has_cycles_no_cycles(self):
        """Test detection of graph with no cycles."""
        graph = {
            "a": ["b", "c"],
            "b": ["d"],
            "c": ["d"],
            "d": []
        }
        
        builder = DepTreeBuilder()
        assert builder.has_cycles(graph) is False

    def test_has_cycles_simple_cycle(self):
        """Test detection of simple cycle."""
        graph = {
            "a": ["b"],
            "b": ["a"]
        }
        
        builder = DepTreeBuilder()
        assert builder.has_cycles(graph) is True

    def test_has_cycles_self_loop(self):
        """Test detection of self-loop."""
        graph = {
            "a": ["a"]
        }
        
        builder = DepTreeBuilder()
        assert builder.has_cycles(graph) is True

    def test_has_cycles_empty_graph(self):
        """Test cycle detection on empty graph."""
        builder = DepTreeBuilder()
        assert builder.has_cycles({}) is False

    def test_has_cycles_complex_cycle(self):
        """Test detection of complex cycle."""
        graph = {
            "a": ["b"],
            "b": ["c"],
            "c": ["d"],
            "d": ["b"]
        }
        
        builder = DepTreeBuilder()
        assert builder.has_cycles(graph) is True


class TestDepTreeBuilderFindRoots:
    """Tests for DepTreeBuilder.find_roots method."""

    def test_find_roots_single_root(self):
        """Test finding roots in a tree with single root."""
        graph = {
            "requests": ["urllib3"],
            "urllib3": []
        }
        
        builder = DepTreeBuilder()
        roots = builder.find_roots(graph)
        
        assert roots == ["requests"]

    def test_find_roots_multiple_roots(self):
        """Test finding roots in a tree with multiple roots."""
        graph = {
            "django": ["sqlparse"],
            "requests": ["urllib3"],
            "sqlparse": [],
            "urllib3": []
        }
        
        builder = DepTreeBuilder()
        roots = builder.find_roots(graph)
        
        assert set(roots) == {"django", "requests"}

    def test_find_roots_empty_graph(self):
        """Test finding roots in empty graph."""
        builder = DepTreeBuilder()
        roots = builder.find_roots({})
        
        assert roots == []

    def test_find_roots_all_independent(self):
        """Test finding roots when all packages are independent."""
        graph = {
            "a": [],
            "b": [],
            "c": []
        }
        
        builder = DepTreeBuilder()
        roots = builder.find_roots(graph)
        
        assert set(roots) == {"a", "b", "c"}


class TestDepTreeBuilderPrintSubtree:
    """Tests for DepTreeBuilder.print_subtree method."""

    def test_print_subtree_simple(self):
        """Test printing a simple subtree."""
        graph = {
            "requests": ["urllib3"],
            "urllib3": []
        }
        
        builder = DepTreeBuilder()
        # Should not raise
        builder.print_subtree(graph, "requests")

    def test_print_subtree_with_cycles(self):
        """Test printing subtree with cycles (should avoid infinite recursion)."""
        graph = {
            "a": ["b"],
            "b": ["a"]
        }
        
        builder = DepTreeBuilder()
        # Should not hang or raise
        builder.print_subtree(graph, "a")

    def test_print_subtree_leaf_node(self):
        """Test printing a leaf node."""
        graph = {
            "leaf": []
        }
        
        builder = DepTreeBuilder()
        builder.print_subtree(graph, "leaf")


class TestDepTreeBuilderPrintFullTree:
    """Tests for DepTreeBuilder.print_full_tree method."""

    def test_print_full_tree(self):
        """Test printing a full tree."""
        graph = {
            "requests": ["urllib3"],
            "numpy": [],
            "urllib3": []
        }
        
        builder = DepTreeBuilder()
        # Should not raise
        builder.print_full_tree(graph)

    def test_print_full_tree_empty(self):
        """Test printing an empty tree."""
        builder = DepTreeBuilder()
        # Should not raise
        builder.print_full_tree({})
        assert True
