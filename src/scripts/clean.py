"""
Script per la pulizia del progetto:
- Rimuove file temporanei, cache, metadati e log
- Può eliminare l'ambiente virtuale .venv
"""

import shutil
import sys
import os
from pathlib import Path

# Root del progetto (2 livelli sopra la cartella scripts)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_DIR = PROJECT_ROOT / ".venv"

PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.log",
    "**/*.egg-info",
]

def is_in_venv():
    """Rileva se il processo Python corrente è dentro un venv"""
    return sys.prefix != sys.base_prefix

def clean():
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
            except Exception as e:
                print(f" ! Errore su {path}: {e}")

    print("\nPulizia completata.")

def clean_venv(remove_all: bool = True):
    """
    Pulizia dell'ambiente virtuale .venv
    - Se remove_all=True → elimina tutta la cartella .venv
    - Se remove_all=False → esegue solo la pulizia del progetto (cache, log, ecc.)
    """
    if is_in_venv():
        print("ATTENZIONE!!! Sei dentro un ambiente virtuale attivo.")
        print("\nEsegui 'deactivate' nella shell prima di cancellare .venv.")
        return

    if not VENV_DIR.exists():
        print("Nessun ambiente virtuale .venv trovato.")
        clean()
        return
    
    if remove_all:
        try:
            shutil.rmtree(VENV_DIR)
            print("\nAmbiente virtuale .venv rimosso completamente.")
        except Exception as e:
            print(f"Errore nella rimozione di .venv: {e}")
            clean()
    else:
        clean()

if __name__ == "__main__":
    clean_venv()
