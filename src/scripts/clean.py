"""
Script di pulizia del progetto:
- Rimuove cache/log/artefatti noti
- Può eliminare un virtualenv (opt-in)
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Assume standard practice: file ran from project root.
PROJECT_ROOT = Path.cwd()
DEFAULT_VENV = ".venv"

PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.log",
    "**/*.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    ".coverage",
    "coverage.xml",
]


def is_in_venv() -> bool:
    """Rileva se il processo Python corrente è dentro un venv."""
    return sys.prefix != sys.base_prefix


def clean() -> None:
    """
    Remove all files defined in the pattern.
    """

    # No logger - scripts are allowed no internal imports.
    print("Pulizia del progetto in corso...")

    for pattern in PATTERNS:
        for path in PROJECT_ROOT.rglob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                    print(f" - File rimosso: {path}")
                elif path.is_dir():
                    shutil.rmtree(path)
                    print(f" - Cartella rimossa: {path}")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f" ! Errore su {path}: {exc}")

    print("Pulizia completata.")


def remove_venv(venv_dir: Path) -> None:
    """Removes the virtual environment.
    Warns the user if they're attempting to remove a currently
    active one.

    Args:
        venv_dir (Path): The path to wupe.
    """
    if is_in_venv():
        print("ATTENZIONE: sei dentro un ambiente virtuale attivo.")
        print("Esegui 'deactivate' nella shell prima di cancellare il venv.")
        return

    try:
        venv_dir.relative_to(PROJECT_ROOT)
    except ValueError:
        print(f"Percorso venv non valido (fuori dal progetto): {venv_dir}")
        return

    if not venv_dir.exists():
        print(f"Nessun ambiente virtuale trovato in {venv_dir}.")
        return

    try:
        shutil.rmtree(venv_dir)
        print(f"Ambiente virtuale rimosso: {venv_dir}")
    except IOError as exc:
        print(f"Errore nella rimozione di {venv_dir}: {exc}")


def parse_args() -> argparse.Namespace:
    """Binds command line arguments to functions.

    Returns:
        argparse.Namespace: The bindings' namespace.
    """
    parser = argparse.ArgumentParser(
        description="Pulisce cache/log e opzionalmente elimina il virtualenv."
    )
    parser.add_argument(
        "--remove-venv",
        action="store_true",
        help="Elimina anche l'ambiente virtuale (default: no).",
    )
    parser.add_argument(
        "--venv-name",
        default=DEFAULT_VENV,
        help="Nome/cartella del virtualenv da rimuovere (default: .venv).",
    )
    return parser.parse_args()


def main() -> None:
    """The main function of the script.
    Will be called by CI/CD pipelines.
    """
    args = parse_args()
    clean()
    if args.remove_venv:
        venv_dir = PROJECT_ROOT / args.venv_name
        remove_venv(venv_dir)


if __name__ == "__main__":
    main()
