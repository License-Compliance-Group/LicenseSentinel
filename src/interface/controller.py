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
from analyzer.license_comparator import LicenseComparator

from infrastructure.pypi_client import PyPiHandler
from infrastructure.repo_downloader import RepoDownloader
from infrastructure.dep_tree_builder import DepTreeBuilder
from infrastructure.logger_formatter import LoggerFormatter
from infrastructure.scancode_runner import ScanCodeRunner
from interface.ui_state import CommandResult

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
PACKAGES_TO_SKIP = ("pip", "pipdeptree")

COMMANDS_SUGGESTIONS: list[str] = [
    "scan <package_name>",
    "scan all",
    #    "analyze dependencies",
    #    "show licenses",
    #    "export report",
    #    "clear cache",
    "quit",
]

COMMANDS: list[str] = [
    "scan",
    "scan all",
    #    "analyze dependencies",
    #    "show licenses",
    #    "export report",
    #    "clear cache",
    "quit",
]

# L'init deve preparare il matrix.json e scaricarlo


class Controller:
    """Main controller class for license compatibility analysis.

    Orchestrates the entire workflow of dependency analysis, license extraction,
    compatibility checking, and source code scanning. This class serves as the
    primary interface for the license checking application.

    Attributes:
        _license_names: Class-level cache of valid license names.
        _license_lookup: Class-level dictionary mapping lowercase license names to canonical names.
        orchestrator: Handles package metadata fetching and dependency resolution.
        incompatible_edges: List of detected license incompatibilities between packages.
    """

    _license_names: list[str] = None
    _license_lookup: dict[str, str] = {}

    def __init__(self):
        """Initialize the Controller with empty state.

        Sets up internal data structures for requirements tracking, license analysis,
        and dependency graph management. The orchestrator and analysis results are
        initialized as None and populated during analysis execution.
        """

        self._requirements_path: str
        self._main_license: str
        self.orchestrator: PackageMetadataFetcher | None = None
        # New graph with added licenses
        self._graph_with_licenses: dict[str, list[str]] | None = None
        self.metadata_items: list[PyPIMetadata]
        self.incompatible_edges: list[tuple[str,
                                            str, str, str, tuple[str, str]]] | None = None

        # Initialize matrix.json during startup - blocking operation
        # logger.info("Initializing license matrix...")
        # self.load_license_names()
        # logger.info("License matrix initialized successfully.")

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
        """Return the list of available command suggestions for autocomplete.

        Returns:
            List of command strings with parameter placeholders for UI suggestions.
        """
        return COMMANDS_SUGGESTIONS

    def get_commands(self) -> list[str]:
        """Return the list of valid command names.

        Returns:
            List of base command strings without parameters.
        """
        return COMMANDS

    def get_package_metadata(self, package_name: str) -> PyPIMetadata | None:
        """Retrieve PyPI metadata for the specified package.

        Strips any license suffix from the package name before lookup.

        Args:
            package_name: Name of the package, optionally with license suffix.

        Returns:
            PyPIMetadata object containing package information, or None if not found.

        Raises:
            RuntimeError: If start_analysis() has not been called yet.
        """
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
        """Return the dependency graph with license information appended to package names.

        Constructs a modified dependency graph where each package name is suffixed
        with its license in parentheses (e.g., "requests (Apache-2.0)").

        Returns:
            Tuple containing:
                - Root package name with its license
                - Dictionary mapping package names (with licenses) to their dependencies

        Raises:
            RuntimeError: If start_analysis() has not been called yet.
        """
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

    def get_incompatibilities(self, package_name) \
            -> list[tuple[str, str, str, str, tuple[str, str]]]:
        """Retrieve all license incompatibilities for the specified package.

        Returns incompatibilities where the package is the parent in the dependency tree.

        Args:
            package_name: Name of the package to check, optionally with license suffix.

        Returns:
            List of tuples, each containing:
                - Parent package name
                - Parent license
                - Child package name
                - Child license
                - Compatibility info tuple (verdict, explanation)

        Raises:
            RuntimeError: If start_analysis() has not been called yet.
        """
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

    def start_analysis(self, file_path: Path, ignore_cache: bool = False) -> bool:
        """Execute comprehensive license analysis on a requirements file.

        Main workflow:
        1. Loads and resolves dependencies from the requirements file
        2. Fetches metadata and licenses from PyPI for each package
        3. Analyzes the dependency tree for license incompatibilities
        4. Stores results for later retrieval via getter methods

        Args:
            file_path: Path to the requirements.txt or similar dependency file.
            ignore_cache: If True, bypass cached data and fetch fresh metadata.

        Returns:
            None. Results are stored in instance attributes and accessed via getters.
        """

        logger.debug("Working directory: %s", os.getcwd())
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return False

        logger.debug("File loaded: %s", file_path)
        pypi_scraper = PyPiHandler()
        repo_downloader = RepoDownloader()
        dependencies_resolver = DepTreeBuilder()
        self.orchestrator = PackageMetadataFetcher(
            pypi_scraper,
            dependencies_resolver,
            repo_downloader
        )

        self.metadata_items, graph = self.orchestrator.build_package_metadata(
            file_path,
            self.main_license,
            ignore_cache
        )
        if not self.metadata_items:
            logger.warning("No package metadata found for %s", file_path)
            return False

        header = f"{' PACKAGE':<20} {' LICENSE':<40} {' LINK'}"
        logger.info("-" * (len(header) + 40))
        logger.info(header)
        logger.info("-" * (len(header) + 40))

        for metadata in self.metadata_items:
            logger.info(" %s %s %s", f"{metadata.package:<20}",
                        f"{metadata.license_type:<40}", metadata.link)

        tree_analyzer = TreeAnalyzer()

        self.incompatible_edges = tree_analyzer.run_tree_compatibility_check(
            self.metadata_items, graph)
        # TODO: used for "testing", remove
        # self.incompatible_edges.extend([
        #    (
        #        "myapp",
        #        "MIT",
        #        "gnuplot",
        #        "GPL-3.0-only",
        #        (
        #            "No",
        #            "Software under a copyleft license such as the GPL-3.0-only license normally cannot be redistributed under a non-copyleft license such as the MIT license, except if it were explicitly permitted in the licenses."
        #        )
        #    ),
        #    (
        #        "backend-service",
        #        "Apache-2.0",
        #        "database-core",
        #        "AGPL-3.0-only",
        #        (
        #            "No",
        #            "Software under a copyleft license such as the AGPL-3.0-only license normally cannot be redistributed under a non-copyleft license such as the Apache-2.0 license, except if it were explicitly permitted in the licenses."
        #        )
        #    ),
        #    (
        #        "frontend-ui",
        #        "BSD-3-Clause",
        #        "auth-lib",
        #        "LGPL-3.0-only",
        #        (
        #            "No",
        #            "Software under a copyleft license such as the LGPL-3.0-only license normally cannot be redistributed under a non-copyleft license such as the BSD-3-Clause license, except if it were explicitly permitted in the licenses."
        #        )
        #    ),
        #    (
        #        "analytics",
        #        "0BSD",
        #       "report-engine",
        #        "MPL-2.0",
        #        (
        #            "No",
        #            "Software under a copyleft license such as the MPL-2.0 license normally cannot be redistributed under a non-copyleft license such as the 0BSD license, except if it were explicitly permitted in the licenses."
        #        )
        #    ),
        #    (
        #        "cli-tool",
        #        "ISC",
        #        "storage-layer",
        #        "EPL-2.0",
        #        (
        #            "No",
        #            "Software under a copyleft license such as the EPL-2.0 license normally cannot be redistributed under a non-copyleft license such as the ISC license, except if it were explicitly permitted in the licenses."
        #        )
        #    ),
        #    (
        #        "image-processor",
        #        "Zlib",
        #        "compression-engine",
        #        "CDDL-1.1",
        #        (
        #            "No",
        #            "Software under a copyleft license such as the CDDL-1.1 license normally cannot be redistributed under a non-copyleft license such as the Zlib license, except if it were explicitly permitted in the licenses."
        #        )
        #    ),
        # ])

        print("graph:", str(graph))
        print("incompatible_edges"+str(self.incompatible_edges))
        return True

    def start_scancode_analysis(self, package_name: str, ignore_cache: bool = False):
        """Perform ScanCode analysis on package source code to verify license accuracy.

        Downloads the package source repository and scans it with ScanCode to detect
        licenses directly from the codebase. Compares results against PyPI metadata
        to identify discrepancies and dubious entries.

        Args:
            package_name: Name of the package to scan or "all" to scan all packages.
            ignore_cache: If True, re-download sources and re-scan even if cached.

        Returns:
            Tuple of (discrepancies, doubts) lists, or (None, None) if package not found.

        Raises:
            RuntimeError: If start_analysis() has not been called yet.
        """
        if self.orchestrator is None:
            raise RuntimeError(
                "Must execute start_analysis() before using this method")

        scan_engine = ScanCodeRunner()

        if package_name.lower() == "all":
            return self._scan_all_packages(scan_engine, ignore_cache)

        return self._scan_single_package(package_name, scan_engine, ignore_cache)

    def _scan_all_packages(self, scan_engine: ScanCodeRunner, ignore_cache: bool):
        """Scan all packages in the metadata items.

        Args:
            scan_engine: The ScanCode runner instance.
            ignore_cache: If True, re-download sources and re-scan even if cached.

        Returns:
            Tuple of (discrepancies, doubts) lists.
        """
        for pkg in self.metadata_items:
            self.orchestrator.download_sources(
                {pkg.package: pkg.link},
                override_cache=ignore_cache
            )

        license_comparator = LicenseComparator(
            self.metadata_items, scan_engine)
        return license_comparator.compare_license_trees(ignore_cache)

    def _scan_single_package(self, package_name: str, scan_engine: ScanCodeRunner,
                             ignore_cache: bool):
        """Scan a single package.

        Args:
            package_name: Name of the package to scan.
            scan_engine: The ScanCode runner instance.
            ignore_cache: If True, re-download sources and re-scan even if cached.

        Returns:
            Tuple of (discrepancies, doubts) lists, or (None, None) if package not found.
        """
        pkg_metadata = self.get_package_metadata(package_name)
        if pkg_metadata is None or pkg_metadata.link is None:
            logger.warning(
                "No repository link found for package: %s", package_name)
            return None, None

        self.orchestrator.download_sources(
            {pkg_metadata.package: pkg_metadata.link},
            override_cache=ignore_cache
        )

        # LicenseComparator expects an iterable, so wrap single package in a list
        license_comparator = LicenseComparator([pkg_metadata], scan_engine)
        return license_comparator.compare_license_trees(ignore_cache)

    def execute_command(self, command: str) -> CommandResult:
        """Parse and execute a user command.

        Supported commands:
        - scan <package_name>: Run ScanCode analysis on the specified package
        - quit: Exit the application

        Args:
            command: The full command string including arguments.

        Returns:
            CommandResult object with execution outcome and data.
        """
        cmd_parts = command.strip().split(" ", 1)
        cmd = cmd_parts[0].lower()

        match cmd:
            case "scan":
                if len(cmd_parts) != 2:
                    return CommandResult(
                        command_type="scan",
                        success=False,
                        message="Usage: scan <package_name>"
                    )
                package_name = cmd_parts[1]
                discrepancies, doubts = self.start_scancode_analysis(package_name)  # noqa
                return CommandResult(
                    command_type="scan",
                    success=True,
                    data={
                        "package_name": package_name,
                        "discrepancies": discrepancies,
                        "doubts": doubts
                    }
                )
            case "quit":
                logger.info("Exiting the application.")
                sys.exit()
            case _:
                logger.error("Unknown command: %s", command)
                return CommandResult(
                    command_type="unknown", success=False, message="Unknown command"
                )

    def is_valid_command(self, command: str) -> bool:
        """Validate command syntax and arguments.

        Checks if the command is recognized and has the correct number and type
        of arguments. For 'scan' commands, also verifies that the package exists
        in the current analysis.

        Args:
            command: The full command string to validate.

        Returns:
            True if the command is valid and can be executed, False otherwise.
        """
        cmd_parts = command.strip().split(" ", 1)
        if not cmd_parts or not cmd_parts[0]:
            return False
        cmd = cmd_parts[0].lower()
        match cmd:
            case "scan":
                # scan requires an argument; accept 'all' as a special case
                if len(cmd_parts) != 2 or not cmd_parts[1].strip():
                    return False
                arg = cmd_parts[1].strip()
                if arg.lower() == "all":
                    return True
                if arg.lower() == "root":
                    return False
                pkg_exist = self.get_package_metadata(arg)
                return pkg_exist is not None
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

    # TODO: Da correggere i path della matrice e del file license_names.txt
    @classmethod
    def load_license_names(cls) -> list[str]:
        """Load valid license names from the compatibility matrix.

        Reads the matrix.json file, extracts all license names, and populates
        class-level caches for efficient lookup. Updates the matrix from remote
        sources before loading.

        Returns:
            Sorted list of all valid license names, or empty list if loading fails.
        """
        if cls._license_names:
            print("Using cached license names")
            return cls._license_names

        # Create data directory if it doesn't exist
        MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)

        lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)
        # success = lca.update_license_matrix()
        lca.update_license_matrix()
        # print("update_license_matrix() returned: %s", success)

        # if not success:
        #    return []

        # if not MATRIX_PATH.exists():
        #    return []

        try:
            with MATRIX_PATH.open(encoding="utf-8") as file:
                data = json.load(file)

            print("JSON loaded, extracting licenses...")
            cls._license_names = sorted(
                {lic.get("name")
                 for lic in data.get("licenses", []) if lic.get("name")}
            )
            cls._license_lookup = {
                name.lower(): name for name in cls._license_names}

            print("Successfully loaded %d license names",
                  len(cls._license_names))
            return cls._license_names
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print("Failed to load license names from %s: %s",
                  MATRIX_PATH, str(e))
            return []

    @classmethod
    def license_check(cls, license_str: str) -> bool:
        """Validate whether a license name exists in the compatibility matrix.

        Performs case-insensitive lookup against the loaded license database.
        Automatically loads the license matrix on first use.

        Args:
            license_str: The license name to validate.

        Returns:
            True if the license exists in the matrix, False otherwise or if empty.
        """
        if not license_str or not license_str.strip():
            return False

        # Lazy-load the matrix into class-level caches if needed
        if not cls._license_lookup:
            cls.load_license_names()

        return cls._license_lookup.get(license_str.strip().lower()) is not None
