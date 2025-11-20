import requests
import re
import logging
logger = logging.getLogger(__name__)

# SourceLinkResolver


class PyPiHandler:
    """A client to interact with PyPI and fetch package information."""

    @staticmethod
    def getSourceLinks(packages_names):
        """Fetches source links for a list of package names from PyPI.

        Args:
            packages_names (list): A list of package names.
        Returns:
            dict: A dictionary mapping package names to their source links and license.
        """
        results = {}
        for package in packages_names:
            try:
                response = requests.get(f"https://pypi.org/pypi/{package}/json")  
                if response.status_code == 200:
                    source_link = None
                    data = response.json()
                    info = data.get('info', {})
                    project_urls = info.get('project_urls') or {}
                    if isinstance(project_urls, dict):
                        source_link = project_urls.get('Source') or project_urls.get('source') or project_urls.get(
                            'Source Code') or project_urls.get('Repository') or project_urls.get('repository') or project_urls.get('Homepage')  # noqa: E501

                    license_info = info.get('license') or info.get('license_expression')  # noqa: E501
                    results[package] = {
                        'license': license_info,
                        'link': source_link
                    }

                else:
                    results[package] = {
                        'license': 'Unknown',
                        'link': None
                    }
            except Exception as e:
                logger.error(
                    f"An error occurred while fetching data for {package}: {e}")
                results[package] = {
                    'license': 'Unknown',
                    'link': None
                }
        return results
