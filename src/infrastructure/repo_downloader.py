"""Repository downloader module.

Downloads source code from Git hosting providers (GitHub, GitLab) as ZIP archives.
Uses a simple HTTP-based approach without requiring full Git history.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import re
from pathlib import Path
from typing import Dict, Optional

import requests
from infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("repo_downloader", logging.INFO)


URL_REGEX = re.compile(
    r'^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/[^\s]*)?$')


GITHUB_REPO_REGEX = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE
)

GITLAB_REPO_REGEX = re.compile(
    r"^https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE
)


class _RepoDownloadError(Exception):
    """Exception raised when repository download fails."""


class _RepoDownloader:
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
        self.executor = ThreadPoolExecutor()

    def download_repos(
        self,
        repo_urls: Dict[str, str | None],
        output_path: str,
        branch: str = "main",
        provider: Optional[str] = None
    ) -> Dict[str, bool]:
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
        results: dict[str, bool] = {}
        loop = asyncio.get_event_loop()
        tasks = []

        # Step 1: Resolve output directory relative to project root if it's a relative path
        output_dir = Path(output_path)
        if not output_dir.is_absolute():
            # Make it relative to project root (1 level up from this file)
            project_root = Path(__file__).resolve().parents[1]
            output_dir = project_root / output_dir

        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Download directory created: %s", output_dir)
        else:
            LOGGER.info("Download directory exists: %s", output_dir)

        for pkg, repo_url in repo_urls.items():

            if repo_url is None or repo_url.strip() == "":
                LOGGER.warning("Empty repository URL for package: %s", pkg)
                results[pkg] = False
                continue
            if not URL_REGEX.match(repo_url):
                LOGGER.warning("Invalid repository URL: %s", repo_url)
                results[pkg] = False
                continue

            # Step 2: Detect provider if not specified
            if provider is None:
                if GITHUB_REPO_REGEX.match(repo_url):
                    provider = 'github'
                elif GITLAB_REPO_REGEX.match(repo_url):
                    provider = 'gitlab'

            if not provider:
                LOGGER.warning("Unsupported repository URL: %s", repo_url)
                results[repo_url] = False
                continue

            # Step 3: Normalize URL (remove trailing slash, .git suffix)
            normalized_url = repo_url.rstrip('/')
            if normalized_url.endswith('.git'):
                normalized_url = normalized_url[:-4]

            # Step 4: Construct download URL based on provider
            if provider == 'github':
                zip_url = f"{normalized_url}/archive/refs/heads/{branch}.zip"
            elif provider == 'gitlab':
                zip_url = f"{normalized_url}/-/archive/{branch}/{branch}.zip"
            else:
                raise _RepoDownloadError(f"Unsupported provider: {provider}")
            print("---------------------->"+zip_url)
            # Step 5: Download and save
            LOGGER.info("Downloading %s branch '%s' to %s",
                        normalized_url, branch, output_path)
            # ERRORE VIENE PASSATO IL PATH MA DOWNLOAD_ZIP LO USA PER APRIRE IL FILE E QUINDI TUTTI I DOWNLOAD
            # SONO FILE ZIP DI NOME UGUALI ALL'OUTPUT PATH (SI SOVRASCRIVONO)
            task = loop.run_in_executor(
                self.executor, self._download_zip, pkg, zip_url, Path(output_path))
            tasks.append((pkg, repo_url, task))

        # Wait for all downloads
        for pkg, repo_url, task in tasks:
            try:
                results[pkg] = loop.run_until_complete(task)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                LOGGER.error("Download failed for %s: %s - %s",
                             pkg, repo_url, exc)
                results[pkg] = False

        loop.close()
        return results

    def _download_zip(self, pkg: str, url: str, output_path: Path) -> bool:
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
            output_path = output_path / f"{pkg}.zip"

            # Stream download to handle large files efficiently
            with open(output_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # filter out keep-alive chunks
                        file.write(chunk)

            LOGGER.info("Successfully downloaded to %s (%d bytes)",
                        output_path, output_path.stat().st_size)
            return True

        except requests.exceptions.Timeout:
            LOGGER.error("Request timeout after %d seconds for %s",
                         self.timeout, url)
        except requests.exceptions.ConnectionError as exc:
            LOGGER.error("Connection error: %s", exc)
        except requests.exceptions.HTTPError as exc:
            LOGGER.error("HTTP error %s: %s", response.status_code, exc)
        except OSError as exc:
            LOGGER.error("File I/O error writing to %s: %s", output_path, exc)

        # Clean up partial file on failure
        if output_path.exists():
            try:
                output_path.unlink()
                LOGGER.info("Cleaned up partial download: %s", output_path)
            except OSError:
                pass

        return False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically cleanup executor."""
        self.executor.shutdown(wait=True)
        return False


# Standalone convenience function
def download_repos(repo_urls: Dict[str, str | None],
                   branch: str,
                   output: str,
                   timeout: int = 30) -> Dict[str, bool]:
    """Download multiple repositories as ZIP files.

    Convenience function that handles RepoDownloader lifecycle automatically.
    I don't know ho to do private classes. I don't know if this is messy.

    Args:
        repo_urls: Dictionary mapping repository names to URLs.
        branch: Branch name to download (e.g., main, master).
        output: Output directory path where ZIPs will be saved.
        timeout: Request timeout in seconds.

    Returns:
        Dictionary mapping pkg_name -> bool (success/failure for each download).

    Example:
        results = download_repos(
            repo_urls={"numpy": "https://github.com/numpy/numpy",
                       "requests": "https://github.com/requests/requests"},
            branch="main",
            output="downloads"
        )
    """
    with _RepoDownloader(timeout=timeout) as downloader:
        return downloader.download_repos(
            repo_urls=repo_urls,
            output_path=output,
            branch=branch
        )
