"""
scancode_runner — ScanCode integration utilities

Provides simple helpers to run ScanCode on downloaded repositories and to
extract ZIP archives prior to scanning.

Public functions
- run_scancode(scan_path, pkg)
    Run ScanCode on `scan_path` (Path) and return parsed JSON results.
    Logs failures and returns None on error.


Notes
- Requires the `scancode` CLI on PATH.
- Uses subprocess to invoke ScanCode; caller is responsible for ensuring
  `scan_path` exists.
- Logging is performed via infrastructure.logger_formatter.LoggerFormatter.
"""
from datetime import datetime
import subprocess
import logging
import json
from typing import Optional
from pathlib import Path

from src.entities.scan_engine import ScanEngine
from src.infrastructure.logger_formatter import LoggerFormatter
from src.infrastructure.connectivity import Connectivity as io
import src.infrastructure.license_name_normalizer as normalizer


LOGGER = LoggerFormatter.initialize("scancode_runner", logging.INFO)

SCANCOMMAND_ALL = [
    "scancode",
    '-l',
    '--include',
    'LICENSE',
    '--include',
    'LICENSE.*',
    '--include',
    'COPYING',
    '--ignore',
    'docs',
    '--ignore',
    'LICENSE_*',
    '--max-depth',
    '3',  # Either a LICENSE file, or a LICENSE dir
    '--license-score',
    '80',  # only take 100% certain picks for now
    '--tallies',
    '--json-pp',
    '-'
]


class ScanCodeRunner(ScanEngine):
    """Adapter that implements ScanEngine Protocol using subprocess to call scancode."""

    # This class is intended for a single purpose.
    # pylint: disable=too-few-public-methods

    def run_scan(self, scan_path: Path, pkg: str,
                 override_cache: bool = False) -> Optional[dict]:
        """
        Run ScanCode on the specified path and return the JSON results.

        :param scan_path: The ZIP file path or extracted root to scan.
        :param pkg: Package name for logging purposes.
        :param override_cache: Run Scancode even if results are cached,
        defaults to False
        :return: Parsed JSON dict from ScanCode output, or None on failure.
        """
        cache_dir = Path("/data/scancode-results")
        cache_path = cache_dir / f"{pkg}-scancode-result.json"

        # Check if cache exists
        if not override_cache and cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_results = json.load(f)
                LOGGER.debug("Loaded cached ScanCode results for %s", pkg)
                return cached_results
            except (json.JSONDecodeError, IOError) as e:
                LOGGER.warning("Failed to load cached results for %s: %s"
                               ', recreating.', pkg, e)

        extracted_path = scan_path.parent / f"{scan_path.stem}_extracted"

        if not io.extract_zip_contents(scan_path, extracted_path):
            LOGGER.error(
                "Skipping ScanCode for %s due to extraction failure.", pkg)
            return None

        cmd_all = SCANCOMMAND_ALL + [str(extracted_path)]
        LOGGER.debug("Running ScanCode command: %s", " ".join(cmd_all))

        start_time = datetime.now()
        try:
            result = subprocess.run(
                cmd_all,
                check=True,
                capture_output=True,
                text=True
            )
            LOGGER.debug("Scan completed for %s", pkg)
            # Parse JSON from stdout
            try:
                scan_results = json.loads(result.stdout)
                elapsed = datetime.now() - start_time
                LOGGER.debug("Elapsed time for %s: %s", pkg, elapsed)
                # Save to cache
                try:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    with open(cache_path, 'w', encoding='utf-8') as f:
                        json.dump(scan_results, f)
                    LOGGER.debug("Cached ScanCode results for %s", pkg)
                except IOError as e:
                    LOGGER.warning(
                        "Failed to save cached results for %s: %s", pkg, e)
                return scan_results
            except json.JSONDecodeError as e:
                LOGGER.error(
                    "Failed to parse ScanCode JSON output for %s: %s", pkg, e)
                return None

        except subprocess.CalledProcessError as e:
            LOGGER.error("Error scanning %s repository at %s: %s",
                         pkg, extracted_path, e)
            return None

    def scan_for_license(self, scan_path: Path, pkg: str,
                         override_cache: bool = False):
        """Extract the plain license string(s) from a package

        Args:
            scan_path (Path): The path to seek source file in.
            pkg (str): The package name
            override_cache (bool, optional): True if scanning should 
                be done unconditionally. Defaults to False.

        Returns:
            tuple[str]: The extracted license strings, ('Unknown',) if none
        """
        full_output = self.run_scan(scan_path, pkg, override_cache)
        if full_output is None:
            return ("Unknown",)
        if not 'tallies' in full_output.keys():
            LOGGER.error('This version of the analyzer requires the\
                --tallies flag to be active. Enable it and try again.')
            return ("Unknown",)
        tallies = full_output['tallies']['detected_license_expression']
        # attach the most popular license (which should be the only one
        # but you never know)
        if not tallies:
            LOGGER.error('Failed to extract a suitable license for:\
                %s', pkg)
            return ("Unknown",)

        if len(tallies) == 1 and len(tallies[0]['value'].split('AND')) == 1:
            return (normalizer.normalize(tallies[0]['value']),)

        LOGGER.debug("More than one license for %s detected.", pkg)
        license_names = []
        for tally in tallies:
            license_name = tally['value']
            LOGGER.debug("%s : %s", pkg, license_name)
            if license_name is not None:
                # tallies containing 'AND' mean multiple licenses
                # a project depending on such solution has to be
                # compatible with ALL of them
                license_names.extend(
                    tuple(license_name.split(' AND ')))

            else:
                return ('Unknown',)
        return tuple(map(
            normalizer.normalize,
            set(license_names)
        ))


def main() -> None:
    """Example main to demonstrate usage (adjust path before running)."""
    example_path = Path(
        "/tmpvenv/repo_downloads/parse.zip")
    engine = ScanCodeRunner()
    licenses = engine.scan_for_license(example_path, 'parse', True)
    for lic in licenses:
        print(lic)


if __name__ == "__main__":
    main()
