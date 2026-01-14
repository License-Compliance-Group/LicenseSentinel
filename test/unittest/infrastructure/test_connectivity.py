"""Unit tests for Connectivity class."""

import pytest
from pathlib import Path
import zipfile
import tempfile

from src.infrastructure.connectivity import Connectivity


class TestConnectivityCheckFileExists:
    """Tests for Connectivity.check_file_exists method."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.temp_file_path = Path(self.temp_file.name)
        self.temp_file.write("test content")
        self.temp_file.close()
        yield
        """Clean up test fixtures."""
        self.temp_file_path.unlink(missing_ok=True)

    def test_check_file_exists_valid_file(self):
        """Test that check_file_exists returns True for an existing file."""
        result = Connectivity.check_file_exists(self.temp_file_path)
        assert result is True

    def test_check_file_exists_nonexistent_file(self):
        """Test that check_file_exists returns False for a non-existent file."""
        result = Connectivity.check_file_exists(Path("/nonexistent/path/file.txt"))
        assert result is False

    def test_check_file_exists_permission_error(self, mocker):
        """Test that check_file_exists returns False on PermissionError."""
        mocker.patch("pathlib.Path.open", side_effect=PermissionError())
        result = Connectivity.check_file_exists(Path("/some/path/file.txt"))
        assert result is False

    def test_check_file_exists_io_error(self, mocker):
        """Test that check_file_exists returns False on IOError."""
        mocker.patch("pathlib.Path.open", side_effect=IOError())
        result = Connectivity.check_file_exists(Path("/some/path/file.txt"))
        assert result is False


class TestConnectivitySafeWrite:
    """Tests for Connectivity.safe_write method."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)
        yield
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_safe_write_success(self):
        """Test that safe_write successfully writes to a file."""
        file_path = self.temp_dir_path / "test.txt"
        content = "test content"

        result = Connectivity.safe_write(file_path, content)

        assert result is True
        assert file_path.exists()
        assert file_path.read_text() == content

    def test_safe_write_creates_new_file(self):
        """Test that safe_write creates a new file if it doesn't exist."""
        file_path = self.temp_dir_path / "new_file.txt"
        content = "new content"

        result = Connectivity.safe_write(file_path, content)

        assert result is True
        assert file_path.exists()

    def test_safe_write_io_error(self, mocker):
        """Test that safe_write returns False on IOError."""
        mocker.patch("builtins.open", side_effect=IOError("Write error"))
        result = Connectivity.safe_write(Path("/some/path/file.txt"), "content")
        assert result is False

    def test_safe_write_overwrites_existing(self):
        """Test that safe_write overwrites existing file content."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file_path = Path(temp_file.name)
        temp_file.write("old content")
        temp_file.close()

        try:
            new_content = "new content"
            result = Connectivity.safe_write(temp_file_path, new_content)

            assert result is True
            assert temp_file_path.read_text() == new_content
        finally:
            temp_file_path.unlink(missing_ok=True)


class TestConnectivitySafeRead:
    """Tests for Connectivity.safe_read method."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.temp_file_path = Path(self.temp_file.name)
        self.temp_file.write("test content")
        self.temp_file.close()
        yield
        """Clean up test fixtures."""
        self.temp_file_path.unlink(missing_ok=True)

    def test_safe_read_success(self):
        """Test that safe_read successfully reads a file."""
        result = Connectivity.safe_read(self.temp_file_path)
        assert result == "test content"

    def test_safe_read_nonexistent_file(self):
        """Test that safe_read returns None for non-existent file."""
        result = Connectivity.safe_read(Path("/nonexistent/path/file.txt"))
        assert result is None

    def test_safe_read_io_error(self, mocker):
        """Test that safe_read returns None on IOError."""
        mocker.patch("builtins.open", side_effect=IOError("Read error"))
        result = Connectivity.safe_read(Path("/some/path/file.txt"))
        assert result is None

    def test_safe_read_attribute_error(self):
        """Test that safe_read returns None on AttributeError."""
        result = Connectivity.safe_read(None)
        assert result is None


class TestConnectivityVerifyInternetAccess:
    """Tests for Connectivity.verify_internet_access method."""

    def test_verify_internet_access_success(self, mocker):
        """Test that verify_internet_access returns True when connection succeeds."""
        mock_response = mocker.Mock()
        mock_response.raise_for_status.return_value = None
        mocker.patch("requests.head", return_value=mock_response)

        result = Connectivity.verify_internet_access()
        assert result is True

    def test_verify_internet_access_http_error(self, mocker):
        """Test that verify_internet_access returns False on HTTPError."""
        import requests
        mock_response = mocker.Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mocker.patch("requests.head", return_value=mock_response)

        result = Connectivity.verify_internet_access()
        assert result is False

    def test_verify_internet_access_connection_error(self, mocker):
        """Test that verify_internet_access returns False on ConnectionError."""
        import requests
        mock_head = mocker.patch("requests.head")
        mock_head.side_effect = requests.ConnectionError()

        result = Connectivity.verify_internet_access()
        assert result is False

    def test_verify_internet_access_timeout(self, mocker):
        """Test that verify_internet_access handles timeout."""
        import requests
        mock_head = mocker.patch("requests.head")
        mock_head.side_effect = requests.Timeout()

        result = Connectivity.verify_internet_access()
        # Should not raise, returns False
        assert result is False

    def test_verify_internet_access_custom_host(self, mocker):
        """Test verify_internet_access with custom host."""
        mock_response = mocker.Mock()
        mock_response.raise_for_status.return_value = None
        mock_head = mocker.patch("requests.head", return_value=mock_response)

        result = Connectivity.verify_internet_access(host="https://custom.com")
        assert result is True
        mock_head.assert_called_once_with("https://custom.com", timeout=30)


class TestConnectivityDownloadFile:
    """Tests for Connectivity.download_file method."""

    def test_download_file_success(self, mocker):
        """Test that download_file successfully downloads a file."""
        mock_internet = mocker.patch("src.infrastructure.connectivity.Connectivity.verify_internet_access")
        mock_internet.return_value = True
        mock_response = mocker.Mock()
        mock_response.headers.get.return_value = "1000"
        mock_response.raise_for_status.return_value = None
        mocker.patch("requests.get", return_value=mock_response)

        result = Connectivity.download_file("http://example.com/file.txt")
        assert result == mock_response

    def test_download_file_no_internet(self, mocker):
        """Test that download_file returns None when offline."""
        mock_internet = mocker.patch("src.infrastructure.connectivity.Connectivity.verify_internet_access")
        mock_internet.return_value = False

        result = Connectivity.download_file("http://example.com/file.txt")
        assert result is None

    def test_download_file_timeout(self, mocker):
        """Test that download_file handles timeout."""
        import requests
        mock_internet = mocker.patch("src.infrastructure.connectivity.Connectivity.verify_internet_access")
        mock_get = mocker.patch("requests.get")
        mock_internet.return_value = True
        mock_get.side_effect = requests.Timeout()

        result = Connectivity.download_file("http://example.com/file.txt", timeout=5)
        assert result is None

    def test_download_file_too_large(self, mocker):
        """Test that download_file rejects files that are too large."""
        mock_internet = mocker.patch("src.infrastructure.connectivity.Connectivity.verify_internet_access")
        mock_internet.return_value = True
        mock_response = mocker.Mock()
        mock_response.headers.get.return_value = "10000000"  # 10MB
        mocker.patch("requests.get", return_value=mock_response)

        result = Connectivity.download_file("http://example.com/file.txt", max_size=1000)
        assert result is None

    def test_download_file_http_error(self, mocker):
        """Test that download_file handles HTTP errors."""
        import requests
        mock_internet = mocker.patch("src.infrastructure.connectivity.Connectivity.verify_internet_access")
        mock_get = mocker.patch("requests.get")
        mock_internet.return_value = True
        mock_get.side_effect = requests.HTTPError()

        result = Connectivity.download_file("http://example.com/file.txt")
        assert result is None

    def test_download_file_custom_timeout(self, mocker):
        """Test download_file with custom timeout."""
        mock_internet = mocker.patch("src.infrastructure.connectivity.Connectivity.verify_internet_access")
        mock_internet.return_value = True
        mock_response = mocker.Mock()
        mock_response.headers.get.return_value = "1000"
        mock_response.raise_for_status.return_value = None
        mock_get = mocker.patch("requests.get", return_value=mock_response)

        Connectivity.download_file("http://example.com/file.txt", timeout=60)
        mock_get.assert_called_once()
        assert mock_get.call_args[1]['timeout'] == 60


class TestConnectivityExtractZipContents:
    """Tests for Connectivity.extract_zip_contents method."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)
        yield
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_extract_zip_contents_success(self):
        """Test successful ZIP file extraction."""
        zip_path = self.temp_dir_path / "test.zip"
        extract_path = self.temp_dir_path / "extracted"

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file.txt", "content")

        result = Connectivity.extract_zip_contents(zip_path, extract_path)

        assert result is True
        assert extract_path.exists()
        assert (extract_path / "file.txt").exists()

    def test_extract_zip_contents_nonexistent_file(self):
        """Test extraction with non-existent ZIP file."""
        result = Connectivity.extract_zip_contents(
            Path("/nonexistent/file.zip"),
            Path("/some/extract/path")
        )
        assert result is False

    def test_extract_zip_contents_corrupt_zip(self):
        """Test extraction with corrupt ZIP file."""
        zip_path = self.temp_dir_path / "corrupt.zip"
        extract_path = self.temp_dir_path / "extracted"

        zip_path.write_text("not a zip file")

        result = Connectivity.extract_zip_contents(zip_path, extract_path)
        assert result is False

    def test_extract_zip_contents_creates_directory(self):
        """Test that extract_zip_contents creates target directory if needed."""
        zip_path = self.temp_dir_path / "test.zip"
        extract_path = self.temp_dir_path / "new_dir" / "sub_dir"

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file.txt", "content")

        result = Connectivity.extract_zip_contents(zip_path, extract_path)

        assert result is True
        assert extract_path.exists()

    def test_extract_zip_contents_io_error(self, mocker):
        """Test extraction handling of IOError."""
        mock_zipfile = mocker.patch("zipfile.ZipFile")
        mock_zipfile.side_effect = IOError("IO Error")

        result = Connectivity.extract_zip_contents(
            self.temp_dir_path / "test.zip",
            self.temp_dir_path / "extract"
        )
        assert result is False
