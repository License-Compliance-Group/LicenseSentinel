"""The main file of the project"""
import os
import itertools
from pathlib import Path

import logging
from infrastructure import pypi_client
from infrastructure import repo_downloader
from infrastructure import dep_tree_builder
from infrastructure.logger_formatter import LoggerFormatter
from infrastructure import license_name_normalizer

from analyzer import package_metadata_fetcher
from analyzer.license_compatibility_analyzer import\
    LicenseCompatibilityAnalyzer

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"





def main() -> None:
    """The main function of the project."""
    logger.debug("Working directory: %s", os.getcwd())

    file_path = DEFAULT_REQUIREMENTS
    if not file_path.exists():
        logger.warning("File not found: %s", file_path)
        return

    logger.debug("File loaded: %s", file_path)
    pypi_client_instance = pypi_client.PyPiHandler()
    repo_downloader_instance = repo_downloader.RepoDownloader()
    dep_tree_builder_instance = dep_tree_builder.DepTreeBuilder()
    package_metadata_fetcher_instance = package_metadata_fetcher.\
    PackageMetadataFetcher(
        pypi_client_instance,
        dep_tree_builder_instance,
        repo_downloader_instance
    )
    finder, graph = package_metadata_fetcher_instance.\
    build_package_metadata(str(file_path))
    for pkg in finder:
        print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")

    run_tree_compatibility_check(finder, graph)

def run_tree_compatibility_check(packages_metadata, graph) -> None:
    """  
    Run compatibility check along dependency edges instead of flat union

    Args:  
        packages_metadata (list): List of package metadata objects,
            each representing a package and its license information.  
        graph (dict): Dictionary mapping package names to a list of
            their dependency package names.  
    """
    if not packages_metadata:
        logger.warning("No package metadata available, skipping\
            compatibility check.")
        return
    if not graph:
        logger.warning("Dependency graph unavailable, cannot performtree-based\
             compatibility check.")
        return

    license_by_pkg: dict[str, str] = {}
    for pkg in packages_metadata:
        lic = (pkg.license_type or "").strip()
        if not lic:
            logger.warning("Package %s has unknown license, skipping in\
                compatibility check.", pkg.package)
            continue
        normalized = license_name_normalizer.normalize(lic)
        if normalized is None:
            logger.warning("Package %s has unrecognized license '%s',\
                skipping in compatibility check.", pkg.package, lic)
            continue
        license_by_pkg[pkg.package.lower()] = normalized

    if not license_by_pkg:
        logger.warning("No valid licenses collected, cannot perform\
            compatibility check.")
        return

    lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)
    lca.update_license_matrix()
    incompatible_edges = detect_incompatible_edges(graph, license_by_pkg, lca)


    print_dependency_forest(graph, license_by_pkg, incompatible_edges)

    compile_compatibility_report(incompatible_edges)

def detect_incompatible_edges(graph, license_by_pkg, lca = None):
    """Detects and highlights incompatibilites within a dependency graph

    Args:
        graph (dict[str, list[str]]): A dependency graph.
        license_by_pkg (dict[str, str]): A packagename-license relation
        dict.
        lca (optional, LicenseCompatibilityAnalyzer): A customized
        instance of LCA. If not present, a sensible default 
        will be created.
    """
    incompatible_edges = []
    if lca is None:
        lca = LicenseCompatibilityAnalyzer()
    for parent, deps in graph.items():
        parent_key = parent.lower()
        lic_parent = license_by_pkg.get(parent_key)
        if not lic_parent:
            continue
        for dep in deps:
            lic_dep = license_by_pkg.get(dep.lower())
            if not lic_dep:
                continue
            if lic_parent == lic_dep:
                # Same license, treat as compatible
                # even if matrix has no self-entry
                continue
            notice = lca.compare_licenses(lic_parent, lic_dep)
            if not notice or notice[0] != "Yes":
                if notice[0] == 'Same':
                    logger.error('License %s/%s is incompatible with itself.',
                                 lic_parent,lic_dep)
                if notice[1] is None:
                    msg = "No explanation available."
                else:
                    msg = notice[1]
                incompatible_edges.append((
                    parent, lic_parent,dep, lic_dep, (notice[0], msg)))
    return incompatible_edges
def compile_compatibility_report(incompatible_edges):
    """Prints a report regarding potential tree incompatibilities.

    Args:
        incompatible_edges (List): List of incompatible edges.
    """
    if not incompatible_edges:
        logger.info("Dependency-tree compatibility result:\
            Yes (all edges compatible).")
        return
    logger.warning("Dependency-tree compatibility check negative.")
    logger.info('Listing problems.')
    for edge in incompatible_edges:
        logger.info("Incompatibility: %s (%s) -> %s (%s), reason: %s",
                   *edge)


def find_first_incompatibility(lca: LicenseCompatibilityAnalyzer,
                               pkg_licenses: list[tuple[str, str]])\
    -> tuple[str, str, str, str, tuple | None] | None:
    """  
    Planned for future use.
    Return the first incompatible pair of packages/licenses with 
    the notice from the matrix.  

    Args:  
        lca (LicenseCompatibilityAnalyzer): The license compatibility
        analyzer instance used to compare licenses.  
        pkg_licenses (list[tuple[str, str]]): A list of (package name,
        license key) tuples to check for incompatibilities.  

    Returns:  
        tuple[str, str, str, str, tuple | None] or None:  
            If an incompatibility is found, returns a 5-tuple:  
                (package_a, license_a, package_b, license_b, notice)  
            where 'notice' is the result from lca.compare_licenses 
                (typically a tuple or None).  
            Returns None if all pairs are compatible.  
    """
    for (pkg_a, lic_a), (pkg_b, lic_b) in itertools.combinations(
        pkg_licenses, 2):
        notice = lca.compare_licenses(lic_a, lic_b)
        if not notice or notice[0] != "Yes":
            return pkg_a, lic_a, pkg_b, lic_b, notice
    return None


def print_dependency_forest(graph: dict[str, list[str]],
                            license_by_pkg: dict[str, str],
                            incompatible_edges: list[tuple[str, str, str, str, tuple | None]]):
    """  
    Print dependency trees and highlight incompatible edges in red.  

    Args:  
        graph (dict[str, list[str]]): The dependency graph, mapping 
            package names to lists of their dependencies.  
        license_by_pkg (dict[str, str]): Mapping of package names 
            (lowercase) to their license names.  
        incompatible_edges (list[tuple[
            str, str, str, str, tuple | None
            ]]): 
            List of tuples representing incompatible dependency 
            relationships. Each tuple contains  
            (parent_pkg, parent_license, dep_pkg, dep_license, notice).  
    """
    red = "\x1b[31m"
    reset = "\x1b[0m"

    incompatible_set = {(p.lower(), d.lower())
                        for p, _, d, _, _
                        in incompatible_edges}

    deps_only = {dep.lower() for deps in graph.values() for dep in deps}
    roots = [pkg for pkg in graph.keys() if pkg.lower() not in deps_only]
    if not roots:
        roots = list(graph.keys())

    def render(pkg: str, prefix: str, is_last: bool, visited: set[str],
               edge_incompatible: bool = False):
        connector = "└── " if is_last else "├── "
        label = f"{pkg}"
        lic = license_by_pkg.get(pkg.lower())
        if lic:
            label += f" ({lic})"
        if edge_incompatible:
            label = f"{red}{label}{reset}"
        print(prefix + connector + label)
        if pkg.lower() in visited:
            return
        visited.add(pkg.lower())
        children = graph.get(pkg, [])
        for idx, dep in enumerate(children):
            sub_prefix = prefix + ("    " if is_last else "│   ")
            edge_incompatible = (pkg.lower(), dep.lower())\
                in incompatible_set
            render(
                dep,sub_prefix, idx == len(children) - 1, visited,
                   edge_incompatible
                   )

    print("\n=== Dependency Tree (incompatible edges in red) ===")
    visited_global: set[str] = set()
    for idx, root in enumerate(roots):
        render(root, "", idx == len(roots) - 1, visited_global, False)
    print("=== End Dependency Tree ===\n")


if __name__ == "__main__":
    main()
