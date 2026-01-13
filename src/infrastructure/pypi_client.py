"""PyPI client utilities.

Provides PyPiHandler which can fetch license and source/homepage/repository links
for packages from the PyPI JSON API.
"""
from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.exceptions import RequestException

from src.entities.package_manager_fetcher import AbstractPackageManagerFetcher
from src.infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("pypi_client", logging.INFO)


_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class PyPiHandler(AbstractPackageManagerFetcher):
    """A client to interact with PyPI and fetch package information."""

    def get_source_links(self, packages_names: List[str],
                         timeout: int = 10) -> Dict[str, Dict[str, Optional[str]]]:
        """Fetch source/homepage/repository links and license for a list of package names.

        Orchestrates concurrent fetching using asyncio and a thread pool.

        Args:
            packages_names: list of package names (strings).
            timeout: HTTP request timeout (seconds).

        Returns:
            A dict mapping package name -> {'license': Optional[str], 'link': Optional[str]}.
        """
        try:
            return asyncio.run(self._get_source_links_async(packages_names, timeout))
        except RuntimeError:
            # Fallback if an event loop is already running (e.g. inside another async call)
            loop = asyncio.get_event_loop_policy().new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self._get_source_links_async(packages_names, timeout)
                )
                return result
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

    async def _get_source_links_async(self, packages_names: List[str],
                                      timeout: int) -> Dict[str, Dict[str, Optional[str]]]:
        """Coroutine that schedules fetching tasks for all packages."""
        results: Dict[str, Dict[str, Optional[str]]] = {}
        loop = asyncio.get_running_loop()

        # Use a ThreadPoolExecutor to run synchronous requests non-blocking
        with ThreadPoolExecutor() as executor:
            tasks = []
            for pkg in packages_names:
                tasks.append(
                    loop.run_in_executor(
                        executor, self._process_single_package, pkg, timeout)
                )

            # Wait for all tasks to complete
            completed_results = await asyncio.gather(*tasks)

            for pkg_name, data in completed_results:
                results[pkg_name] = data

        return results

    def _process_single_package(self,
                                package: str,
                                timeout: int) -> Tuple[str, Dict[str, Optional[str]]]:
        """Synchronous worker to fetch and extract metadata for a single package.

        Executed in a separate thread to avoid blocking the async loop.
        """
        # 1. Validate package name
        if not isinstance(package, str) or not _PACKAGE_NAME_RE.match(package):
            LOGGER.warning("Skipping invalid package name: %r", package)
            return str(package), {'license': 'Unknown', 'link': None}

        # 2. Fetch JSON
        data = self.fetch_package_json(package, timeout)
        if not data:
            return package, {'license': 'Unknown', 'link': None}

        # 3. Extract Metadata
        info = data.get('info', {}) or {}
        project_urls = info.get('project_urls') or {}
        source_link: Optional[str] = None

        if isinstance(project_urls, dict):
            for key in ('Source', 'source', 'Source Code', 'source code',
                        'Code', 'code',
                        'Repository', 'repository', 'Homepage'):
                candidate = project_urls.get(key)
                if candidate:
                    source_link = candidate
                    break

            license_final = self.extract_license(info)

            LOGGER.info("Fetched %s.json", package)
            return package, {
                'license': license_final,
                'link': source_link
            }
        return package, {'license': 'Unknown', 'link': None}


    def extract_license(self, info):
        """Extract license type when given PyPI metadata JSON
        Looks in
        - classifier fields
        - dedicated license field
        - dedicated license_expression field
        The first found value is returned

        Args:
            info (dict[str, list[str]]): The JSON representation
            of package metadata

        Returns:
            str: The determined license, "Unkown" if none detected
        """
        # ----------------------------------
        # Extract license from classifiers  |
        # ----------------------------------
        classifiers = info.get("classifiers", []) or []
        license_from_classifiers = None

        for c in classifiers:
            if c.startswith("License ::"):
                parts = c.split("::")
                last_part = parts[-1].strip() if parts else None
                if last_part:
                    license_from_classifiers = last_part
                break  # take first valid license classifier

        # ----------------------------------
        # Extract "license" field (fallback)|
        # ----------------------------------
        license_simple = info.get("license")
        if isinstance(license_simple, str) and not license_simple.strip():
            license_simple = None

        # ------------------------------
        # Extract license_expression (separate field)
        # generalmente contiene la licenza intera
        # ------------------------------
        license_expression = info.get("license_expression")
        if isinstance(license_expression, str) and \
        not license_expression.strip():
            license_expression = None

        # ------------------------------
        # Final license selection
        # ------------------------------
        license_final = license_from_classifiers or \
            license_simple or \
            license_expression or \
            "Unknown"
        return license_final
    def fetch_package_json(self, package: str, timeout: int) -> Optional[Dict[str, Any]]:
        """Download and parse the JSON metadata for a single package from PyPI.

        Args:
            package: The package name.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON dictionary, or None if the request fails or JSON is invalid.
        """
        url = f"https://pypi.org/pypi/{package}/json"
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except RequestException as exc:
            LOGGER.warning("Network error fetching %s: %s", package, exc)
            return None
        except ValueError as exc:
            LOGGER.warning("Invalid JSON for %s: %s", package, exc)
            return None
        return None
