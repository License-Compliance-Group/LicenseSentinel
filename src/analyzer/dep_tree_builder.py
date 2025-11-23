"""TreeBuilder Canary Module

Creates an isolated virtual environment, installs specified packages,
and uses pipdeptree to build and print a dependency tree.
"""
import json
import os
import shutil
import subprocess
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from infrastructure.logger_formatter import LoggerFormatter

logger = LoggerFormatter.initialize("Dependency tree builder", logging.INFO)

PACKAGES = ["flask"]

# Deve gestire la creazione dell'enviroment stile singleton
# (create e destroy ecc ma per ora non uso il pattern)
# Deve essere l'unica classe a poter modificare o interagire con il tempvenv

def venv_exists(path: str = "tmpvenv") -> bool:
    """Check if a virtual environment exists at the given path.

    Args:
        path: Directory name for the virtual environment.

    Returns:
        True if the venv directory exists, False otherwise.
    """
    venv_path = Path(path)
    return venv_path.exists() and venv_path.is_dir()


def create_venv(path: str = "tmpvenv", force_recreate: bool = False) -> str:
    """Create a virtual environment if it doesn't exist.

    Args:
        path: Directory name for the virtual environment.
        force_recreate: If True, delete existing venv and create a fresh one.

    Returns:
        Path to the bin/Scripts directory of the venv.

    Raises:
        RuntimeError: If venv creation or deletion fails.
    """
    venv_path = Path(path)

    if force_recreate and venv_exists(path):
        delete_venv(path)

    if not venv_path.exists():
        logger.info("Creating virtual environment at %s…", path)
        try:
            subprocess.run([sys.executable, "-m", "venv", path], check=True)
            logger.info("Virtual environment ready at %s", path)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Failed to create venv: {exc}") from exc
    else:
        logger.info("Virtual environment at %s already exists.", path)

    bin_dir = "Scripts" if os.name == "nt" else "bin"
    return str(venv_path / bin_dir)

def delete_venv(path: str = "tmpvenv") -> None:
    """Delete the virtual environment directory if it exists.

    Args:
        path: Directory name for the virtual environment.

    Raises:
        RuntimeError: If deletion fails.
    """
    venv_path = Path(path)
    if venv_path.exists():
        logger.info("Deleting virtual environment at %s…", path)
        try:
            shutil.rmtree(venv_path)
        except OSError as exc:
            raise RuntimeError(f"Failed to delete venv: {exc}") from exc
    else:
        logger.warning("Virtual environment at %s does not exist, nothing to delete.", path)

#Pipdeptree deve essere per forza installato nel venv
def install_packages(venv_bin: str, packages: List[str]) -> None:
    """Install packages and pipdeptree into the virtual environment.

    Args:
        venv_bin: Path to the tmpvenv bin/Scripts directory.
        packages: List of package names to install.

    Raises:
        RuntimeError: If any pip install command fails.
    """
    python_exe = "python.exe" if os.name == "nt" else "python"
    python = Path(venv_bin) / python_exe
    #TODO: pipdeptree should not be downloaded but shipped with this tool
    logger.info("Installing packages: %s", ", ".join(packages))
    try:
        subprocess.run([str(python), "-m", "pip", "install", "--quiet"] + packages, check=True)
        subprocess.run([str(python), "-m", "pip", "install", "--quiet", "pipdeptree"], check=True)
        # For hiding the output of pip install
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL,
       
    except subprocess.CalledProcessError as exc:
        logger.critical("Failed to install packages with exit code %s", exc.returncode)
        raise RuntimeError(f"Failed to install packages: {exc}") from exc

def get_tree_json(venv_bin: str) -> List[Dict]:
    """Run pipdeptree and return the JSON dependency tree.

    Args:
        venv_bin: Path to the venv bin/Scripts directory.

    Returns:
        Parsed JSON tree (list of package nodes).

    Raises:
        RuntimeError: If pipdeptree execution fails or JSON is invalid.
    """
    exe = "pipdeptree.exe" if os.name == "nt" else "pipdeptree"
    pipdeptree = Path(venv_bin) / exe

    logger.info("Running pipdeptree…")
    try:
        result = subprocess.run(
            [str(pipdeptree), "--json-tree"],
            stdout=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as exc:
        logger.critical("pipdeptree failed with exit code %s", exc.returncode)
        raise RuntimeError(f"pipdeptree failed: {exc}") from exc

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from pipdeptree: {exc}") from exc

def build_map(tree_json: List[Dict]) -> Dict[str, List[str]]:
    """Build a flat dependency graph from the pipdeptree JSON output.

    Args:
        tree_json: Parsed JSON tree from pipdeptree.

    Returns:
        A dict mapping package name -> list of direct dependencies.
    """
    graph: Dict[str, List[str]] = {}

    def visit(node: Dict) -> None:
        pkg = node.get("key", "")
        deps = [d.get("key", "") for d in node.get("dependencies", []) if d.get("key")]
        graph[pkg] = deps

        for dep_node in node.get("dependencies", []):
            visit(dep_node)

    for node in tree_json:
        visit(node)

    return graph


def print_subtree(graph:Dict[str, List[str]], pkg:str, indent: int = 0,
                   visited: Optional[Set[str]]=None) -> None:
    """Recursively print the dependency subtree for a given package.

    Args:
        graph: Dependency graph (package -> list of dependencies).
        pkg: Root package name.
        indent: Current indentation level.
        visited: Set of already-visited packages (to avoid infinite recursion).
    """
    if visited is None:
        visited = set()

    print(" " * indent + "└── " + pkg)

    if pkg in visited:
        return

    visited.add(pkg)

    for dep in graph.get(pkg, []):
        print_subtree(graph, dep, indent + 4, visited)







def main() -> None:
    """Pylint shut up"""
    try:
        logger.info("Creating venv…")
        venv_bin = create_venv()

        logger.info("Installing root packages…")
        install_packages(venv_bin, PACKAGES)

        logger.info("Analyzing dependencies…")
        tree_json = get_tree_json(venv_bin)
        graph = build_map(tree_json)
        for pkg in graph:
            print(pkg)

        print("\n=== DEPENDENCY TREE ===\n")
        for pkg in PACKAGES:
            print(pkg)
            print_subtree(graph, pkg, indent=2)
            print()
    except RuntimeError as exc:
        logger.error("Error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    print("Running TreeBuilder…\n")
    main()
