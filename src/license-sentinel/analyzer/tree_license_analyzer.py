import itertools
from pathlib import Path

import logging
from src.license_sentinel.entities.pypi_metadata import PyPIMetadata
from src.license_sentinel.infrastructure.logger_formatter import LoggerFormatter
from src.license_sentinel.infrastructure import license_name_normalizer

from src.license_sentinel.analyzer.matrix_manager import LicenseCompatibilityAnalyzer

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


class TreeAnalyzer:

    logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

    @classmethod
    def explain_discrepancies(cls, discrepancies):
        """Explains comparison errors in an user-friendly way.

        Args:
            discrepancies: A list of discrepancies obtained from 
                comparing license trees
        """
        error_str = 'Lacking compatibility report:\n'
        for d in discrepancies:
            pkg = d[0]
            pypi_lic = d[1]
            scan_lic = d[2]
            error_str += f'{pkg}: {pypi_lic} was declared, '
            if len(scan_lic) == 1:
                error_str += f'but {scan_lic[0]} was found.\n'
            else:
                error_str += f'multiple licenses: ({scan_lic}) were found and'\
                    'the declared one is none of them.\n'
        error_str += 'Please note that licenses may be interchangeable despite not'\
            ' being identical.'
        cls.logger.error(error_str)

    @classmethod
    def explain_doubts(cls, doubts):
        """Explains comparison errors in an user-friendly way.

        Args:
            discrepancies: A list of unclear decisions obtained from 
                comparing license trees
        """
        multi_licensing = False
        warn_str = 'Unknown compatibility report:\n'
        for d in doubts:
            pkg = d[0]
            pypi_lic = d[1]
            scan_lic = d[2]

            warn_str += f'{pkg}: {pypi_lic} was declared'

            if isinstance(scan_lic, tuple) and len(scan_lic) > 1:
                multi_licensing = True
                warn_str += f', but multiple licenses ({scan_lic}) were found'\
                    f' and {pypi_lic} is one of them.\n'

            if scan_lic == 'Unknown':
                warn_str += ' and we were unable to discover'\
                    ' a license based on source files.\n'
        warn_str += 'Please note that exceptions and special clauses may apply. '
        if multi_licensing:
            warn_str += 'When a program is released under multiple licenses, it is'\
                ' usually the licensee\'s responsibility to comply with all of them.'
        cls.logger.warning(warn_str)

    #

    @classmethod
    def run_tree_compatibility_check(cls, packages_metadata: list[PyPIMetadata], graph) -> list[tuple[str, str, str, str, tuple[str, str]]] | None:
        """  
        Run compatibility check along dependency edges instead of flat union

        Args:  
            packages_metadata (list): List of package metadata objects,
                each representing a package and its license information.  
            graph (dict): Dictionary mapping package names to a list of
                their dependency package names.  
        """
        if not packages_metadata:
            cls.logger.warning("No package metadata available, skipping"
                               " compatibility check.")
            return
        if not graph:
            cls.logger.warning("Dependency graph unavailable, cannot performtree-based"
                               " compatibility check.")
            return

        license_by_pkg: dict[str, str] = {}
        for pkg in packages_metadata:
            lic = (pkg.license_type or "").strip()
            if not lic:
                cls.logger.warning("Package %s has unknown license, skipping in\
                    compatibility check.", pkg.package)
                continue
            normalized = license_name_normalizer.normalize(lic)
            if normalized is None:
                cls.logger.warning("Package %s has unrecognized license '%s',\
                    skipping in compatibility check.", pkg.package, lic)
                continue
            license_by_pkg[pkg.package.lower()] = normalized

        if not license_by_pkg:
            cls.logger.warning("No valid licenses collected, cannot perform\
                compatibility check.")
            return

        lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)
        lca.update_license_matrix()
        incompatible_edges = cls.detect_incompatible_edges(
            graph, license_by_pkg, lca)
        return incompatible_edges
        # print_dependency_forest(graph, license_by_pkg, incompatible_edges)

        # compile_compatibility_report(incompatible_edges)

    @classmethod
    def detect_incompatible_edges(
        cls,
        graph: dict[str, list[str]],
        license_by_pkg: dict[str, str],
        lca: LicenseCompatibilityAnalyzer | None = None
    ) -> list[tuple[str, str, str, str, tuple[str, str]]]:
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
                notice = lca.compare_licenses(
                    lic_parent, lic_dep)  # TODO INVERT HERE FOR TESTING

                if not notice or notice[0] != "Yes":
                    if notice[0] == 'Same':
                        logger.error('License %s/%s is incompatible with itself.',
                                     lic_parent, lic_dep)
                    if notice[1] is None:
                        msg = "No explanation available."
                    else:
                        msg = notice[1]
                    incompatible_edges.append((
                        parent, lic_parent, dep, lic_dep, (notice[0], msg)))
        return incompatible_edges

    @classmethod
    def compile_compatibility_report(cls, incompatible_edges):
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

    @classmethod
    def find_first_incompatibility(cls, lca: LicenseCompatibilityAnalyzer,
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
