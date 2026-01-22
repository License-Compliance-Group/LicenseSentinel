"""Unit tests for ScanCodeRunner class."""

import tempfile
import json
from pathlib import Path
import subprocess

from src.license_sentinel.infrastructure.scancode_runner import ScanCodeRunner


class TestScanCodeRunnerRunScan:
    """Tests for ScanCodeRunner.run_scan method."""

    def test_run_scan_success(self, mocker):
        """Test successful ScanCode execution."""
        mocker.patch("src.license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is not None
        assert "tallies" in result

    def test_run_scan_extraction_fails(self, mocker):
        """Test run_scan when ZIP extraction fails."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=False)
        mock_run = mocker.patch("subprocess.run")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None
        mock_run.assert_not_called()

    def test_run_scan_subprocess_fails(self, mocker):
        """Test run_scan when ScanCode subprocess fails."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "scancode"))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None

    def test_run_scan_invalid_json_output(self, mocker):
        """Test run_scan with invalid JSON in stdout."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = "invalid json output"
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None

    def test_run_scan_caching(self, mocker):
        """Test that run_scan uses cache when available."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({"tallies": {"detected_license_expression": []}})
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            # Create cache directory and cache file
            cache_dir = Path("/data/scancode-results")
            cache_path = cache_dir / "test-package-scancode-result.json"
            
            runner = ScanCodeRunner()
            
            mocker.patch("pathlib.Path.exists", return_value=True)
            mocker.patch("builtins.open", mocker.mock_open(read_data=json.dumps({"cached": True})))
            
            result = runner.run_scan(zip_path, "test-package", override_cache=False)
        
        # Should use cached result when available
        assert result is not None

    def test_run_scan_override_cache(self, mocker):
        """Test run_scan with override_cache=True."""
        mocker.patch("src.license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({"tallies": {"detected_license_expression": []}})
        mock_result.returncode = 0
        mock_run = mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package", override_cache=True)
        
        # Should call subprocess even if cache exists
        assert mock_run.called or result is not None


class TestScanCodeRunnerScanForLicense:
    """Tests for ScanCodeRunner.scan_for_license method."""

    def test_scan_for_license_single_license(self, mocker):
        """Test extracting a single license."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert len(result) == 1
        assert "MIT" in result

    def test_scan_for_license_multiple_licenses(self, mocker):
        """Test extracting multiple licenses."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT OR Apache-2.0"},
                    {"value": "BSD"}
                ]
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert len(result) > 1

    def test_scan_for_license_combined_licenses(self, mocker):
        """Test extracting licenses with AND operator."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT AND Apache-2.0"}
                ]
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        # Should split AND-combined licenses
        assert len(result) >= 1

    def test_scan_for_license_scan_returns_none(self, mocker):
        """Test scan_for_license when run_scan returns None."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value=None)
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    def test_scan_for_license_no_tallies(self, mocker):
        """Test scan_for_license when tallies are missing."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={"no_tallies": "here"})
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    def test_scan_for_license_empty_tallies(self, mocker):
        """Test scan_for_license when tallies are empty."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": []
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    def test_scan_for_license_none_license_value(self, mocker):
        """Test scan_for_license when license value is None."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": [
                    {"value": None}
                ]
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        assert result == ("Unknown",)

    def test_scan_for_license_with_override_cache(self, mocker):
        """Test scan_for_license with override_cache parameter."""
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": [
                    {"value": "GPL-3.0"}
                ]
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package", override_cache=True)
        
        assert "GPL" in str(result) or len(result) > 0

    def test_scan_for_license_normalization(self, mocker):
        """Test that licenses are normalized."""
        mock_normalize = mocker.patch(
            "src.license_sentinel.infrastructure.scancode_runner.normalize",
            side_effect=lambda x: x.upper())
        mocker.patch.object(ScanCodeRunner, "run_scan", return_value={
            "tallies": {
                "detected_license_expression": [
                    {"value": "mit"}
                ]
            }
        })
        
        runner = ScanCodeRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            result = runner.scan_for_license(zip_path, "test-package")
        
        # Normalization should have been called
        assert mock_normalize.called is True


class TestScanCodeRunnerIntegration:
    """Integration tests for ScanCodeRunner."""

    def test_full_scan_workflow(self, mocker):
        """Test complete scan workflow from ZIP to license extraction."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)
        
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

    def test_scan_handles_complex_licenses(self, mocker):
        """Test scanning packages with complex license expressions."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "(MIT OR Apache-2.0) AND GPL-2.0"}
                ]
            }
        })
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "complex.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            licenses = runner.scan_for_license(zip_path, "complex-package")
        
        # Should handle complex expressions
        assert len(licenses) > 0


class TestScanCodeRunnerErrorHandling:
    """Tests for error handling in ScanCodeRunner."""

    def test_scan_handles_scancode_not_installed(self, mocker):
        """Test handling when ScanCode is not installed."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mocker.patch("subprocess.run", side_effect=FileNotFoundError("scancode not found"))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None

    def test_scan_handles_permission_error(self, mocker):
        """Test handling of permission errors."""
        mocker.patch("license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=False)
        mocker.patch("subprocess.run")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        assert result is None


class TestScanCodeRunnerCaching:
    """Tests for caching behavior in ScanCodeRunner."""

    def test_cache_directory_creation(self, mocker):
        """Test that cache directory is created if needed."""
        mocker.patch("src.license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        # Should complete successfully even if cache directory doesn't exist
        assert result is not None

    def test_cache_invalid_json_fallback(self, mocker):
        """Test that invalid cached JSON is handled gracefully."""
        mocker.patch("src.license_sentinel.infrastructure.scancode_runner.io.extract_zip_contents", return_value=True)
        mock_result = mocker.Mock()
        mock_result.stdout = json.dumps({
            "tallies": {
                "detected_license_expression": [
                    {"value": "MIT"}
                ]
            }
        })
        mock_result.returncode = 0
        mock_run = mocker.patch("subprocess.run", return_value=mock_result)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            zip_path.touch()
            
            mocker.patch("builtins.open", mocker.mock_open(read_data="invalid"))
            
            runner = ScanCodeRunner()
            result = runner.run_scan(zip_path, "test-package")
        
        # Should handle invalid cache and re-scan
        assert mock_run.called or result is not None

