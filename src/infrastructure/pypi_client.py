"""The definition of PyPiHandler class"""
import logging
import requests
logger = logging.getLogger(__name__)
# SourceLinkResolver


class PyPiHandler:
    """A client to interact with PyPI and fetch package information."""

    @staticmethod
    def get_source_links(packages_names):
        """Fetches source links for a list of package names from PyPI.

        Args:
            packages_names (list): A list of package names.
        Returns:
            dict: A dictionary mapping package names to their source
            links and license.
        """
        results = {}
        for package in packages_names:
            try:
                response = requests.get(
                    f"https://pypi.org/pypi/{package}/json",
                    timeout = 10
                )
                if response.status_code == 200:
                    source_link = None
                    data = response.json()
                    info = data.get('info', {})
                    project_urls = info.get('project_urls') or {}
                    if isinstance(project_urls, dict):
                        source_link = project_urls.get('Source') \
                            or project_urls.get('source') or project_urls.get(
                            'Source Code') or project_urls.get('Repository') \
                            or project_urls.get('repository') \
                            or project_urls.get('Homepage')

                    license_info = info.get('license') or \
                        info.get('license_expression')
                    results[package] = {
                        'license': license_info,
                        'link': source_link
                    }

                else:
                    results[package] = {
                        'license': 'Unknown',
                        'link': None
                    }
            except requests.exceptions.HTTPError as e:
                logger.error(
                    "An error occurred while fetching data for %s: %s"
                    ,package, e)
                results[package] = {
                    'license': 'Unknown',
                    'link': None
                }
        return results
