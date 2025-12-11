"""Entities.pypiMetadata

PyPiMetadata represents metadata downloaded from PyPI for a single package.

This object stores:
- package: the package name (str)
- license_type: the license string reported by PyPI (or None if unknown)
- link: a source / homepage / repository link (or None if unavailable)

Intended usage:
    meta = PyPiMetadata(package="requests", license_type="Apache-2.0", link="https://github.com/psf/requests")
    print(meta.package, meta.license_type, meta.link)
"""
from typing import Optional
import json


class PyPiMetadata():
    """
    Container for PyPI package metadata.

    Responsibilities:
    - Hold the package name, license type and a relevant link (e.g. repository or homepage).
    - Provide simple validation for the package name.
    - Expose read/write properties while keeping internal attributes private.

    Args:
        package (str): Package name (must be non-empty).
        license_type (Optional[str]): License reported by PyPI (may be None).
        link (Optional[str]): URL to package source/homepage/repository (may be None).
    """

    def _default(self, obj):
        return getattr(obj.__class__, "to_json", _default.default)(obj) # pylint:disable=E0602
                                                                        # Works as-is.

    _default.default = json.JSONEncoder().default
    json.JSONEncoder.default = _default 

    def __init__(self, package: str, license_type: Optional[str], link: Optional[str]):
        if not package:
            raise ValueError("Package cannot be empty.")
        self._package = package
        self._license_type = license_type
        self._link = link

    @property
    def package(self) -> str:
        """str: The package name. Setter validates non-empty value."""
        return self._package

    @package.setter
    def package(self, value: str) -> None:
        if not value:
            raise ValueError("Package cannot be empty.")
        self._package = value

    @property
    def license_type(self) -> Optional[str]:
        """Optional[str]: License string reported by PyPI (may be None)."""
        return self._license_type

    @license_type.setter
    def license_type(self, value: Optional[str]) -> None:
        self._license_type = value

    @property
    def link(self) -> Optional[str]:
        """Optional[str]: URL to the package's source/homepage/repository (may be None)."""
        return self._link

    @link.setter
    def link(self, value: Optional[str]) -> None:
        self._link = value

    def __repr__(self) -> str:
        return self.to_json()
        #return f"PyPiMetadata(package={self._package!r}, license_type={self._license_type!r}, link={self._link!r})"
    def to_json(self):
        """Dump PyPiMetadata object to JSON string

        Returns:
            str: The JSON string
        """
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=True,
            indent=4)
    @staticmethod
    def from_json(json_str):
        """Load PyPiMetadata from JSON string

        Args:
            json_str (str): the JSON representation

        Returns:
            PyPiMetadata: The deserialized object
        """
        return json.loads(json_str)


if __name__ == "__main__":
    test = PyPiMetadata('pkg', 'bsd', None)
    json_test = test.to_json()
    test2 = PyPiMetadata.from_json(json_test)
    print(test2['_license_type'])
