import subprocess
import sys
import os
import json

def generate_sbom():
    print("Generazione SBOM in corso...")

    # Directory dove si trova questo script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Root del progetto (due livelli sopra)
    project_root = os.path.abspath(os.path.join(script_dir, "../.."))

    # Percorso del file SBOM nella root del progetto
    output_file = os.path.join(project_root, "sbom.spdx.json")

    # Comando Syft (senza redirezione, così possiamo catturare l'output)
    command = ["syft", project_root, "-o", "spdx-json"]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("Errore durante la generazione della SBOM:")
        print(e.stderr)
        sys.exit(1)

    # Parsing del JSON prodotto da Syft
    try:
        sbom_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Errore: l'output di Syft non è un JSON valido.")
        sys.exit(1)

    # Scrittura del JSON formattato
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sbom_data, f, indent=4)

    print(f"SBOM generata con successo e formattata: {output_file}")

if __name__ == "__main__":
    generate_sbom()

