from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AbstractPackageManagerFetcher(ABC):
    """Interfaccia per ottenere metadata/package info da PyPI."""

    @abstractmethod
    def get_source_links(
        self,
        packages_names: List[str],
        timeout: int = 10
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Restituisce per ogni package una mappa {'license': str|None, 'link': str|None}.
        """
        raise NotImplementedError
