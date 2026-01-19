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

    # Directory dello script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Root del progetto (due livelli sopra)
    project_root = os.path.abspath(os.path.join(script_dir, "../.."))

    # Percorso output SBOM
    output_file = os.path.join(project_root, "sbom.spdx.json")

    # Percorso interprete Python attuale
    python_path = sys.executable
    print(f"Interprete Python rilevato: {python_path}")

    # Comando Syft: analizza l'ambiente Python reale
    command = [
        "syft",
        f"python:{python_path}",
        "-o", "spdx-json"
    ]

    print("Eseguo comando Syft:", " ".join(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=600
        )
    except subprocess.TimeoutExpired:
        print("Errore: timeout durante l'esecuzione di Syft.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("Errore durante la generazione della SBOM:")
        print(e.stderr or e.stdout)
        sys.exit(1)

    # Parsing JSON
    try:
        sbom_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Errore: l'output di Syft non è un JSON valido.")
        sys.exit(1)

    # Scrittura file SBOM
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(sbom_data, f, indent=4)
    except OSError as e:
        print(f"Errore nella scrittura del file SBOM: {e}")
        sys.exit(1)

    print(f"SBOM generata con successo: {output_file}")


if __name__ == "__main__":
    generate_sbom()
