""" An abstract interface for a license analyzer toolkit used 
by the orchestrator.

    Raises: NotImplementedError: this is an abstract class, it is not
intended to be used directly.

"""

from __future__ import annotations
from typing import Protocol, Optional, Dict, Any
from pathlib import Path



class ScanEngine(Protocol):
    """Abstract interface for a license analyzer toolkit used by the orchestrator.

    Implementations should run a license/scan on `scan_path` and return the
    parsed JSON results or `None` on error.
    """

    # This class is intended for a single purpose.
    # pylint: disable=too-few-public-methods

    def run_scan(self, scan_path: Path, pkg: str,
                 override_cache: Optional[bool]) -> Optional[Dict[str, Any]]:
        """Run ScanCode (or equivalent) on `scan_path` and return full output.

        Args:
            scan_path: Path to the repository archive (zip) or extracted root.
            pkg: Package name used for logging / context.
            override_cache: True if should run scans unconditionally 
                (n/a if no cache is implemented)

        Returns:
            Parsed ScanCode JSON as a dict, or `None` on failure.
        """
        raise NotImplementedError

    def scan_for_license(self, scan_path: Path, pkg:str,
                         override_cache: Optional[bool]) -> tuple(str):
        """Run Scancode (or eq.) and return a plain license string.

        Args:
            scan_path: Path to the repository archive (zip) 
                or extracted root.
            pkg: Package name used for logging / context.
            override_cache: True if should run scans unconditionally 
                (n/a if no cache is implemented)

        Returns:
            The license name(s), ("Unknown") if not detected.
        """
        raise NotImplementedError
