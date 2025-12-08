from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List


class AbstractDepTreeBuilder(ABC):
    """Interfaccia per la costruzione dell'albero di dipendenze."""

    @abstractmethod
    def create_venv(self, path: str = "tmpvenv", force_recreate: bool = False) -> str:
        """Crea (o riusa) una venv e ritorna il path della 'bin' o 'Scripts'."""
        raise NotImplementedError

    @abstractmethod
    def install_packages(self, venv_bin: str, packages: List[str]) -> None:
        """Installa pacchetti nella venv fornita."""
        raise NotImplementedError

    @abstractmethod
    def get_tree_json(self, venv_bin: str) -> List[Dict]:
        """Esegue pipdeptree e ritorna il JSON dell'albero."""
        raise NotImplementedError

    @abstractmethod
    def build_map(self, tree_json: List[Dict]) -> Dict[str, List[str]]:
        """Converte il JSON in una mappa package -> [dependencies]."""
        raise NotImplementedError

    @abstractmethod
    def delete_venv(self, path: str) -> None:
        """Elimina il venv (cleanup)."""
        raise NotImplementedError
