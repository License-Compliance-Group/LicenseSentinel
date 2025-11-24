#!/usr/bin/env python3
"""
Static analysis per verificare che i layer del progetto LicenseSentinel
rispettino le dipendenze corrette.
"""

import ast
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT                 

# Mappa layer → cartella reale
LAYER_PATHS = {
    "Entities": SRC_ROOT / "Entities",
    "Infrastructure": SRC_ROOT / "Infrastructure",
    "Analyzer": SRC_ROOT / "Analyzer",
    "scripts": SRC_ROOT / "scripts",
}

# Regole vere del progetto
LAYER_RULES = {
    "Entities": set(),  
    "Infrastructure": {"Entities"},
    "Analyzer": {"Entities", "Infrastructure"},
    "scripts": set(), 
}


def detect_layer(file_path: Path) -> str | None:
    """Determina a quale layer appartiene un file."""
    for layer, folder in LAYER_PATHS.items():
        try:
            file_path.relative_to(folder)
            return layer
        except ValueError:
            continue
    return None


def extract_imports(file_path: Path) -> list[tuple[str, int]]:
    """
    Estrae tutti gli import di livello 1 dal file.
    Restituisce: [(modulo, linea), ...]
    """
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module, node.lineno))

    return imports


def classify_import(module: str) -> str | None:
    """
    Riconosce se un import appartiene a un layer del progetto.
    """
    parts = module.split(".")

    if len(parts) >= 2 and parts[0] == "src":
        layer = parts[1]
    else:
        layer = parts[0]

    return layer if layer in LAYER_RULES else None


def check_file(file_path: Path, layer: str):
    """Verifica le regole per un singolo file."""
    violations = []
    imports = extract_imports(file_path)

    for module, line in imports:
        imported_layer = classify_import(module)

        # Import proveniente da una libreria esterna → OK
        if imported_layer is None:
            continue

        # ENTITIES → nessun import di moduli del progetto
        if layer == "Entities":
            violations.append(
                f"[Entities violation] {file_path} (line {line}) "
                f"importa {module}, ma Entities deve essere privo di import del progetto."
            )
            continue

        # scripts non devono essere importate da nessuno
        if imported_layer == "scripts":
            violations.append(
                f"[Scripts violation] {file_path} (line {line}) "
                f"importa {module}, ma la cartella 'scripts' non può essere importata."
            )
            continue

        # regola generale dei layer
        allowed = LAYER_RULES[layer]
        if imported_layer not in allowed and imported_layer != layer:
            violations.append(
                f"[Layer violation] {file_path} (line {line}) "
                f"({layer}) → importa {module} ({imported_layer}) NON PERMESSO"
            )

    return violations


def main():
    print("Controllo statico dei livelli...")

    all_violations = []

    for file_path in SRC_ROOT.rglob("*.py"):
        layer = detect_layer(file_path)
        if not layer:
            continue
        all_violations.extend(check_file(file_path, layer))

    if not all_violations:
        print("Nessuna violazione trovata.")
        sys.exit(0)

    print("\nViolazioni trovate:\n")
    for v in all_violations:
        print(" - " + v)

    sys.exit(1)


if __name__ == "__main__":
    main()
