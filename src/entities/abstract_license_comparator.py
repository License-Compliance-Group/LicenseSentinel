"""Abstract class for comparing license trees.
Raises: NotImplementedError - this is an abstract class, it is not
intended to be used directly.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class AbstractLicenseComparator(ABC):

    """Interface for providing license tree comparison capabilities."""

    # This class is intended for a single purpose.
    # pylint: disable=too-few-public-methods

    @abstractmethod
    def compare_license_trees(self, override_cache: Optional[bool]):
        """An abstract tree-comparing function.
        Args:
            override_cache: True is code shouldn't use caching
                (n/a if caching not implemented)
        """
        raise NotImplementedError
