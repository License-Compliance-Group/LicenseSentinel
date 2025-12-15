"""Package metadata fetcher module.

This module parses requirements.txt files, builds a complete dependency 
tree using a temporary virtual environment, and fetches license/link 
metadata from PyPI for all discovered packages.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List


from entities.package_manager_fetcher import AbstractPackageManagerFetcher
from entities.abstract_dep_tree_builder import AbstractDepTreeBuilder
from entities.abstract_repo_downloader import AbstractRepoDownloader

from entities.pypi_metadata import PyPiMetadata

from infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("package_metadata_fetcher", logging.DEBUG)


PROJECT_ROOT = Path.cwd()
DOWNLOAD_DIRECTORY = Path.joinpath(PROJECT_ROOT,'src','tmpvenv','repo_downloads')
DEFAULT_DOWNLOAD_BRANCH = "main"


class PackageMetadataFetcher:
    """The class responsible for fetching package metadata from PyPI.

    Raises:
        NotImplementedError: A WIP function has been called.

    """
    @property
    def cache_file(self) -> Path:
        """Get the cache file path."""
        return Path.joinpath(PROJECT_ROOT,"src", "data", "metadata_cache.json")

    def __init__(self,
                 pypi_client: AbstractPackageManagerFetcher,
                 dep_builder: AbstractDepTreeBuilder,
                 repo_downloader: AbstractRepoDownloader):
        self.pypi_client = pypi_client
        self.dep_builder = dep_builder
        self.repo_downloader = repo_downloader
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, Dict[str, str]]:
        """Load metadata cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                LOGGER.warning("Failed to load cache: %s", exc)
        return {}

    def _save_cache(self, cache: Dict[str, Dict[str, str]]) -> None:
        """Save metadata cache to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2)
        except OSError as exc:
            LOGGER.warning("Failed to save cache: %s", exc)

    def build_package_metadata(self, file_path: str,
                               override_cache: bool = False)\
        -> tuple[List[PyPiMetadata], dict[str, list[str]]]:
        """Build package metadata from a requirements.txt file.

        This is the main orchestrator that:
        1. Parses requirements.txt
        2. Builds full dependency tree (using temp venv + pipdeptree)
        3. Fetches PyPI metadata for all packages

        Args:
            file_path: Path to the requirements.txt file.
            override_cache: download everything unconditionally if True.

        Returns:
            (metadata_list, dependency_graph)
            metadata_list: A list of PyPiMetadata objects containing
                package name, license, and link.
            dependency_graph: dict pkg -> list of direct dependencies.
            Returns ([], {}) if parsing/build fails.
        """
        # Step 1: Parse requirements file
        dependencies = self._parse_requirements_file(file_path)
        if not dependencies:
            return [], {}

        # Step 2: Build dependency tree
        # (single pass - no intermediate function)

        LOGGER.info("Building dependency tree for %d root packages",
                    len(dependencies))
        try:
            graph, all_packages = self._deptree_handler(dependencies)
            LOGGER.info("Discovered %d total packages", len(all_packages))
        except RuntimeError as exc:
            LOGGER.error("Failed to build dependency tree: %s", exc)
            return [], {}

        # Step 3: Fetch PyPI metadata (batch operation with caching)
        results = self._load_pypi_metadata(all_packages,override_cache)

        package_urls: Dict[str, str | None] = {}
        # Step 4: Build PyPiMetadata objects and prepare
        _packages_metadata = []
        for pkg_name, metadata in results.items():
            _packages_metadata.append(PyPiMetadata(
                package=pkg_name,
                license_type=metadata['license'],
                link=metadata['link']
            ))
            package_urls[pkg_name] = metadata["link"]

        LOGGER.info("Successfully fetched metadata for %d packages",
                    len(_packages_metadata))

        # Step 5: download sources (only for packages with valid repo links)
        self._download_sources(package_urls, override_cache)

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

        return _packages_metadata, graph

    def _download_sources(self, package_urls, override_cache = False):
        """Private function. Downloads package sources from given URLs,
        utilizing a cache where appriopriate.

        Args:
            package_urls (Dict[str,str]): Dictionary storing package
            names and their respective URLs.
            override_cache (bool, optional): Downloads everything
            unconditionally if True, else uses a cache.
            Defaults to False.
        """
        if override_cache:
            LOGGER.info('Cache override active, redownloading everything.')
            filtered_repo_urls = {pkg: url for pkg,
                                  url in package_urls.items() if url}
        else:
            filtered_repo_urls = {}
            for pkg, url in package_urls.items():
                zip_path = Path.joinpath(
                    Path(DOWNLOAD_DIRECTORY), f'{pkg}.zip')
                LOGGER.debug('Looking for cached .zip at %s', zip_path)
                if url \
                and not Path.exists(zip_path):
                    filtered_repo_urls[pkg] = url
                else:
                    LOGGER.debug(
                        'Package %s inaccessible or cached, skipping',
                        pkg)
        if filtered_repo_urls:
            down_results = self.repo_downloader.download_repos(
                repo_urls=filtered_repo_urls,
                output_path=DOWNLOAD_DIRECTORY,
                branch=DEFAULT_DOWNLOAD_BRANCH,
            )
            for pkg, success in down_results.items():
                LOGGER.info("Download %s: %s", pkg, success)
        else:
            LOGGER.info("No valid repository links found, skipping downloads")

    def _deptree_handler(self, dependencies):
        """Private function. 
        Creates a dependency graph and lists packages used.

        Args:
            dependencies (List[str]): list of detected dependencies.

        Returns:
            (Dict[str, List[str]], set(str)): A dependency graph
            and names of packages used within that graph.
        """
        temp_venv = self.dep_builder.create_venv()
        self.dep_builder.install_packages(temp_venv, dependencies)
        tree_json = self.dep_builder.get_tree_json(temp_venv)
        graph = self.dep_builder.build_map(tree_json)

        # Check for cycles in dependency graph
        if self.dep_builder.has_cycles(graph):
            LOGGER.warning("Cycles detected in dependency graph - this may cause issues")

        # Extract all unique packages (keys + all values)
        all_packages = set(graph.keys())
        for deps in graph.values():
            all_packages.update(deps)

        return graph, all_packages



    def _load_pypi_metadata(self, packages,override_cache=False):
        """Private function. Loads PyPIMetadata, utilizing a cache.

        Args:
            packages: set(str): A set of package names.
            override_cache (bool, optional): 
            If true, download unconditionally. Defaults to False.
        """
        if override_cache:
            LOGGER.info('Cache override active, redownloading everything.')
            LOGGER.info("Fetching PyPI metadata for %d packages",
                    len(packages))
            results = self.pypi_client.get_source_links(list(packages))
        else:
            cache = self._load_cache()
            missing_packages = [pkg for pkg in packages
                                if pkg not in cache]

            if missing_packages:
                LOGGER.info("Fetching PyPI metadata for %d new packages\
                    (cached: %d)",
                            len(missing_packages),
                            len(packages) - len(missing_packages))
                results = self.pypi_client.get_source_links(missing_packages)
                # Update cache with new data
                cache.update(results)
                self._save_cache(cache)
            else:
                LOGGER.info("All %d package links found in cache",
                            len(packages))

            # Use cached data for all packages
            results = {pkg: cache[pkg] for pkg in packages}
        return results

    def _parse_requirements_file(self, file_path: str) -> List[str]:
        """Parse a requirements.txt file and extract package names.

        Args:
            file_path: Path to the requirements.txt file.

        Returns:
            List of package names found in the file.
        """
        dependencies = []
        # More restrictive pattern: allow only safe characters, no leading/trailing special chars
        # I don't think regex patterns are line-breakable
        pattern = re.compile(r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)(?:\s*(?:[<>=!~]+|;).*)?$") # pylint: disable=line-too-long

        try:
            LOGGER.info("Parsing project dependencies from %s", file_path)
            with open(file_path, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.split("#")[0].strip()
                    if not line:
                        continue
                    match = pattern.match(line)
                    if match:
                        pkg_name = match.group(1)
                        # Additional security: limit length and disallow dangerous patterns
                        if len(pkg_name) > 100:
                            LOGGER.warning("Package name too long on\
                                line %d, skipping: %s", line_num, pkg_name)
                            continue
                        if ".." in pkg_name \
                        or pkg_name.startswith(("/", "\\", ".")):
                            LOGGER.warning("Potentially unsafe package \
                                name on line %d, skipping: %s",
                                line_num, pkg_name)
                            continue
                        dependencies.append(pkg_name)
                    else:
                        LOGGER.warning("Invalid package name format on line %d: %s", line_num, line)

            LOGGER.info("Found %d direct dependencies", len(dependencies))

        except FileNotFoundError:
            LOGGER.error("File not found: %s", file_path)
        except OSError as exc:
            LOGGER.error("Error reading file %s: %s", file_path, exc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            LOGGER.error("Unexpected error parsing %s: %s", file_path, exc)

        return dependencies

    def pypi_license_checker(self):
        """Placeholder for future license compatibility checker."""
        raise NotImplementedError("PyPiLicenseChecker is not yet implemented")
