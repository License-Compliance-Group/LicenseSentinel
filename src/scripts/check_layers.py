import ast
from pathlib import Path
import networkx as nx

# Definisco regole di dipendenza tra i layers
RULES = {
    "Entities": set(),
    "Analyzer": {"Entities"},
    "Infrastructure": {"Analyzer", "Entities"},
    "Interface": {"Infrastructure", "Analyzer", "Entities"},
    "script": {"Entities", "Analyzer", "Infrastructure", "Interface"},
    "test": {"Entities", "Analyzer", "Infrastructure", "Interface", "script"},
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", "__pycache__", ".git"}

def get_layer_from_path(path: Path):
    for layer in RULES.keys():
        if layer.lower() in str(path).lower():
            return layer
    return None

def analyze_imports(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # caso di import modulo
            for alias in node.names:
                imports.append((alias.name.split(".")[0], node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            # caso "from modulo import"
            if node.module:
                imports.append((node.module.split(".")[0], node.lineno, f"from {node.module} import ..."))
    return imports

# Costruzione del grafo delle dipendenze
def build_dependency_graph():
    G = nx.DiGraph()
    violations = []
    for py_file in PROJECT_ROOT.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in py_file.parts):
            continue
        layer = get_layer_from_path(py_file)
        if not layer:
            continue
        imports = analyze_imports(py_file)
        for imp, lineno, imp_text in imports:
            for target_layer in RULES.keys():
                if imp.lower() == target_layer.lower():
                    G.add_edge(layer, target_layer)
                    if target_layer not in RULES[layer] and layer != target_layer:
                        violations.append({
                            "file": str(py_file),
                            "line": lineno,
                            "source": layer,
                            "target": target_layer,
                            "import": imp_text
                        })
    return G, violations

def check_cycles(G):
    return list(nx.simple_cycles(G))

if __name__ == "__main__":
    G, violations = build_dependency_graph()

    print("Mappa delle dipendenze tra layer:")
    for edge in G.edges():
        print(f"{edge[0]} → {edge[1]}")

    print("\nViolazioni trovate:")
    if violations:
        for v in violations:
            print(f"{v['file']} (riga {v['line']}): {v['source']} importa {v['target']} [{v['import']}]")
    else:
        print("Nessuna violazione")

    cycles = check_cycles(G)
    if cycles:
        print("\nCicli di dipendenza trovati:")
        for c in cycles:
            print(" -> ".join(c))
    else:
        print("\nNessun ciclo di dipendenza")
