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

    def run_scan(self, scan_path: Path, pkg: str) -> Optional[Dict[str, Any]]:
        """Run ScanCode (or equivalent) on `scan_path`.

        Args:
            scan_path: Path to the repository archive (zip) or extracted root.
            pkg: Package name used for logging / context.

        Returns:
            Parsed ScanCode JSON as a dict, or `None` on failure.
        """
        raise NotImplementedError
