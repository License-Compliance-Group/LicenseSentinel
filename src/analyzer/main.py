"""The main file of the project"""
import os
import itertools
from pathlib import Path

import logging
from infrastructure import pypi_client
from infrastructure import repo_downloader
from infrastructure import dep_tree_builder
from infrastructure.logger_formatter import LoggerFormatter

from analyzer import package_metadata_fetcher
from analyzer.license_compatibility_analyzer import\
    LicenseCompatibilityAnalyzer

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


def ensure_license_matrix() -> None:
    """Ensure the OSADL compatibility matrix is present\
        before processing.
    Creates the DATA_DIR if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)

    if not lca.matrix_file_present():
        logger.info("License matrix missing, downloading a fresh copy...")
        if not lca.update_license_matrix():
            logger.error("Unable to download the license matrix.\
                Continuing with offline copy, if present.")
        return

    if lca.check_timestamp():
        logger.info("License matrix present and up-to-date.")
    else:
        logger.info("License matrix is stale, updating...")
        if not lca.update_license_matrix():
            logger.error("Unable to update the license matrix;\
                using offline copy.")


def main() -> None:
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
    package_metadata_fetcher_instance = package_metadata_fetcher.\
    PackageMetadataFetcher(
        pypi_client_instance,
        dep_tree_builder_instance,
        repo_downloader_instance
    )
    try:
        finder, graph = package_metadata_fetcher_instance.\
        build_package_metadata(str(file_path))
        for pkg in finder:
            print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")

        run_tree_compatibility_check(finder, graph)
    except Exception as exc:
        logger.error("An error occurred during processing: %s", exc)
        return


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
        normalized = normalize_license_name(lic)
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
                # Same license, treat as compatible 
                # even if matrix has no self-entry
                continue
            notice = lca.compare_licenses(lic_parent, lic_dep)
            if not notice or notice[0] != "Yes":
                incompatible_edges.append((parent, lic_parent, 
                                           dep, lic_dep, notice))

    print_dependency_forest(graph, license_by_pkg, incompatible_edges)

    if not incompatible_edges:
        logger.info("Dependency-tree compatibility result:\
             Yes (all edges compatible).")
        return

    first = incompatible_edges[0]
    msg = first[4][1] if first[4] and len(first[4]) > 1 else "No explanation available."
    logger.warning("Dependency-tree compatibility result: No. First incompatible edge: %s (%s) -> %s (%s) -> %s",
                   first[0], first[1], first[2], first[3], msg)


def normalize_license_name(name: str) -> str | None:
    """Map common license strings to OSADL/SPDX-like keys used 
        by the matrix.
    Args:  
        name (str): The input license string to normalize.  

    Returns:  
        str | None: The normalized OSADL/SPDX-compatible license 
            identifier, or None if not recognized.  

    """
    key = name.strip().lower()
    mapping = {
        # GPL Family
        "gpl-1.0": "GPL-1.0-only",
        "gpl-1.0+": "GPL-1.0-or-later",
        "gnu general public license v1.0 only": "GPL-1.0-only",
        "gnu general public license v1.0 or later": "GPL-1.0-or-later",
        "gpl-2.0": "GPL-2.0-only",
        "gpl-2.0+": "GPL-2.0-or-later",
        "gnu general public license v2.0 only": "GPL-2.0-only",
        "gnu general public license v2.0 or later": "GPL-2.0-or-later",
        "gpl-3.0": "GPL-3.0-only",
        "gpl-3.0+": "GPL-3.0-or-later",
        "gnu general public license v3.0 only": "GPL-3.0-only",
        "gnu general public license v3.0 or later": "GPL-3.0-or-later",
        "gnu general public license (gpl)": "GPL-2.0-only",

        # LGPL Family
        "lgpl-2.0": "LGPL-2.0-only",
        "lgpl-2.0+": "LGPL-2.0-or-later",
        "gnu library general public license v2 only": "LGPL-2.0-only",
        "gnu library general public license v2 or later": "LGPL-2.0-or-later",
        "lgpl-2.1": "LGPL-2.1-only",
        "lgpl-2.1+": "LGPL-2.1-or-later",
        "gnu lesser general public license v2.1 only": "LGPL-2.1-only",
        "gnu lesser general public license v2.1 or later": "LGPL-2.1-or-later",
        "lgpl-3.0": "LGPL-3.0-only",
        "lgpl-3.0+": "LGPL-3.0-or-later",
        "gnu lesser general public license v3.0 only": "LGPL-3.0-only",
        "gnu lesser general public license v3.0 or later": "LGPL-3.0-or-later",

        # AGPL Family
        "agpl-3.0": "AGPL-3.0-only",
        "gnu affero general public license v3.0": "AGPL-3.0-only",
        "gnu affero general public license v3.0 only": "AGPL-3.0-only",
        "gnu affero general public license v3.0 or later": "AGPL-3.0-or-later",

        # Apache Family
        "apache license 1.0": "Apache-1.0",
        "apache license 1.1": "Apache-1.1",
        "apache license 2.0": "Apache-2.0",
        "apache software license": "Apache-2.0",

        # BSD Family
        "bsd zero clause license": "0BSD",
        "bsd 1-clause license": "BSD-1-Clause",
        "bsd 2-clause \"simplified\" license": "BSD-2-Clause",
        "bsd 2-clause": "BSD-2-Clause",
        "bsd-simplified": "BSD-2-Clause",
        "bsd 3-clause \"new\" or \"revised\" license": "BSD-3-Clause",
        "bsd 3-clause": "BSD-3-Clause",
        "bsd license": "BSD-3-Clause",
        "bsd-new": "BSD-3-Clause",
        "bsd 4-clause \"original\" or \"old\" license": "BSD-4-Clause",
        "bsd 4-clause (university of california-specific)": "BSD-4-Clause-UC",
        "bsd 3-clause open mpi variant": "BSD-3-Clause-Open-MPI",
        "bsd-2-clause-freebsd": "BSD-2-Clause-FreeBSD",
        "bsd-2-clause-netbsd": "BSD-2-Clause-NetBSD",
        "bsd-3-clause-attribution": "BSD-3-Clause-Attribution",
        "bsd-3-clause-clear": "BSD-3-Clause-Clear",
        "bsd-3-clause-lbnl": "BSD-3-Clause-LBNL",

        # MIT Family
        "mit license": "MIT",
        "mit no attribution": "MIT-0",
        "cmu license": "MIT-CMU",
        "mit-cmu": "MIT-CMU",
        "cmu-uc": "MIT-CMU",
        "mit-modern-variant": "MIT-Modern-Variant",
        "mit-enna": "MIT-enna",
        "mit-feh": "MIT-feh",
        "mit-wu": "MIT-Wu",

        # Mozilla Family
        "mozilla public license 1.1": "MPL-1.1",
        "mozilla public license 2.0": "MPL-2.0",
        "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
        "mozilla public license 2.0 (no copyleft exception)": "MPL-2.0-no-copyleft-exception",

        # Other Common Licenses
        "academic free license v2.0": "AFL-2.0",
        "academic free license v2.1": "AFL-2.1",
        "academic free license v3.0": "AFL-3.0",
        "apple public source license 2.0": "APSL-2.0",
        "artistic license 1.0": "Artistic-1.0",
        "artistic license 1.0 (perl)": "Artistic-1.0-Perl",
        "artistic license 2.0": "Artistic-2.0",
        "bitstream vera font license": "Bitstream-Vera",
        "boost software license 1.0": "BSL-1.0",
        "creative commons attribution 2.5 generic": "CC-BY-2.5",
        "creative commons attribution 3.0 unported": "CC-BY-3.0",
        "common development and distribution license 1.0": "CDDL-1.0",
        "common development and distribution license 1.1": "CDDL-1.1",
        "common public license 1.0": "CPL-1.0",
        "educational community license v1.0": "ECL-1.0",
        "educational community license v2.0": "ECL-2.0",
        "eiffel forum license v2.0": "EFL-2.0",
        "eclipse public license 1.0": "EPL-1.0",
        "eclipse public license 2.0": "EPL-2.0",
        "european union public license 1.1": "EUPL-1.1",
        "european union public license 1.2": "EUPL-1.2",
        "fsf all permissive license": "FSFAP",
        "fsf unlimited license": "FSFUL",
        "freetype project license": "FTL",
        "historical permission notice and disclaimer": "HPND",
        "ibm powerpc initialization and boot software": "IBM-pibs",
        "icu license": "ICU",
        "independent jpeg group license": "IJG",
        "imagemagick license": "ImageMagick",
        "info-zip license": "Info-ZIP",
        "ibm public license v1.0": "IPL-1.0",
        "isc license": "ISC",
        "jasper license": "JasPer-2.0",
        "libpng license": "Libpng",
        "png reference library version 2": "libpng-2.0",
        "libtiff license": "libtiff",
        "minpack license": "Minpack",
        "the miros licence": "MirOS",
        "microsoft public license": "MS-PL",
        "microsoft reciprocal license": "MS-RL",
        "net boolean public license v1": "NBPL-1.0",
        "university of illinois/ncsa open source license": "NCSA",
        "ntp license": "NTP",
        "ogc software license, version 1.0": "OGC-1.0",
        "open ldap public license v2.8": "OLDAP-2.8",
        "openssl license": "OpenSSL",
        "open software license 3.0": "OSL-3.0",
        "php license v3.01": "PHP-3.01",
        "postgresql license": "PostgreSQL",
        "python software foundation license 2.0": "PSF-2.0",
        "python software foundation license": "PSF-2.0",
        "python license 2.0": "Python-2.0",
        "qhull license": "Qhull",
        "rsa message-digest license": "RSA-MD",
        "saxpath license": "Saxpath",
        "sgi free software license b v2.0": "SGI-B-2.0",
        "sleepycat license": "Sleepycat",
        "sml of new jersey license": "SMLNJ",
        "spencer license 86": "Spencer-86",
        "ssh openssh license": "SSH-OpenSSH",
        "ssh short notice": "SSH-short",
        "sunpro license": "SunPro",
        "unicode license v3": "Unicode-3.0",
        "unicode license agreement - data files and software (2015)": "Unicode-DFS-2015",
        "unicode license agreement - data files and software (2016)": "Unicode-DFS-2016",
        "the unlicense": "Unlicense",
        "universal permissive license v1.0": "UPL-1.0",
        "w3c software notice and license (2002-12-31)": "W3C",
        "w3c software notice and license (1998-07-20)": "W3C-19980720",
        "w3c software notice and document license (2015-05-13)": "W3C-20150513",
        "do what the f*ck you want to public license": "WTFPL",
        "x11 license": "X11",
        "xfree86 license 1.1": "XFree86-1.1",
        "zlib license": "Zlib",
        "zlib/libpng license with acknowledgement": "zlib-acknowledgement",
        "zope public license 2.0": "ZPL-2.0",
        # Additional common mappings
        "isc": "ISC",
        "cc0-1.0": "CC0-1.0",
        "cc-by-4.0": "CC-BY-4.0",
        "cc-by-sa-4.0": "CC-BY-SA-4.0",
        "beerware": "Beerware",
        "postgresql": "PostgreSQL",
        "public domain": "Unlicense",  # Approximation
    }
    if key in mapping:
        return mapping[key]
    # Already in a likely OSADL/SPDX form
    if any(key.startswith(prefix) for prefix in (
        "apache-", "bsd-", "gpl-", "lgpl-", "mpl-", "mit", "psf")
    ):
        return key
    return None


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
