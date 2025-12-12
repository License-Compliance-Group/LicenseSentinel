"""
Controllo statico dei layer del progetto LicenseSentinel.

Regole implementate:

- entities:
    - non può importare nessun altro layer del progetto
    - può importare solo librerie esterne

- infrastructure:
    - può importare solo entities

- analyzer:
    - può importare entities e infrastructure

- interface:
    - può importare entities, infrastructure e analyzer

- scripts:
    - non deve essere importato da nessun altro layer

Il controllo:
- considera solo file Python dentro package (cartelle con __init__.py),
- esclude directory temporanee come .venv, __pycache__, .git, tmpvenv,
- fallisce con exit code 1 se trova violazioni (utile per CI).


Static layer checking of the project.

Rules currently in place:
- script:
    - no imports allowed
    - cannot be imported

- entities:
    - not allowed to import any other layer of the project
    - external imports only
- infrastructure:
    - allowed to import entities

Each following layer can import any layer above it (except scripts)
- analyzer
- interface

Additional rules:
- only package files are checked (placed within folders containing
    __init__.py)
- temporary directories are excluded (hidden directories, __pycache__,
    tmpvenv)
- for CI integration: returns 1 on any failure.
"""

import ast
import sys
from pathlib import Path

# Assume standard practice: file called from project root.
PROJECT_ROOT = Path.cwd()
SRC_ROOT = PROJECT_ROOT

# Directory da escludere dalla scansione
# Excluded directories
EXCLUDED_DIRS = {".venv", "tmpvenv", "__pycache__", ".git"}

# Mappa layer → cartella reale (relativa alla root del progetto)
# layer-path mappings
LAYER_PATHS = {
    "entities": SRC_ROOT / "entities",
    "infrastructure": SRC_ROOT / "infrastructure",
    "analyzer": SRC_ROOT / "analyzer",
    "interface": SRC_ROOT / "interface",
    "scripts": SRC_ROOT / "scripts",
}

# Regole dei layer (nomi coerenti e tutti in minuscolo)
# Allowed import rules
LAYER_RULES = {
    "entities": set(),
    "infrastructure": {"entities"},
    "analyzer": {"entities", "infrastructure"},
    "interface": {"entities", "infrastructure", "analyzer"},
    "scripts": set(),  # non devono essere importati da nessuno
}


def is_package(path: Path) -> bool:
    """
    Verifica se una directory è un package Python.
    Checks if a folder is considered a Python package.

    Args:
        path (Path): The path to check.

    Returns:
        bool: The decision.
    """
    return (path / "__init__.py").exists()


def detect_layer(file_path: Path) -> str | None:
    """
    Determina a quale layer appartiene un file in base alla sua posizione
    nelle cartelle definite in LAYER_PATHS.
    Checks which layer a file belongs to.

    Args:
        file_path (Path): The filepath

    Returns:
        str | None: The associated layer - none if the layer is not\
            considered within the ruleset.
    """
    for layer, folder in LAYER_PATHS.items():
        try:
            file_path.relative_to(folder)
            return layer  # es: "entities", "analyzer", ...
        except ValueError:
            continue
    return None


def extract_imports(file_path: Path) -> list[tuple[str, int, str]]:
    """
    Estrae tutti gli import da un file Python usando AST.

    Restituisce una lista di tuple:
        (nome_modulo, numero_linea, testo_import)
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        # Se il file non è sintatticamente valido, lo saltiamo
        return []

    imports: list[tuple[str, int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # alias.name può essere "src.entities.user" ecc.
                module_name = alias.name
                imports.append((module_name, node.lineno, 
                                f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module
                imports.append(
                    (module_name, node.lineno, 
                     f"from {node.module} import ...")
                )

    return imports


def classify_import(module: str) -> str | None:
    """
    Cerca di capire se un import appartiene a un layer del progetto.

    Regole:
    - Se il modulo inizia con "src.<layer>...", prende <layer>.
    - Altrimenti prende la prima parte prima del punto.
    - Restituisce il nome del layer in minuscolo se è uno dei layer
        noti, altrimenti None.
    """
    parts = module.split(".")

    if len(parts) >= 2 and parts[0] == "src":
        candidate = parts[1]
    else:
        candidate = parts[0]

    candidate = candidate.lower()
    return candidate if candidate in LAYER_RULES else None


def check_file(file_path: Path, layer: str) -> list[str]:
    """
    Verifica le regole per un singolo file appartenente a un certo layer.

    Restituisce la lista di stringhe di violazione.
    """
    violations: list[str] = []
    imports = extract_imports(file_path)

    for module, line, imp_text in imports:
        imported_layer = classify_import(module)

        # Import proveniente da una libreria esterna → OK
        if imported_layer is None:
            continue

        # Regola speciale: ENTITIES non deve importare moduli del progetto
        if layer == "entities":
            violations.append(
                f"[Entities violation] {file_path} (line {line}) "
                f"importa {module} tramite '{imp_text}', "
                f"ma 'entities' deve essere privo di import di altri\
                    layer del progetto."
            )
            continue

        # Regola speciale: scripts non deve essere importato da nessuno
        if imported_layer == "scripts":
            violations.append(
                f"[Scripts violation] {file_path} (line {line}) "
                f"importa {module} tramite '{imp_text}', "
                "ma la cartella 'scripts' non può essere importata da\
                    nessun layer."
            )
            continue

        # Regola generale dei layer:
        # un layer può importare solo sé stesso
        # e quelli ammessi in LAYER_RULES[layer]
        allowed = LAYER_RULES[layer]
        if imported_layer not in allowed and imported_layer != layer:
            violations.append(
                f"[Layer violation] {file_path} (line {line}) "
                f"({layer}) → importa {module} ({imported_layer}) \
                    tramite '{imp_text}' → NON PERMESSO"
            )

    return violations


def main() -> None:
    print("Controllo statico dei livelli...")

    all_violations: list[str] = []

    for file_path in SRC_ROOT.rglob("*.py"):
        # Salta file dentro cartelle escluse
        if any(part in EXCLUDED_DIRS for part in file_path.parts):
            continue

        # Considera solo file dentro package Python
        if not is_package(file_path.parent):
            continue

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
