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

logger = logging.getLogger(__name__)

_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class PyPiHandler:
    """A client to interact with PyPI and fetch package information."""

    @staticmethod
    def get_source_links(pkgs_names: List[str], timeout: int = 10) -> Dict[str, Dict[str, Optional[str]]]:
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
                logger.warning("Skipping invalid package name: %r", package)
                results[str(package)] = {'license': 'Unknown', 'link': None}
                continue

            url = f"https://pypi.org/pypi/{package}/json"
            try:
                resp = requests.get(url, timeout=timeout)
                resp.raise_for_status()
            except RequestException as exc:
                logger.warning("Network error fetching %s: %s", package, exc)
                results[package] = {'license': 'Unknown', 'link': None}
                continue

            try:
                data = resp.json()
            except ValueError as exc:  # includes simplejson / json decode errors
                logger.warning("Invalid JSON for %s: %s", package, exc)
                results[package] = {'license': 'Unknown', 'link': None}
                continue

            info = data.get('info', {}) or {}
            project_urls = info.get('project_urls') or {}
            source_link: Optional[str] = None
            if isinstance(project_urls, dict):
                # try several common keys (case variations)
                for key in ('Source','source','Source Code','source code',
                            'Repository','repository','Homepage'):
                    candidate = project_urls.get(key)
                    if candidate:
                        source_link = candidate
                        break

            # prefer license_expression (PEP 639-like) then license field, normalize empty -> None
            license_info = info.get(
                'license_expression') or info.get('license') or None
            if isinstance(license_info, str) and license_info.strip() == "":
                license_info = None

            results[package] = {
                'license': license_info or 'Unknown', 'link': source_link}

        return results
