import subprocess
import sys
import os
import json
import shutil


def generate_sbom():
    print("Generazione SBOM in corso...\n")

    # Verifica che syft sia disponibile
    if shutil.which("syft") is None:
        print("Errore: 'syft' non è installato o non è nel PATH.")
        sys.exit(1)

    # Directory dove si trova questo script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Root del progetto (due livelli sopra)
    project_root = os.path.abspath(os.path.join(script_dir, "../.."))

    if not os.path.isdir(project_root):
        print(f"Errore: root del progetto non trovata: {project_root}")
        sys.exit(1)

    # Percorso del file SBOM
    output_file = os.path.join(project_root, "sbom.spdx.json")

    # Copia il file requirements-dev.txt nella root
    requirements_src = os.path.join(project_root, "src/requirements-dev.txt")
    requirements_dst = os.path.join(project_root, "requirements-dev.txt")

    try:
        shutil.copy(requirements_src, requirements_dst)
        print(f"Copiato {requirements_src} → {requirements_dst}")
    except Exception as e:
        print(f"Errore durante la copia del file requirements: {e}")
        sys.exit(1)

    # Comando Syft: analizza l'intero progetto (un solo input!)
    command = [
        "syft",
        project_root,
        "-o", "spdx-json",
        "--exclude", "**/__pycache__/**",
        "--exclude", "**/.github/**",
        "--exclude", "**/tmp/**"
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=300
        )
    except subprocess.TimeoutExpired:
        print("Errore: timeout durante l'esecuzione di Syft.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("Errore durante la generazione della SBOM:")
        print(e.stderr or e.stdout)
        sys.exit(1)

    # Parsing del JSON prodotto da Syft
    try:
        sbom_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Errore: l'output di Syft non è un JSON valido.")
        sys.exit(1)

    # Scrittura del JSON formattato
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(sbom_data, f, indent=4)
    except OSError as e:
        print(f"Errore nella scrittura del file SBOM: {e}")
        sys.exit(1)

    print(f"SBOM generata con successo: {output_file}")
    print("Directory analizzata da Syft:", project_root)


if __name__ == "__main__":
    generate_sbom()
