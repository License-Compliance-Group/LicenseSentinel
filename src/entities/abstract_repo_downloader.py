"""
Abstract repository downloader interface.

This module defines `AbstractRepoDownloader`, a small abstract interface that
declares the contract for components that download source repositories (usually
as zip archives) for a list of packages.

"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional


class AbstractRepoDownloader(ABC):
    """Interface for downloading repositories (package -> zip)."""

    @abstractmethod
    def download_repo(self, repo_url: str, pkg_name: str, branch: str, output_path: Path) -> bool:
        """Download a single repository archive (zip) for a given branch (synchronous)."""
        raise NotImplementedError

    @abstractmethod
    def download_repos(
        self,
        repo_urls: Dict[str, Optional[str]],
        output_path: str,
        branch: str = "main",
    ) -> Dict[str, bool]:
        """Download multiple repositories (asynchronous).

        Args:
            repo_urls: Mapping from package name to repository URL. A value of
                       `None` indicates no repository URL is known for that package.
            output_path: Destination directory (string). Implementations should
                         create it if needed and may accept relative paths.
            branch: Default branch name to try when downloading repositories.

        Returns:
            Mapping from package name -> boolean indicating success (True) or
            failure (False) for each requested package.

        Implementation expectations / recommendations:
        - Perform downloads in a way that does not block the orchestrator for long
          (use a thread pool, async IO, or external worker), but preserve the
          synchronous return contract (i.e., return a completed mapping).
        - Where possible, attempt sensible branch fallbacks (for example,
          try `main`, then `master` on 404).
        - Do not raise on per-repo failures; indicate failures using the returned bools.


        Example return value:
            {"requests": True, "nonexistent": False, "no-url": False}
        """
        raise NotImplementedError
