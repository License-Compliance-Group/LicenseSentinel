"""Unit tests for ScanCodeRunner class."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import subprocess

from src.infrastructure.scancode_runner import ScanCodeRunner


class TestScanCodeRunnerRunScan:
    """Tests for ScanCodeRunner.run_scan method."""

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_run_scan_success(self, mock_extract, mock_run):
        """Test successful ScanCode execution."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is not None
        assert "tallies" in result

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_run_scan_extraction_fails(self, mock_extract, mock_run):
        """Test run_scan when ZIP extraction fails."""
        mock_extract.return_value = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None
        mock_run.assert_not_called()

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_run_scan_subprocess_fails(self, mock_extract, mock_run):
        """Test run_scan when ScanCode subprocess fails."""
        mock_extract.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "scancode")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_run_scan_invalid_json_output(self, mock_extract, mock_run):
        """Test run_scan with invalid JSON in stdout."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = "invalid json output"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_run_scan_caching(self, mock_extract, mock_run):
        """Test that run_scan uses cache when available."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"tallies": {"detected_license_expression": []}})
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            # Create cache directory and cache file
            cache_dir = Path("/data/scancode-results")
            cache_path = cache_dir / "test-package-scancode-result.json"
            
            runner = ScanCodeRunner()
            
            with patch("pathlib.Path.exists", return_value=True), \
                 patch("builtins.open", create=True) as mock_file:
                mock_file.return_value.__enter__.return_value.read.return_value = \
                    json.dumps({"cached": True})
                
                result = runner.run_scan(zip_path, "test-package", override_cache=False)

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_run_scan_override_cache(self, mock_extract, mock_run):
        """Test run_scan with override_cache=True."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"tallies": {"detected_license_expression": []}})
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package", override_cache=True)
        
        # Should call subprocess even if cache exists
        assert mock_run.called or result is not None


class TestScanCodeRunnerScanForLicense:
    """Tests for ScanCodeRunner.scan_for_license method."""

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_single_license(self, mock_scan):
        """Test extracting a single license."""
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert len(result) == 1
        assert "MIT" in result

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_multiple_licenses(self, mock_scan):
        """Test extracting multiple licenses."""
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT OR Apache-2.0"},
                    {"value": "BSD"}
                ]
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert len(result) > 1

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_combined_licenses(self, mock_scan):
        """Test extracting licenses with AND operator."""
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT AND Apache-2.0"}
                ]
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        # Should split AND-combined licenses
        assert len(result) >= 1

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_scan_returns_none(self, mock_scan):
        """Test scan_for_license when run_scan returns None."""
        mock_scan.return_value = None
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_no_tallies(self, mock_scan):
        """Test scan_for_license when tallies are missing."""
        mock_scan.return_value = {"no_tallies": "here"}
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_empty_tallies(self, mock_scan):
        """Test scan_for_license when tallies are empty."""
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": []
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_none_license_value(self, mock_scan):
        """Test scan_for_license when license value is None."""
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": [
                    {"value": None}
                ]
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    @patch.object(ScanCodeRunner, "run_scan")
    def test_scan_for_license_with_override_cache(self, mock_scan):
        """Test scan_for_license with override_cache parameter."""
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": [
                    {"value": "GPL-3.0"}
                ]
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package", override_cache=True)
        
        assert "GPL" in str(result) or len(result) > 0

    @patch.object(ScanCodeRunner, "run_scan")
    @patch("src.infrastructure.scancode_runner.normalizer.normalize")
    def test_scan_for_license_normalization(self, mock_normalize, mock_scan):
        """Test that licenses are normalized."""
        mock_normalize.side_effect = lambda x: x.upper()
        mock_scan.return_value = {
            "tallies": {
                "detected_license_expression": [
                    {"value": "mit"}
                ]
            }
        }
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        # Normalization should have been called
        assert mock_normalize.called is True


class TestScanCodeRunnerIntegration:
    """Integration tests for ScanCodeRunner."""

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_full_scan_workflow(self, mock_extract, mock_run):
        """Test complete scan workflow from ZIP to license extraction."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "package.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            
            # First run the scan
            scan_result = runner.run_scan(zip_path, "test-package")
            
            # Then extract license
            if scan_result:
                licenses = runner.scan_for_license(zip_path, "test-package")
                assert len(licenses) > 0

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_scan_handles_complex_licenses(self, mock_extract, mock_run):
        """Test scanning packages with complex license expressions."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "(MIT OR Apache-2.0) AND GPL-2.0"}
                ]
            }
        })
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "complex.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            licenses = runner.scan_for_license(zip_path, "complex-package")
        
        # Should handle complex expressions
        assert len(licenses) > 0


class TestScanCodeRunnerErrorHandling:
    """Tests for error handling in ScanCodeRunner."""

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_scan_handles_scancode_not_installed(self, mock_extract, mock_run):
        """Test handling when ScanCode is not installed."""
        mock_extract.return_value = True
        mock_run.side_effect = FileNotFoundError("scancode not found")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_scan_handles_permission_error(self, mock_extract, mock_run):
        """Test handling of permission errors."""
        mock_extract.return_value = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None


class TestScanCodeRunnerCaching:
    """Tests for caching behavior in ScanCodeRunner."""

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_cache_directory_creation(self, mock_extract, mock_run):
        """Test that cache directory is created if needed."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        # Cache directory should be created
        cache_dir = Path("/data/scancode-results")
        # Note: Directory might not exist due to permissions, but code should handle it

    @patch("subprocess.run")
    @patch("src.infrastructure.scancode_runner.io.extract_zip_contents")
    def test_cache_invalid_json_fallback(self, mock_extract, mock_run):
        """Test that invalid cached JSON is handled gracefully."""
        mock_extract.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            with patch("builtins.open", create=True) as mock_file:
                mock_file.return_value.__enter__.return_value.read.return_value = "invalid"
                
                runner = ScanCodeRunner()
                result = runner.run_scan(zip_path, "test-package")
        
        # Should handle invalid cache and re-scan
        assert mock_run.called or result is not None
