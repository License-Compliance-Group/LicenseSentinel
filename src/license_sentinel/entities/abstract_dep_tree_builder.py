"""Abstract class for future potential tree-building mechanisms.

    Raises:
        NotImplementedError: This is an abstract class.
        You are not intended to call it directly.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List


class AbstractDepTreeBuilder(ABC):
    """Interface for building the dependency tree of a package. (Dependency tree builder)"""

    @abstractmethod
    def create_venv(self, path: str = "tmpvenv", force_recreate: bool = False) -> str:
        """Create (or reuse) a virtual environment and return the path to 'bin' or 'Scripts'."""
        raise NotImplementedError

    @abstractmethod
    def install_packages(self, venv_bin: str, packages: List[str]) -> None:
        """Install packages in the provided virtual environment."""
        raise NotImplementedError

    @abstractmethod
    def get_tree_json(self, venv_bin: str) -> List[Dict]:
        """Run pipdeptree and return the JSON representation of the dependency tree."""
        raise NotImplementedError

    @abstractmethod
    def build_map(self, tree_json: List[Dict]) -> Dict[str, List[str]]:
        """Convert the JSON into a map package -> [dependencies]."""
        raise NotImplementedError

    @abstractmethod
    def delete_venv(self, path: str) -> None:
        """Delete the virtual environment (cleanup)."""
        raise NotImplementedError

    @abstractmethod
    def has_cycles(self, graph: Dict[str, List[str]]) -> bool:
        """Check if the dependency tree has cycles."""
        raise NotImplementedError
