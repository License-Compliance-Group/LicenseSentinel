"""Definition of the PyPiMetadata object
"""

class PyPiMetadata:
    """Describes the metadata of a PyPI-hosted package"""
    def __init__(self, package, license_name, link):
        self._package = package
        self._license = license_name
        self._link = link

    @property
    def package(self):
        """The package name"""
        return self._package

    @property
    def license(self):
        """The package license"""
        return self._license

    @property
    def link(self):
        """Link to package in PyPI"""
        return self._link

    @package.setter
    def package(self, value):
        if not value:
            raise ValueError("Package cannot be empty.")
        self._package = value

    @license.setter
    def license(self, value):
        self._license = value

    @link.setter
    def link(self, value):
        self._link = value
