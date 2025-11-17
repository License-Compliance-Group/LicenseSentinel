
class PyPiMetadata:
    def __init__(self, package, license, link):
        self._package = package
        self._license = license
        self._link = link

    @property
    def package(self):
        return self._package

    @property
    def license(self):
        return self._license

    @property
    def link(self):
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
