"""The main file of the project"""
import os
import sys
from pathlib import Path
import logging
import json
import copy

from entities.pypi_metadata import PyPIMetadata
from analyzer.package_metadata_fetcher import PackageMetadataFetcher
from analyzer.matrix_manager import LicenseCompatibilityAnalyzer
from analyzer.tree_license_analyzer import TreeAnalyzer
from analyzer import license_name_normalizer as normalizer

from infrastructure.pypi_client import PyPiHandler
from infrastructure.repo_downloader import RepoDownloader
from infrastructure.dep_tree_builder import DepTreeBuilder
from infrastructure.logger_formatter import LoggerFormatter
from infrastructure.scancode_runner import ScanCodeRunner
# from infrastructure.license_comparator import LicenseComparator

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
PACKAGES_TO_SKIP = ("pip", "pipdeptree")

COMMANDS_SUGGESTIONS: list[str] = [
    "scan <package_name>",
    #    "analyze dependencies",
    #    "show licenses",
    #    "export report",
    #    "clear cache",
    "quit",
]

COMMANDS: list[str] = [
    "scan",
    #    "analyze dependencies",
    #    "show licenses",
    #    "export report",
    #    "clear cache",
    "quit",
]

# L'init deve preparare il matrix.json e scaricarlo


class Controller:

    _license_names: list[str] = []
    _license_lookup: dict[str, str] = {}

    def __init__(self):
        # SCARICA IL MATRIX JSON

        self._requirements_path: str
        self._main_license: str
        self.orchestrator: PackageMetadataFetcher | None = None
        # New graph with added licenses
        self._graph_with_licenses: dict[str, list[str]] | None = None
        self.metadata_items: list[PyPIMetadata] | None = None
        self.incompatible_edges: list[tuple[str,
                                            str, str, str, tuple[str, str]]] | None = None

    @property
    def graph_with_licenses(self) -> dict[str, list[str]] | None:
        """Get a deep copy of the dependency graph with licenses."""
        if self._graph_with_licenses is None:
            return None
        return copy.deepcopy(self._graph_with_licenses)

    @property
    def requirements_path(self) -> str:
        """Get the requirements file path."""
        return self._requirements_path

    @requirements_path.setter
    def requirements_path(self, path: str) -> None:
        """Set the requirements file path."""
        self._requirements_path = path

    @property
    def main_license(self) -> str:
        """Get the main license."""
        return self._main_license

    @main_license.setter
    def main_license(self, new_license: str) -> None:
        """Set the main license."""
        self._main_license = new_license

    def get_commands_suggestions(self) -> list[str]:
        """Return the list of available commands."""
        return COMMANDS_SUGGESTIONS

    def get_commands(self) -> list[str]:
        """Return the list of available commands."""
        return COMMANDS

    def get_package_metadata(self, package_name: str) -> PyPIMetadata | None:
        """Ritorna un oggetto PyPIMetadata per il package richiesto."""
        if self.orchestrator is None:
            raise RuntimeError(
                "Must execute start_analysis() before using this method")
        # Rimuovi la licenza se presente
        package_name = package_name.split(" ")[0]
        try:
            return self.orchestrator.get_package_metadata(package_name)
        except KeyError:
            return None

    def get_graph(self) -> tuple[str, dict[str, list[str]]]:
        """Ritorna la root e il grafo delle dipendenze con licenze aggiunte al nome del pacchetto."""
        if self.orchestrator is None:
            raise RuntimeError(
                "Must execute start_analysis() before using this method")

        original_graph = self.orchestrator.get_graph()

        # Rimuovi i pacchetti da skippare dal grafo
        for pkg_to_skip in PACKAGES_TO_SKIP:
            original_graph.pop(pkg_to_skip, None)

        # 1. Costruisci il mapping: nome_originale -> nome_con_licenza
        name_mapping: dict[str, str] = {}
        for pkg in original_graph:
            # Add main license to root
            if pkg == "Root":
                # La salvo per il return; aggiungo a root la licenza principale
                root = pkg + f" ({self.main_license})"
                name_mapping[pkg] = root
                continue
            metadata = self.get_package_metadata(pkg)
            if metadata and metadata.license_type:
                normalized_license = normalizer.normalize(metadata.license_type)  # noqa
                license_suffix = f" ({normalized_license})" if normalized_license else f" ({metadata.license_type})"  # pylint: disable=line-too-long
            else:
                license_suffix = " (Unknown)"
            name_mapping[pkg] = pkg + license_suffix

        # 2. Costruisci il nuovo grafo con i nomi aggiornati
        graph_with_licenses: dict[str, list[str]] = {}
        for pkg, deps in original_graph.items():
            new_key = name_mapping[pkg]
            new_deps = [name_mapping.get(
                dep, dep + " (Unknown)") for dep in deps]
            graph_with_licenses[new_key] = new_deps

        return root, graph_with_licenses

    def get_incompatibilities(self, package_name) -> list[tuple[str, str, str, str, tuple[str, str]]]:
        """Ritorna le incompatibilità per il package richiesto."""
        if self.incompatible_edges is None:
            raise RuntimeError(
                "Must execute start_analysis() before using this method")
        package_name = package_name.split(" ")[0]
        incompatibilities = [
            (parent, parent_license, child, child_license, compatibility_info)
            for parent, parent_license, child, child_license, compatibility_info in self.incompatible_edges
            if parent == package_name
        ]
        return incompatibilities

    def start_analysis(self, file_path: Path, ignore_cache: bool = False) -> None:
        """The main function of the project."""

        # set to True to force redownload/rebuild of everything

        print(PROJECT_ROOT)

        logger.debug("Working directory: %s", os.getcwd())
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return

        logger.debug("File loaded: %s", file_path)
        pypi_scraper = PyPiHandler()
        repo_downloader = RepoDownloader()
        dependencies_resolver = DepTreeBuilder()
        self.orchestrator = PackageMetadataFetcher(
            pypi_scraper,
            dependencies_resolver,
            repo_downloader
        )

        metadata_items, graph = self.orchestrator.build_package_metadata(
            file_path,
            ignore_cache
        )
        if not metadata_items:
            logger.warning("No package metadata found for %s", file_path)
            return

        header = f"{' PACKAGE':<20} {' LICENSE':<40} {' LINK'}"
        logger.info("-" * (len(header) + 40))
        logger.info(header)
        logger.info("-" * (len(header) + 40))

        for metadata in metadata_items:
            logger.info(" %s %s %s", f"{metadata.package:<20}",
                        f"{metadata.license_type:<40}", metadata.link)

        tree_analyzer = TreeAnalyzer()
        # TODO return incompatible edges e mettili d'istanza
        self.incompatible_edges = tree_analyzer.run_tree_compatibility_check(
            metadata_items, graph)
        self.incompatible_edges.extend([
            (
                "myapp",
                "MIT",
                "gnuplot",
                "GPL-3.0-only",
                (
                    "No",
                    "Software under a copyleft license such as the GPL-3.0-only license normally cannot be redistributed under a non-copyleft license such as the MIT license, except if it were explicitly permitted in the licenses."
                )
            ),
            (
                "backend-service",
                "Apache-2.0",
                "database-core",
                "AGPL-3.0-only",
                (
                    "No",
                    "Software under a copyleft license such as the AGPL-3.0-only license normally cannot be redistributed under a non-copyleft license such as the Apache-2.0 license, except if it were explicitly permitted in the licenses."
                )
            ),
            (
                "frontend-ui",
                "BSD-3-Clause",
                "auth-lib",
                "LGPL-3.0-only",
                (
                    "No",
                    "Software under a copyleft license such as the LGPL-3.0-only license normally cannot be redistributed under a non-copyleft license such as the BSD-3-Clause license, except if it were explicitly permitted in the licenses."
                )
            ),
            (
                "analytics",
                "0BSD",
                "report-engine",
                "MPL-2.0",
                (
                    "No",
                    "Software under a copyleft license such as the MPL-2.0 license normally cannot be redistributed under a non-copyleft license such as the 0BSD license, except if it were explicitly permitted in the licenses."
                )
            ),
            (
                "cli-tool",
                "ISC",
                "storage-layer",
                "EPL-2.0",
                (
                    "No",
                    "Software under a copyleft license such as the EPL-2.0 license normally cannot be redistributed under a non-copyleft license such as the ISC license, except if it were explicitly permitted in the licenses."
                )
            ),
            (
                "image-processor",
                "Zlib",
                "compression-engine",
                "CDDL-1.1",
                (
                    "No",
                    "Software under a copyleft license such as the CDDL-1.1 license normally cannot be redistributed under a non-copyleft license such as the Zlib license, except if it were explicitly permitted in the licenses."
                )
            ),
        ])

        print("incompatible_edges"+str(self.incompatible_edges))
        return

    def start_scancode_analysis(self, package_name: str, ignore_cache: bool = False) -> bool:
        """Start the Scancode analysis to verify PyPI metadata integrity."""
        if self.orchestrator is None:
            raise RuntimeError(
                "Must execute start_analysis() before using this method")
        pkg_metadata = self.get_package_metadata(package_name)

        if pkg_metadata is None or pkg_metadata.link is None:
            # logger.warning(
            print("No repository link found for package: %s", package_name)
            return False
        print("Downloading sources for package:", pkg_metadata.package)
        self.orchestrator.download_sources(
            {pkg_metadata.package: pkg_metadata.link},
            override_cache=ignore_cache)
        return True
        # lancio la scan
        #

    # def explain_discrepancies(discrepancies):
    #    logger.info('Verifying PyPI/Scancode integrity...')
    #    scan_engine_instance = scancode_runner.ScanCodeRunner()
    #    license_comparator_instance = LicenseComparator(
    #        metadata_items,
    #        scan_engine_instance
    #    )

     #   discrepancies, doubts = license_comparator_instance.compare_license_trees(
     #       ignore_cache)
     #   if discrepancies:
     #       tree_analyzer.explain_discrepancies(discrepancies)
     #   if doubts:
     #       tree_analyzer.explain_doubts(doubts)
     #   logger.info('Tree cross-check finished with %s errors and %s warnings.',
     #               len(discrepancies), len(doubts))

    def execute_command(self, command: str) -> None:
        """Execute the given command."""
        cmd_parts = command.strip().split(" ", 1)
        cmd = cmd_parts[0].lower()
        print("cmd_parts:", cmd_parts)
        if cmd == "scan":
            if len(cmd_parts) != 2:
                logger.error("Usage: scan <package_name>")
                return
            package_name = cmd_parts[1]
            self.start_scancode_analysis(package_name)
        elif cmd == "quit":
            logger.info("Exiting the application.")
            sys.exit()
        else:
            logger.error("Unknown command: %s", command)

    def is_valid_command(self, command: str) -> bool:
        """Check if the given command is valid."""
        cmd_parts = command.strip().split(" ", 1)
        if not cmd_parts or not cmd_parts[0]:
            return False
        cmd = cmd_parts[0].lower()
        match cmd:
            case "scan":
                # scan requires a package name argument
                pkg_exist = self.get_package_metadata(cmd_parts[1].strip())
                return len(cmd_parts) == 2 and pkg_exist is not None
            case "quit":
                # quit doesn't require arguments
                return True
            case _:
                return False
    # =================================================================================#
    #                                   Logic                                          #
    # =================================================================================#

    @staticmethod
    def path_check(path: str | None) -> bool:
        """Check if the input path is valid (non-empty).
        Args:
            path (str): The input path to validate.
        Returns:
            bool: True if the path is valid, False otherwise.
        """
        if not path or not path.strip():
            return False

        path_obj = Path(path.strip())
        return path_obj.exists() and path_obj.is_file()
        # return bool(Connectivity.check_file_exists(path_obj))

    # Da correggere i path della matrice e del file license_names.txt
    @classmethod
    def load_license_names(cls) -> list[str]:
        """Load license names from matrix.json into class-level caches."""
        lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)
        lca.update_license_matrix()
        try:
            with MATRIX_PATH.open(encoding="utf-8") as file:
                data = json.load(file)
            cls._license_names = sorted(
                {lic.get("name")
                 for lic in data.get("licenses", []) if lic.get("name")}
            )
            cls._license_lookup = {
                name.lower(): name for name in cls._license_names}
            return cls._license_names
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("Failed to load license names from %s", MATRIX_PATH)
            return []

    @classmethod
    def license_check(cls, license_str: str) -> bool:
        """Check if the input license is valid (and non-empty).

            license (str): The input license to validate.
        Returns:
            bool: True if the license is valid, False otherwise.
        """
        if not license_str or not license_str.strip():
            return False

        # Lazy-load the matrix into class-level caches if needed
        if not cls._license_lookup:
            cls.load_license_names()

        return cls._license_lookup.get(license_str.strip().lower()) is not None
