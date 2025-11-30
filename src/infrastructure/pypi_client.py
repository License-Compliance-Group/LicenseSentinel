"""PyPI client utilities.

Provides PyPiHandler which can fetch license and source/homepage/repository links
for packages from the PyPI JSON API.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional
import requests
from requests.exceptions import RequestException
from infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("PyPI Client", logging.INFO)


_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class PyPiHandler:
    """A client to interact with PyPI and fetch package information."""

    @staticmethod
    def get_source_links(pkgs_names: List[str],
                         timeout: int = 10) -> Dict[str, Dict[str, Optional[str]]]:
        """Fetch source/homepage/repository links and license for a list of package names.

        Args:
            pkgs_names: list of package names (strings).
            timeout: HTTP request timeout (seconds).

        Returns:
            A dict mapping package name -> {'license': Optional[str], 'link': Optional[str]}.
        """
        results: Dict[str, Dict[str, Optional[str]]] = {}
        for package in pkgs_names:
            if not isinstance(package, str) or not _PACKAGE_NAME_RE.match(package):
                LOGGER.warning("Skipping invalid package name: %r", package)
                results[str(package)] = {'license': 'Unknown', 'link': None}
                continue

            url = f"https://pypi.org/pypi/{package}/json"
            try:
                resp = requests.get(url, timeout=timeout)
                resp.raise_for_status()
            except RequestException as exc:
                LOGGER.warning("Network error fetching %s: %s", package, exc)
                results[package] = {'license': 'Unknown', 'link': None}
                continue

            try:
                data = resp.json()
            except ValueError as exc:  # includes simplejson / json decode errors
                LOGGER.warning("Invalid JSON for %s: %s", package, exc)
                results[package] = {'license': 'Unknown', 'link': None}
                continue

            info = data.get('info', {}) or {}
            project_urls = info.get('project_urls') or {}
            source_link: Optional[str] = None
            if isinstance(project_urls, dict):
                # Ogni json di un repo mette il in chiavi diverse
                for key in ('Source', 'source', 'Source Code', 'source code',
                            'Code', 'code',
                            'Repository', 'repository', 'Homepage'):
                    candidate = project_urls.get(key)
                    if candidate:
                        source_link = candidate
                        break

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
            # Extract license_expression (separate field) generalmente contiene la licenza intera
            # ------------------------------
            license_expression = info.get("license_expression")
            if isinstance(license_expression, str) and not license_expression.strip():
                license_expression = None

            # ------------------------------
            # Final license selection
            # ------------------------------
            license_final = license_from_classifiers or \
                license_simple or \
                license_expression or \
                "Unknown"

            results[package] = {
                'license': license_final,
                #   'license_expression': license_expression,
                'link': source_link
            }
            LOGGER.info("Fetched %s.json", package)

        return results
