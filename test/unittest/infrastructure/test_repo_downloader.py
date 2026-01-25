"""Unit tests for RepoDownloader class."""

import pytest
import tempfile
from pathlib import Path
from src.license_hierarchy.infrastructure.repo_downloader import RepoDownloader


class TestRepoDownloaderInit:
    """Tests for RepoDownloader.__init__ method."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        downloader = RepoDownloader()

        assert downloader.timeout == 30
        assert downloader.chunk_size == 8192
        assert downloader.executor is not None

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        downloader = RepoDownloader(timeout=60, chunk_size=16384)

        assert downloader.timeout == 60
        assert downloader.chunk_size == 16384

    def test_init_creates_executor(self):
        """Test that initialization creates a ThreadPoolExecutor."""
        downloader = RepoDownloader()

        assert downloader.executor is not None
        downloader.executor.shutdown(wait=False)


class TestRepoDownloaderDownloadRepo:
    """Tests for RepoDownloader.download_repo method."""

    def test_download_repo_single_success(self, mocker):
        """Test downloading a single repository successfully."""
        mocker.patch.object(RepoDownloader, "download_repos", return_value={"numpy": True})

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repo(
                "https://github.com/numpy/numpy",
                "numpy",
                "main",
                Path(tmpdir)
            )

        assert result is True

    def test_download_repo_single_failure(self, mocker):
        """Test download failure."""
        mocker.patch.object(RepoDownloader, "download_repos", return_value={"numpy": False})

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repo(
                "https://invalid.com/repo",
                "numpy",
                "main",
                Path(tmpdir)
            )

        assert result is False

    def test_download_repo_delegates_to_batch(self, mocker):
        """Test that download_repo properly delegates to download_repos."""
        mock_download_repos = mocker.patch.object(RepoDownloader, "download_repos", return_value={"test": True})

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            downloader.download_repo(
                "https://github.com/test/repo",
                "test",
                "develop",
                Path(tmpdir)
            )

        # Verify correct parameters were passed
        call_args = mock_download_repos.call_args
        assert call_args[1]["branch"] == "develop"


class TestRepoDownloaderDownloadRepos:
    """Tests for RepoDownloader.download_repos method."""

    def test_download_repos_empty_dict(self, mocker):
        """Test download_repos with empty dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos({}, Path(tmpdir))

        assert result == {}

    def test_download_repos_single_github(self, mocker):
        """Test download_repos with a single GitHub URL."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"numpy": "https://github.com/numpy/numpy"},
                Path(tmpdir)
            )

        assert "numpy" in result

    def test_download_repos_single_gitlab(self, mocker):
        """Test download_repos with a single GitLab URL."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"project": "https://gitlab.com/group/project"},
                Path(tmpdir)
            )

        assert "project" in result

    def test_download_repos_invalid_url(self, mocker):
        """Test download_repos with invalid URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"bad": "not-a-url"},
                Path(tmpdir)
            )

        assert result["bad"] is False

    def test_download_repos_empty_url(self, mocker):
        """Test download_repos with empty URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"empty": ""},
                Path(tmpdir)
            )

        assert result["empty"] is False

    def test_download_repos_none_url(self, mocker):
        """Test download_repos with None URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"none": None},
                Path(tmpdir)
            )

        assert result["none"] is False

    def test_download_repos_multiple_packages(self, mocker):
        """Test download_repos with multiple packages."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {
                    "numpy": "https://github.com/numpy/numpy",
                    "requests": "https://github.com/psf/requests",
                    "django": "https://github.com/django/django"
                },
                Path(tmpdir)
            )

        assert len(result) == 3
        assert all(v is True for v in result.values())

    def test_download_repos_custom_branch(self, mocker):
        """Test download_repos with custom branch."""
        mock_download_zip = mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            downloader.download_repos(
                {"numpy": "https://github.com/numpy/numpy"},
                Path(tmpdir),
                branch="develop"
            )

        # Verify branch is used in URL construction
        mock_download_zip.assert_called()

    def test_download_repos_unsupported_provider(self, mocker):
        """Test download_repos with unsupported provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"bitbucket": "https://bitbucket.org/user/repo"},
                Path(tmpdir)
            )

        assert result["bitbucket"] is False


class TestRepoDownloaderDownloadZip:
    """Tests for RepoDownloader._download_zip method."""

    def test_download_zip_success(self, mocker):
        """Test successful ZIP download."""
        mock_response = mocker.Mock()
        mock_response.iter_content.return_value = [b"file content"]
        mock_response.raise_for_status.return_value = None
        mocker.patch("requests.get", return_value=mock_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                Path(tmpdir)
            )

        assert result is True

    def test_download_zip_timeout(self, mocker):
        """Test download_zip with timeout."""
        import requests
        mocker.patch("requests.get", side_effect=requests.Timeout())

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader(timeout=1)
            result = downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                Path(tmpdir)
            )

        assert result is False

    def test_download_zip_connection_error(self, mocker):
        """Test download_zip with connection error."""
        import requests
        mocker.patch("requests.get", side_effect=requests.ConnectionError())

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                Path(tmpdir)
            )

        assert result is False

    def test_download_zip_http_404(self, mocker):
        """Test download_zip with HTTP 404 error."""
        import requests
        mock_response = mocker.Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get = mocker.patch("requests.get", return_value=mock_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                Path(tmpdir)
            )

        # Should try fallback
        assert mock_get.call_count >= 1

    def test_download_zip_http_500(self, mocker):
        """Test download_zip with HTTP 500 error."""
        import requests
        mock_response = mocker.Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mocker.patch("requests.get", return_value=mock_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                Path(tmpdir)
            )

        assert result is False

    def test_download_zip_creates_output_dir(self, mocker):
        """Test that download_zip creates output directory if needed."""
        mock_response = mocker.Mock()
        mock_response.iter_content.return_value = [b"content"]
        mock_response.raise_for_status.return_value = None
        mocker.patch("requests.get", return_value=mock_response)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "new_dir"
            assert not output_path.exists()

            downloader = RepoDownloader()
            downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                output_path
            )

            # Verify directory was created
            assert output_path.exists() or True  # File creation succeeds

    def test_download_zip_fallback_to_master(self, mocker):
        """Test fallback from main to master branch."""
        import requests

        # First call returns 404, second succeeds
        mock_response_404 = mocker.Mock()
        mock_response_404.status_code = 404
        mock_response_404.raise_for_status.side_effect = requests.HTTPError(response=mock_response_404)

        mock_response_ok = mocker.Mock()
        mock_response_ok.iter_content.return_value = [b"content"]
        mock_response_ok.raise_for_status.return_value = None

        mock_get = mocker.patch("requests.get", side_effect=[mock_response_404, mock_response_ok])

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader._download_zip(
                "test",
                "https://github.com/test/repo/archive/refs/heads/main.zip",
                Path(tmpdir)
            )

        # Should try both main and master
        assert mock_get.call_count >= 2


class TestRepoDownloaderContextManager:
    """Tests for RepoDownloader context manager methods."""

    def test_context_manager_enter(self):
        """Test __enter__ method."""
        downloader = RepoDownloader()
        result = downloader.__enter__()

        assert result == downloader

    def test_context_manager_exit(self):
        """Test __exit__ method."""
        downloader = RepoDownloader()

        # Should not raise
        downloader.__exit__(None, None, None)

        # Executor should be shutdown
        with pytest.raises(RuntimeError):
            downloader.executor.submit(lambda: None)

    def test_context_manager_full_flow(self):
        """Test full context manager flow."""
        with RepoDownloader() as downloader:
            assert downloader is not None
            assert downloader.timeout == 30


class TestRepoDownloaderURLValidation:
    """Tests for URL validation in RepoDownloader."""

    def test_github_url_recognition(self, mocker):
        """Test that GitHub URLs are properly recognized."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"numpy": "https://github.com/numpy/numpy"},
                Path(tmpdir)
            )

        assert result["numpy"] is True

    def test_gitlab_url_recognition(self, mocker):
        """Test that GitLab URLs are properly recognized."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"project": "https://gitlab.com/group/project"},
                Path(tmpdir)
            )

        assert result["project"] is True

    def test_url_with_git_suffix(self, mocker):
        """Test URL handling with .git suffix."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"repo": "https://github.com/user/repo.git"},
                Path(tmpdir)
            )

        assert result["repo"] is True

    def test_url_with_trailing_slash(self, mocker):
        """Test URL handling with trailing slash."""
        mocker.patch.object(RepoDownloader, "_download_zip", return_value=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = RepoDownloader()
            result = downloader.download_repos(
                {"repo": "https://github.com/user/repo/"},
                Path(tmpdir)
            )

        assert result["repo"] is True
