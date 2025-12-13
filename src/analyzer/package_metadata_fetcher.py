"""Package metadata fetcher module.

This module parses requirements.txt files, builds a complete dependency tree
using a temporary virtual environment, and fetches license/link metadata from PyPI
for all discovered packages.
"""
import copy
import logging
import re
from typing import Dict, List


from entities.package_manager_fetcher import AbstractPackageManagerFetcher
from entities.abstract_dep_tree_builder import AbstractDepTreeBuilder
from entities.abstract_repo_downloader import AbstractRepoDownloader
from entities.pypi_metadata import PyPiMetadata

from infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("package_metadata_fetcher", logging.INFO)
DOWNLOAD_DIRECTORY = "tmpvenv/repo_downloads"
DEFAULT_DOWNLOAD_BRANCH = "main"
PACKAGES_TO_SKIP = ("pip", "pipdeptree")

# Note: module-level caches moved into the class as class variables below


class PackageMetadataFetcher:
    """Fetches package metadata."""
    # Module-level cache for package metadata, shared across all instances

    # Tree having only package names
    graph: Dict[str, List[str]] = {}
    # Same tree but with objects containing metadata
    packages_metadata: Dict[str, PyPiMetadata] = {}

    def __init__(self,
                 pypi_client: AbstractPackageManagerFetcher,
                 dep_builder: AbstractDepTreeBuilder,
                 repo_downloader: AbstractRepoDownloader):
        self.pypi_client = pypi_client
        self.dep_builder = dep_builder
        self.repo_downloader = repo_downloader

    def build_package_metadata(self,
                               file_path: str,

                               ) -> Dict[str, PyPiMetadata]:
        """Build package metadata from a requirements.txt file.

        This is the main orchestrator that:
        1. Parses requirements.txt
        2. Builds full dependency tree (using temp venv + pipdeptree)
        3. Fetches PyPI metadata for all packages

        Args:
            file_path: Path to the requirements.txt file.

        Returns:
            A list of PyPiMetadata objects containing package name, license, and link.
            Returns an empty list if file parsing fails.
        """
        cls = self.__class__

        # Step 1: Parse requirements file
        dependencies = self._parse_requirements_file(file_path)
        if not dependencies:
            return {}

        # Step 2: Build dependency tree (single pass - no intermediate function)
        LOGGER.info("Building dependency tree for %d root packages",
                    len(dependencies))
        try:
            temp_venv = self.dep_builder.create_venv()
            self.dep_builder.install_packages(temp_venv, dependencies)
            tree_json = self.dep_builder.get_tree_json(temp_venv)
            cls.graph = self.dep_builder.build_map(tree_json)

            # Extract all unique packages (keys + all values)
            all_packages = set(cls.graph.keys())
            for deps in cls.graph.values():
                all_packages.update(deps)

            LOGGER.info("Discovered %d total packages", len(all_packages))
        except RuntimeError as exc:
            LOGGER.error("Failed to build dependency tree: %s", exc)
            return {}

        # Step 3: Fetch PyPI metadata (batch operation)
        LOGGER.info("Fetching PyPI metadata for %d packages",
                    len(all_packages))
        results = self.pypi_client.get_source_links(list(all_packages))

        # Step 4: Build PyPiMetadata objects and prepare
        package_urls: Dict[str, str | None] = {}
        # _packages_metadata = {}
        for pkg_name, metadata in results.items():
            if pkg_name in PACKAGES_TO_SKIP:
                continue
            cls.packages_metadata[pkg_name] = PyPiMetadata(
                package=pkg_name,
                license_type=metadata['license'],
                link=metadata['link']
            )
            package_urls[pkg_name] = metadata["link"]

        LOGGER.info("Successfully fetched metadata for %d packages",
                    len(cls.packages_metadata))

        # Step 5: download sources
        # down_results = self.repo_downloader.download_repos(
        #    repo_urls=package_urls,
        #    output_path=DOWNLOAD_DIRECTORY,
        #    branch=DEFAULT_DOWNLOAD_BRANCH,
        # )
        # for pkg, success in down_results.items():
        #    LOGGER.info("Download %s: %s", pkg, success)

        # Step 6: compare PyPI license vs scancode detected license
        # Step 7: create for each package objects package_metadata
        #        containing both pypi and scancode license info and check results
        # We had to think more about how to structure this part. From the GUI the user
        # could select a single package (from the tree view) and see all its details like:
        #  - PyPI license
        #  - Scancode detected license
        #  - License compatibility check result
        #  - Incompatibility with other packages in the tree (if any)
        # I think that we should avoid the massive I/O (PyPI jsons + repo download + scancode)
        # at once for all packages # and let this option be on-
        # when the user selects a package.
        # Possibly let the option "scan all packages" be a separate button that the user
        # can press if he wants to scan everything at once.

        # Return a shallow copy so callers don't get a direct reference
        # to the internal class cache.
        return copy.deepcopy(cls.packages_metadata)

    def _parse_requirements_file(self, file_path: str) -> List[str]:
        """Parse a requirements.txt file and extract package names.

        Args:
            file_path: Path to the requirements.txt file.

        Returns:
            List of package names found in the file.
        """
        dependencies = []
        pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)")

        try:
            LOGGER.info("Parsing project dependencies from %s", file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.split("#")[0].strip()
                    if not line:
                        continue
                    match = pattern.match(line)
                    if match:
                        dependencies.append(match.group(1))

            LOGGER.info("Found %d direct dependencies", len(dependencies))

        except FileNotFoundError:
            LOGGER.error("File not found: %s", file_path)
        except OSError as exc:
            LOGGER.error("Error reading file %s: %s", file_path, exc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            LOGGER.error("Unexpected error parsing %s: %s", file_path, exc)

        return dependencies

    def get_graph(self) -> Dict[str, List[str]]:
        """Return a copy of the last-built dependency graph.

        Returns:
            A dict mapping package names to lists of dependency package names.
            Returns an empty dict if no graph was built yet.
        """
        return {pkg: list(deps) for pkg, deps in self.__class__.graph.items()}

    def pypi_license_checker(self):
        """Placeholder for future license compatibility checker."""
        raise NotImplementedError("PyPiLicenseChecker is not yet implemented")
