from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional


class AbstractRepoDownloader(ABC):
    """Interfaccia per scaricare repo come zip."""

    @abstractmethod
    def download_repo(self, repo_url: str, branch: str, output_path: Path) -> bool:
        """Scarica singolo repo (branch) -> salva file -> ritorna True/False."""
        raise NotImplementedError

    @abstractmethod
    def download_repos(
        self,
        repo_urls: Dict[str, Optional[str]],
        output_path: str,
        branch: str = "main",
    ) -> Dict[str, bool]:
        """
        Scarica più repo in parallelo.
        Input: mapping package_name -> repo_url (repo_url può essere None).
        Return: mapping package_name -> success(bool).
        """
        raise NotImplementedError
