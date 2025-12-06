import ast
from pathlib import Path

# Definisco le regole dell'architettura
RULES = {
    "Entities": set(),
    "Analyzer": {"Entities"},
    "Infrastructure": {"Entities"},
    "Interface": {"Infrastructure", "Analyzer", "Entities"},
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", "__pycache__", ".git"}


# Verifico se una directory è un package
def is_package(path: Path) -> bool:
    return (path / "__init__.py").exists()

# Ottengo il layer a cui appartiene un file relazionando con il suo percorso
def get_layer_from_path(path: Path):
    for layer in RULES.keys():
        if layer.lower() in str(path).lower():
            return layer
    return None

# Determina il layer a cui appartiene un import
def get_layer_from_import(import_name: str):
    import_name = import_name.lower()
    for layer in RULES.keys():
        if layer.lower() in import_name:
            return layer
    return None

# Estrae tutti gli import presenti in un file Python usando AST
def analyze_imports(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    imports = []

    # Scansiona l'albero sintattico alla ricerca di import
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name.split(".")[0], node.lineno, f"import {alias.name}"))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.module.split(".")[0], node.lineno, f"from {node.module} import ..."))

    return imports


# Controlla se i file rispettano le regole dell'architettura
def check_architecture():
    violations = []

    for py_file in PROJECT_ROOT.rglob("*.py"):

        # Salta file dentro cartelle da ignorare
        if any(part in EXCLUDE_DIRS for part in py_file.parts):
            continue

        if not is_package(py_file.parent):
            continue

        layer = get_layer_from_path(py_file)
        if not layer:
            continue

        imports = analyze_imports(py_file)

        for imp, lineno, imp_text in imports:
            target_layer = get_layer_from_import(imp)
            if not target_layer:
                continue
            
            # Verifica se il layer corrente è autorizzato a importare il target
            if target_layer not in RULES[layer] and layer != target_layer:
                violations.append({
                    "file": str(py_file),
                    "line": lineno,
                    "source": layer,
                    "target": target_layer,
                    "import": imp_text
                })

    return violations


if __name__ == "__main__":
    violations = check_architecture()

    if violations:
        print("Violazioni trovate:")
        for v in violations:
            print(f"{v['file']} (riga {v['line']}): {v['source']} → {v['target']} [{v['import']}]")
    else:
        print("Nessuna violazione architetturale")
