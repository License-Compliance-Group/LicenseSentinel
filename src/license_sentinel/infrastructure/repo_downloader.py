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
from ..entities.abstract_repo_downloader import AbstractRepoDownloader
from .logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("repo_downloader", logging.INFO)


URL_REGEX = re.compile(
    r'^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/[^\s]*)?$')


GITHUB_REPO_REGEX = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE
)

GITLAB_REPO_REGEX = re.compile(
    r"^https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE
)


class _RepoDownloadError(Exception):
    """Exception raised when repository download fails."""


class RepoDownloader(AbstractRepoDownloader):
    """Download Git repositories as ZIP archives from hosting providers.

    Supports GitHub and GitLab. Downloads a specific branch without full Git history.

    Typical usage:
        downloader = _RepoDownloader()
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
        output_path: Path,
        branch: str = "main",
    ) -> Dict[str, bool]:
        """Download multiple repository branches as ZIP files.

        Args:
            repo_urls: Dictionary mapping package names to repository URLs
            (e.g., {"numpy": "https://github.com/numpy/numpy"}).
            output_path: Directory path where the ZIP files will be saved.
            branch: Branch name to download for each repository (e.g., "main", "master", "develop").

        Returns:
            Dict mapping package names to booleans indicating if the download
            succeeded (True) or failed (False).

        Raises:
            RepoDownloadError: If validation fails or an unrecoverable error
            occurs for any repository.
        """
        results: dict[str, bool] = {}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = []

        # Step 1: Resolve output directory to be inside project root
        output_dir = self._resolve_output_dir(output_path)

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
            provider: Optional[str] = None
            if GITHUB_REPO_REGEX.match(repo_url):
                provider = 'github'
            elif GITLAB_REPO_REGEX.match(repo_url):
                provider = 'gitlab'

            if not provider:
                LOGGER.warning(
                    "Unsupported repository URL (%s) for package %s", repo_url, pkg)
                results[pkg] = False
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
                LOGGER.critical(
                    "This should never happen - Error in parsing the download URL\
                    for package: %s (provider: %s, repo_url: %s)",
                    pkg, provider, repo_url
                )
                raise _RepoDownloadError(f"Unsupported provider: {provider}")

            # Step 5: Download and save
            LOGGER.info("Downloading %s branch '%s' to %s",
                        normalized_url, branch, output_dir)
            task = loop.run_in_executor(self.executor, self._download_zip,
                                        pkg, zip_url, output_dir)
            tasks.append((pkg, repo_url, task))

        # Wait for all downloads
        for pkg, repo_url, task in tasks:
            try:
                results[pkg] = loop.run_until_complete(task)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                LOGGER.error("Download failed for %s: %s - %s", pkg, repo_url, exc)  # noqa
                results[pkg] = False

        loop.close()
        return results

    # pylint: disable=R0912
    def _download_zip(self, pkg: str, url: str, output_path: Path) -> bool:
        """Download a file from URL and save to disk with streaming.

        Args:
            pkg: Package name.
            url: URL to download.
            output_path: Directory path where file will be saved.

        Returns:
            True if successful, False otherwise.
        """
        output_file = output_path / f"{pkg}.zip"

        # Prepare list of URLs to try (main branch, then fallback to master)
        urls_to_try = [url]
        if "/refs/heads/main" in url:
            fallback_url = url.replace(
                "/refs/heads/main", "/refs/heads/master")
            urls_to_try.append(fallback_url)

        for attempt_url in urls_to_try:
            try:
                response = requests.get(
                    attempt_url, timeout=self.timeout, stream=True)
                response.raise_for_status()

                with open(output_file, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            file.write(chunk)

                LOGGER.info("Successfully downloaded %s to %s (%d bytes)",
                            pkg, output_file, output_file.stat().st_size)
                return True

            except requests.exceptions.Timeout:
                LOGGER.error("Request timeout after %d seconds for %s",
                             self.timeout, attempt_url)
            except requests.exceptions.ConnectionError as exc:
                LOGGER.error("Connection error for %s: %s", attempt_url, exc)
            except requests.exceptions.HTTPError as exc:
                status_code = exc.response.status_code  # if exc.response else "unknown"
                # Log the error before deciding what to do
                LOGGER.error("HTTP %s for %s:\n-> %s", status_code, attempt_url, exc)  # noqa
                if status_code == 404:
                    if attempt_url != urls_to_try[-1]:
                        LOGGER.warning(
                            "HTTP 404 for %s, retry with fallback branch(master)", attempt_url)
                        continue  # Explicitly continue to next attempt
                    LOGGER.error(
                        "HTTP 404 for %s, all fallback attempts failed.", attempt_url)
                else:
                    LOGGER.error(
                        "HTTP error %s for %s, stopping attempts.", status_code, attempt_url)

            except OSError as exc:
                LOGGER.error("File I/O error writing to %s: %s",
                             output_file, exc)

            # Clean up partial file on failure before next attempt
            if output_file.exists():
                try:
                    output_file.unlink()
                    LOGGER.debug(
                        "Cleaned up partial download: %s", output_file)
                except OSError as exc:
                    LOGGER.warning(
                        "Failed to clean up partial download: %s (%s)", output_file, exc)

        # All attempts failed
        LOGGER.error("All download attempts failed for package: %s", pkg)
        return False

    def _resolve_output_dir(self, output_path: str | Path) -> Path:
        """Return a Path inside the project root and ensure it exists.

        Accepts both "tmp/repo_downloads" and "/tmp/repo_downloads" and makes
        them relative to the project root (two levels up from this file).
        """
        output_dir = Path(output_path)
        project_root = Path(__file__).resolve().parents[3]

        if output_dir.is_absolute():
            if output_dir.is_relative_to(project_root):
                output_dir = output_dir.relative_to(project_root)
            else:
                # Not within project root, treat as relative name by stripping leading slashes
                output_dir = Path(str(output_dir).lstrip('/\\'))

        # Now output_dir is always relative to project_root
        resolved_output_dir = project_root / output_dir

        if not resolved_output_dir.exists():
            resolved_output_dir.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Download directory created: %s", resolved_output_dir)
        else:
            LOGGER.warning(
                "Download directory already exists: %s", resolved_output_dir)

        return resolved_output_dir

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically cleanup executor."""
        self.executor.shutdown(wait=True)

    def download_repo(self, repo_url: str, pkg_name, branch: str, output_path: Path) -> bool:
        """Download a single repository branch as a ZIP file.
        """

        # Delegate to the batch downloader; it will create directories as needed.
        results = self.download_repos(
            repo_urls={pkg_name: repo_url},
            output_path=output_path,
            branch=branch
        )

        return bool(results.get(pkg_name))
