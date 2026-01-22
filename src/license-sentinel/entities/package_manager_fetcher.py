"""Abstract class for package data retrieval.
Raises: NotImplementedError - this is an abstract class, it is not
intended to be used directly."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AbstractPackageManagerFetcher(ABC):

    """Interfaccia per ottenere metadata/package info da PyPI."""

    # This class is intended for a single purpose.
    # pylint: disable=too-few-public-methods

    @abstractmethod
    def get_source_links(
        self,
        packages_names: List[str],
        timeout: int = 10
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Restituisce per ogni package una mappa 
        {'license': str|None, 'link': str|None}.
        """
        raise NotImplementedError
