"""
Lo script in questione ha il compito di creare un ambiente virtuale in modo da 
isolare le dipendenze e mantenere il sistema pulito
"""

import os
import subprocess
import sys


def create_venv(env_name=".venv"):
    env_path = os.path.join(os.getcwd(), env_name)

    print("Creazione dell'ambiente virtuale....")
    subprocess.check_call([sys.executable, "-m", "venv", env_path])

    # Attivazione dell'ambiente virtuale
    if os.name == "nt":     # Windows
        activate_cmd = f"{env_path}\\Scripts\\activate"
        pip_path = f"{env_path}\\Scripts\\pip"
    else:       # MacOs e Linux
        activate_cmd = f"source {env_path}/bin/activate"
        pip_path = f"{env_path}/bin/pip"

    print(f"Ambiente virtuale creato in: {env_path}")
    print(f"\nPer attivarlo esegui:\n{activate_cmd}\n")

    return pip_path

def install_requirements(pip_path, requirements_file="requirements.txt"):
    if os.path.exists(requirements_file):
        print(f"Installazione pacchetti da {requirements_file}")
        subprocess.check_call([pip_path, "install", "-r", requirements_file])
    else:
        print("Nessun requirements.txt trovato, ambiente creato senza pacchetti.")


if __name__ == "__main__":
    pip_exec = create_venv(".venv")
    install_requirements(pip_exec)