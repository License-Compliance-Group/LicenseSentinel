"""
Script per la pulizia, che permette di rimuovere file temporanei, cache,
metadati e log
"""

import shutil 
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = PROJECT_ROOT / ".venv"

PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.log",
    "*.egg-info",
]

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
                    print(f" - Cartella rimossa {path}")
            except Exception as e:
                print(f" ! Errore su {path}: {e}")

    print("Pulizia completata. ")


def clean_venv(remove_all: bool = True):
    """
    Serve per pulire l'ambiente virtuale .venv
    - Se remove_all=True → elimina tutta la cartella .venv
    - Se remove_all=False → esegue solo la pulizia del progetto (cache, log, ecc.)
    """
    if not VENV_DIR.exists():
        print("Nessun ambiente virtuale .venv trovato.")
        return
    
    if remove_all:
        try:
            shutil.rmtree(VENV_DIR)
            print(f"Ambiente virtuale .venv rimosso completamente.")
        except Exception as e:
            print(f"Errore nella rimozione di .venv: {e}")
            clean()
    else:
        clean()


if __name__ == "__main__":
    clean_venv()