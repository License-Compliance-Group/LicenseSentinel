"""The main file of the project"""
import os
from pathlib import Path
import logging
import json
from analyzer.package_metadata_fetcher import PackageMetadataFetcher
from analyzer.matrix_manager import LicenseCompatibilityAnalyzer
from analyzer.tree_license_analyzer import TreeAnalyzer
from infrastructure.pypi_client import PyPiHandler
from infrastructure.repo_downloader import RepoDownloader
from infrastructure.dep_tree_builder import DepTreeBuilder
from infrastructure.connectivity import Connectivity
from infrastructure.logger_formatter import LoggerFormatter


logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MATRIX_PATH = DATA_DIR / "matrix.json"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

# L'init deve preparare il matrix.json e scaricarlo


class Controller:

    def __init__(self):
        # SCARICA IL MATRIX JSON

        self.license_names = self._load_license_names()
        self._license_lookup = {
            name.lower(): name for name in self.license_names}

    @staticmethod
    def start_analysis(file_path: Path, ignore_cache: bool = False) -> None:
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
        requirements_scanner = PackageMetadataFetcher(
            pypi_scraper,
            dependencies_resolver,
            repo_downloader
        )

        metadata_items, graph = requirements_scanner.build_package_metadata(
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
        tree_analyzer.run_tree_compatibility_check(metadata_items, graph)

    # def explain_discrepancies(discrepancies):
    #    logger.info('Verifying PyPI/Scancode integrity...')
    #    scan_engine_instance = scancode_runner.ScanCodeRunner()
    #    license_comparator_instance = LicenseComparator(
    #        metadata_items,
    #        scan_engine_instance
    #    )

    #    discrepancies, doubts = license_comparator_instance.compare_license_trees(
    #        ignore_cache)
    #    if discrepancies:
    #        tree_analyzer.explain_discrepancies(discrepancies)
    #    if doubts:
    #        tree_analyzer.explain_doubts(doubts)

    #    logger.info('Tree cross-check finished with %s errors and %s warnings.',
    #                len(discrepancies), len(doubts))

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
        return bool(Connectivity.check_file_exists(path_obj))

    # Da correggere i path della matrice e del file license_names.txt
    def _load_license_names(self) -> list[str]:
        """Load license names from matrix.json."""
        lca = LicenseCompatibilityAnalyzer(path=MATRIX_PATH)
        lca.update_license_matrix()
        try:
            with MATRIX_PATH.open(encoding="utf-8") as file:
                data = json.load(file)
            return sorted(
                {lic.get("name")
                    for lic in data.get("licenses", []) if lic.get("name")}
            )
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("Failed to load license names from %s", MATRIX_PATH)
            return []

    def _canonical_license(self, license_str: str) -> str | None:
        """Return the canonical license name if it exists in the matrix."""
        if not license_str or not license_str.strip():
            return None
        return self._license_lookup.get(license_str.strip().lower())

    def license_check(self, license_str: str) -> bool:
        """Check if the input license is valid (and non-empty).

            license (str): The input license to validate.
        Returns:
            bool: True if the license is valid, False otherwise.
        """
        return self._canonical_license(license_str) is not None
