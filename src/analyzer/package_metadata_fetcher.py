"""Package metadata fetcher module.

This module parses requirements.txt files, builds a complete dependency tree
using a temporary virtual environment, and fetches license/link metadata from PyPI
for all discovered packages.
"""
import logging
import re
from typing import List

from entities.pypi_metadata import PyPiMetadata
from infrastructure.logger_formatter import LoggerFormatter
from infrastructure.pypi_client import PyPiHandler

import dep_tree_builder

logger = LoggerFormatter.initialize("package_metadata_fetcher", logging.INFO)

# Module-level cache for package metadata
_packages_metadata: List[PyPiMetadata] = []


def build_package_metadata(file_path: str) -> List[PyPiMetadata]:
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
    # Step 1: Parse requirements file
    dependencies = _parse_requirements_file(file_path)
    if not dependencies:
        return []

    # Step 2: Build dependency tree (single pass - no intermediate function)
    logger.info("Building dependency tree for %d root packages", len(dependencies))
    try:
        temp_venv = dep_tree_builder.create_venv()
        dep_tree_builder.install_packages(temp_venv, dependencies)
        tree_json = dep_tree_builder.get_tree_json(temp_venv)
        graph = dep_tree_builder.build_map(tree_json)

        # Extract all unique packages (keys + all values)
        all_packages = set(graph.keys())
        for deps in graph.values():
            all_packages.update(deps)

        logger.info("Discovered %d total packages", len(all_packages))
    except RuntimeError as exc:
        logger.error("Failed to build dependency tree: %s", exc)
        return []

    # Step 3: Fetch PyPI metadata (batch operation)
    logger.info("Fetching PyPI metadata for %d packages", len(all_packages))
    results = PyPiHandler.get_source_links(list(all_packages))

    # Step 4: per ora stampo ma bisogna lanciare scancode
    metadata_list = []
    for pkg_name, metadata in results.items():
        metadata_list.append(PyPiMetadata(
            package=pkg_name,
            license_type=metadata['license'],
            link=metadata['link']
        ))
    logger.info("Successfully fetched metadata for %d packages", len(metadata_list))
    #step 5: download sources and scan licenses with scancode
    #step 6: compare PyPI license vs scancode detected license
    #Step 7: create for each package objects package_metadata
    #        containing both pypi and scancode license info and check results
    # We had to think more about how to structure this part. From the GUI the user
    # could select a single package (from the tree view) and see all its details like:
    #  - PyPI license
    #  - Scancode detected license
    #  - License compatibility check result
    #  - Incompatibility with other packages in the tree (if any)
    # I think that we should avoid the massive I/O (PyPI jsons + repo download + scancode)
    # at once for all packages # and let this option be on-demand when the user selects a package.
    # Possibly let the option "scan all packages" be a separate button that the user
    # can press if he wants to scan everything at once.

    return metadata_list


def _parse_requirements_file(file_path: str) -> List[str]:
    """Parse a requirements.txt file and extract package names.

    Args:
        file_path: Path to the requirements.txt file.

    Returns:
        List of package names found in the file.
    """
    dependencies = []
    pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)")

    try:
        logger.info("Parsing project dependencies from %s", file_path)
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.split("#")[0].strip()
                if not line:
                    continue
                match = pattern.match(line)
                if match:
                    dependencies.append(match.group(1))

        logger.info("Found %d direct dependencies", len(dependencies))

    except FileNotFoundError:
        logger.error("File not found: %s", file_path)
    except OSError as exc:
        logger.error("Error reading file %s: %s", file_path, exc)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Unexpected error parsing %s: %s", file_path, exc)

    return dependencies


def pypi_license_checker():
    """Placeholder for future license compatibility checker."""
    raise NotImplementedError("PyPiLicenseChecker is not yet implemented")
