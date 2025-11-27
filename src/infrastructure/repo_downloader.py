"""Repository downloader module.

Downloads source code from Git hosting providers (GitHub, GitLab) as ZIP archives.
Uses a simple HTTP-based approach without requiring full Git history.
"""
import logging
import re
from pathlib import Path
from typing import Optional

import requests
from infrastructure.logger_formatter import LoggerFormatter

logger = LoggerFormatter.initialize("repo_downloader", logging.INFO)

GITHUB_REPO_REGEX = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE
)

GITLAB_REPO_REGEX = re.compile(
    r"^https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE
)


class RepoDownloadError(Exception):
    """Exception raised when repository download fails."""


class RepoDownloader:
    """Download Git repositories as ZIP archives from hosting providers.

    Supports GitHub and GitLab. Downloads a specific branch without full Git history.

    Typical usage:
        downloader = RepoDownloader()
        downloader.download_repo(
            repo_url="https://github.com/numpy/numpy",
            branch="main",
            output_path="downloads/numpy-main.zip"
        )
    """

    def __init__(self, timeout: int = 30, chunk_size: int = 8192):
        """Initialize the downloader.

        Args:
            timeout: HTTP request timeout in seconds.
            chunk_size: Size of chunks when streaming download (bytes).
        """
        self.timeout = timeout
        self.chunk_size = chunk_size

    def download_repo(
        self,
        repo_url: str,
        branch: str,
        output_path: str,
        provider: Optional[str] = None
    ) -> bool:
        """Download a repository branch as a ZIP file.

        Args:
            repo_url: Repository URL (e.g., https://github.com/owner/repo).
            branch: Branch name to download (e.g., main, master, develop).
            output_path: Path where the ZIP will be saved.
            provider: Optional provider hint ('github' or 'gitlab'). Auto-detected if None.

        Returns:
            True if download succeeded, False otherwise.

        Raises:
            RepoDownloadError: If validation fails or unrecoverable error occurs.
        """
        # Validate and detect provider
        if provider is None:
            provider = self._detect_provider(repo_url)

        if not provider:
            raise RepoDownloadError(f"Unsupported repository URL: {repo_url}")

        # Normalize URL (remove trailing slash, .git suffix)
        repo_url = self._normalize_url(repo_url)

        # Construct download URL
        zip_url = self._build_zip_url(repo_url, branch, provider)

        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Download and save
        logger.info("Downloading %s branch '%s' to %s", repo_url, branch, output_path)
        return self._download_file(zip_url, output_file)

    def _detect_provider(self, repo_url: str) -> Optional[str]:
        """Detect the Git hosting provider from URL.

        Args:
            repo_url: Repository URL.

        Returns:
            'github', 'gitlab', or None if unrecognized.
        """
        if GITHUB_REPO_REGEX.match(repo_url):
            return 'github'
        if GITLAB_REPO_REGEX.match(repo_url):
            return 'gitlab'
        return None

    def _normalize_url(self, repo_url: str) -> str:
        """Normalize repository URL by removing .git suffix and trailing slashes.

        Args:
            repo_url: Repository URL.

        Returns:
            Normalized URL.
        """
        url = repo_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        return url

    def _build_zip_url(self, repo_url: str, branch: str, provider: str) -> str:
        """Construct the ZIP download URL for the given provider.

        Args:
            repo_url: Normalized repository URL.
            branch: Branch name.
            provider: 'github' or 'gitlab'.

        Returns:
            Full URL to download the ZIP archive.

        Raises:
            RepoDownloadError: If provider is unsupported.
        """
        if provider == 'github':
            return f"{repo_url}/archive/refs/heads/{branch}.zip"
        if provider == 'gitlab':
            # GitLab uses project path encoding in URL
            return f"{repo_url}/-/archive/{branch}/{branch}.zip"

        raise RepoDownloadError(f"Unsupported provider: {provider}")

    def _download_file(self, url: str, output_path: Path) -> bool:
        """Download a file from URL and save to disk with streaming.

        Args:
            url: URL to download.
            output_path: Path object where file will be saved.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Stream download to handle large files efficiently
            with open(output_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # filter out keep-alive chunks
                        file.write(chunk)

            logger.info("Successfully downloaded to %s (%d bytes)",
                       output_path, output_path.stat().st_size)
            return True

        except requests.exceptions.Timeout:
            logger.error("Request timeout after %d seconds for %s", self.timeout, url)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP error %s: %s", response.status_code, exc)
        except OSError as exc:
            logger.error("File I/O error writing to %s: %s", output_path, exc)

        # Clean up partial file on failure
        if output_path.exists():
            try:
                output_path.unlink()
                logger.info("Cleaned up partial download: %s", output_path)
            except OSError:
                pass

        return False


# Backward compatibility - GitHub-only static method
def download_github_zip(repo_url: str, branch: str, output: str, timeout: int = 30) -> bool:
    """Download a GitHub repository as ZIP (legacy function).

    Args:
        repo_url: GitHub repository URL.
        branch: Branch name.
        output: Output file path.
        timeout: Request timeout in seconds.

    Returns:
        True if successful, False otherwise.
    """
    logger.warning("download_github_zip is deprecated; use RepoDownloader.download_repo instead")
    downloader = RepoDownloader(timeout=timeout)
    try:
        return downloader.download_repo(repo_url, branch, output, provider='github')
    except RepoDownloadError as exc:
        logger.error("Download failed: %s", exc)
        return False
