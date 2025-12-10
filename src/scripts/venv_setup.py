"""Crea un ambiente virtuale e installa le dipendenze del progetto."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = ".venv"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "src" / "requirements.txt"
DEFAULT_DEV_REQUIREMENTS = PROJECT_ROOT / "src" / "requirements-dev.txt"


def create_venv(env_name: str = DEFAULT_ENV, recreate: bool = False) -> Path:
    """Create a virtual environment and return its pip executable path."""
    env_path = PROJECT_ROOT / env_name

    if recreate and env_path.exists():
        shutil.rmtree(env_path)

    print("Creazione dell'ambiente virtuale…")
    subprocess.check_call([sys.executable, "-m", "venv", str(env_path)])

    pip_name = "pip.exe" if os.name == "nt" else "pip"
    pip_path = env_path / ("Scripts" if os.name == "nt" else "bin") / pip_name

    print(f"Ambiente virtuale creato in: {env_path}")
    return pip_path


def install_requirements(
    pip_path: Path,
    requirements_file: Path = DEFAULT_REQUIREMENTS,
    dev_requirements_file: Path = DEFAULT_DEV_REQUIREMENTS,
    with_dev: bool = True,
) -> None:
    """Install project (and optionally dev) requirements into the venv."""
    if requirements_file.exists():
        print(f"Installazione pacchetti da {requirements_file}")
        subprocess.check_call([str(pip_path), "install", "-r", str(requirements_file)])
    else:
        print(f"Nessun {requirements_file.name} trovato, salto installazione pacchetti.")

    if with_dev and dev_requirements_file.exists():
        print(f"Installazione pacchetti dev da {dev_requirements_file}")
        subprocess.check_call(
            [str(pip_path), "install", "-r", str(dev_requirements_file)]
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea un virtualenv e installa le dipendenze del progetto."
    )
    parser.add_argument("--env", default=DEFAULT_ENV, help="Nome/cartella del venv.")
    parser.add_argument(
        "--no-dev",
        action="store_true",
        help="Non installare i requisiti di sviluppo (requirements-dev).",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Se esiste, ricrea l'ambiente virtuale da zero.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    pip_exec = create_venv(env_name=args.env, recreate=args.recreate)
    install_requirements(
        pip_exec,
        requirements_file=DEFAULT_REQUIREMENTS,
        dev_requirements_file=DEFAULT_DEV_REQUIREMENTS,
        with_dev=not args.no_dev,
    )

