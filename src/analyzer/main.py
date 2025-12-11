"""The main file of the project"""
import os
import itertools
from pathlib import Path

# Create program-wide logging facility
import logging
from infrastructure import pypi_client
from infrastructure import repo_downloader
from infrastructure import dep_tree_builder

from analyzer import package_metadata_fetcher
from analyzer.license_compatibility_analyzer import LicenseCompatibilityAnalyzer
from infrastructure import scancode_runner
from infrastructure.logger_formatter import LoggerFormatter

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


def ensure_license_matrix() -> None:
    """Ensure the OSADL compatibility matrix is present before processing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)

    if not lca.matrix_file_present():
        logger.info("License matrix missing, downloading a fresh copy...")
        if not lca.update_license_matrix():
            logger.error("Unable to download the license matrix. Continuing without it.")
        return

    if lca.check_timestamp():
        logger.info("License matrix present and up-to-date.")
    else:
        logger.info("License matrix is stale, updating...")
        if not lca.update_license_matrix():
            logger.error("Unable to update the license matrix; using offline copy.")


def main():
    """The main function of the project."""
    logger.debug("Working directory: %s", os.getcwd())

    ensure_license_matrix()

    file_path = DEFAULT_REQUIREMENTS
    if not file_path.exists():
        logger.warning("File not found: %s", file_path)
        return

    logger.debug("File loaded: %s", file_path)
    pypi_client_instance = pypi_client.PyPiHandler()
    repo_downloader_instance = repo_downloader.RepoDownloader()
    dep_tree_builder_instance = dep_tree_builder.DepTreeBuilder()
    package_metadata_fetcher_instance = package_metadata_fetcher.PackageMetadataFetcher(
        pypi_client_instance,
        dep_tree_builder_instance,
        repo_downloader_instance
    )
    finder, graph = package_metadata_fetcher_instance.build_package_metadata(str(file_path))
    for pkg in finder:
        print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")

    run_tree_compatibility_check(finder, graph)


def run_tree_compatibility_check(packages_metadata, graph):
    """Run compatibility check along dependency edges instead of flat union."""
    if not packages_metadata:
        logger.warning("No package metadata available, skipping compatibility check.")
        return
    if not graph:
        logger.warning("Dependency graph unavailable, cannot perform tree-based compatibility check.")
        return

    license_by_pkg: dict[str, str] = {}
    for pkg in packages_metadata:
        lic = (pkg.license_type or "").strip()
        if not lic:
            logger.warning("Package %s has unknown license, skipping in compatibility check.", pkg.package)
            continue
        normalized = normalize_license_name(lic)
        if normalized is None:
            logger.warning("Package %s has unrecognized license '%s', skipping in compatibility check.", pkg.package, lic)
            continue
        license_by_pkg[pkg.package.lower()] = normalized

    if not license_by_pkg:
        logger.warning("No valid licenses collected, cannot perform compatibility check.")
        return

    lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)
    incompatible_edges = []

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
                # Same license, treat as compatible even if matrix has no self-entry
                continue
            notice = lca.compare_licenses(lic_parent, lic_dep)
            if not notice or notice[0] != "Yes":
                incompatible_edges.append((parent, lic_parent, dep, lic_dep, notice))

    print_dependency_forest(graph, license_by_pkg, incompatible_edges)

    if not incompatible_edges:
        logger.info("Dependency-tree compatibility result: Yes (all edges compatible).")
        return

    first = incompatible_edges[0]
    msg = first[4][1] if first[4] and len(first[4]) > 1 else "No explanation available."
    logger.warning("Dependency-tree compatibility result: No. First incompatible edge: %s (%s) -> %s (%s) -> %s",
                   first[0], first[1], first[2], first[3], msg)


def normalize_license_name(name: str) -> str | None:
    """Map common license strings to OSADL/SPDX-like keys used by the matrix."""
    key = name.strip().lower()
    mapping = {
        "mit": "mit",
        "mit license": "mit",
        "bsd": "bsd-3-clause",
        "bsd license": "bsd-3-clause",
        "bsd-3-clause": "bsd-3-clause",
        "bsd 3-clause": "bsd-3-clause",
        "bsd-2-clause": "bsd-2-clause",
        "apache software license": "apache-2.0",
        "apache 2.0": "apache-2.0",
        "apache-2.0": "apache-2.0",
        "mpl 2.0": "mpl-2.0",
        "mpl-2.0": "mpl-2.0",
        "mozilla public license 2.0 (mpl 2.0)": "mpl-2.0",
        "psf": "psf-2.0",
        "python software foundation license": "psf-2.0",
        "lgpl": "lgpl-2.1",
        "lgplv3": "lgpl-3.0",
        "gplv2": "gpl-2.0",
        "gplv3": "gpl-3.0",
    }
    if key in mapping:
        return mapping[key]
    # Already in a likely OSADL/SPDX form
    if any(key.startswith(prefix) for prefix in ("apache-", "bsd-", "gpl-", "lgpl-", "mpl-", "mit", "psf")):
        return key
    return None


def find_first_incompatibility(lca: LicenseCompatibilityAnalyzer,
                               pkg_licenses: list[tuple[str, str]]):
    """Return first incompatible pair with the notice from the matrix."""
    for (pkg_a, lic_a), (pkg_b, lic_b) in itertools.combinations(pkg_licenses, 2):
        notice = lca.compare_licenses(lic_a, lic_b)
        if not notice or notice[0] != "Yes":
            return pkg_a, lic_a, pkg_b, lic_b, notice
    return None


def print_dependency_forest(graph: dict[str, list[str]],
                            license_by_pkg: dict[str, str],
                            incompatible_edges: list[tuple[str, str, str, str, tuple | None]]):
    """Print dependency trees and highlight incompatible edges in red."""
    red = "\x1b[31m"
    reset = "\x1b[0m"

    incompatible_set = {(p.lower(), d.lower()) for p, _, d, _, _ in incompatible_edges}

    deps_only = {dep.lower() for deps in graph.values() for dep in deps}
    roots = [pkg for pkg in graph.keys() if pkg.lower() not in deps_only]
    if not roots:
        roots = list(graph.keys())

    def render(pkg: str, prefix: str, is_last: bool, visited: set[str], edge_incompatible: bool = False):
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
            edge_incompatible = (pkg.lower(), dep.lower()) in incompatible_set
            render(dep, sub_prefix, idx == len(children) - 1, visited, edge_incompatible)

    print("\n=== Dependency Tree (incompatible edges in red) ===")
    visited_global: set[str] = set()
    for idx, root in enumerate(roots):
        render(root, "", idx == len(roots) - 1, visited_global, False)
    print("=== End Dependency Tree ===\n")


if __name__ == "__main__":
    main()
