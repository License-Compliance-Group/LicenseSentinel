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
import zipfile
import json
from typing import Optional
from pathlib import Path

from infrastructure.logger_formatter import LoggerFormatter


LOGGER = LoggerFormatter.initialize("scancode_runner", logging.INFO)

SCANCOMMAND_ALL = [
    "scancode",
    "-l",
    "--license-text",
    "--license-text-diagnostics",
    "--include",
    r"\*.py",  # scancode issue
    "--include",
    "\"LICENSE\"",
    "--json-pp",
    "-"  # print JSON to stdout
]


def run_scancode(scan_path: Path, pkg: str) -> Optional[dict]:
    """
    Run ScanCode on the specified path and return the JSON results.

    :param scan_path: The ROOT path of the repo to scan (Path object).
    :param pkg: Package name for logging purposes.
    :return: Parsed JSON dict from ScanCode output, or None on failure.
    """
    extracted_path = scan_path.parent / f"{scan_path.stem}_extracted"

    _extract_zip_contents(scan_path, extracted_path)


    cmd_all = SCANCOMMAND_ALL + [str(extracted_path)]
    LOGGER.info("Running ScanCode command: %s", " ".join(cmd_all))

    current_time = datetime.now()
    try:
        result = subprocess.run(
            cmd_all,
            check=True,
            capture_output=True,
            text=True
        )
        stdout_output = result.stdout
        LOGGER.info("Scan completed for %s", pkg)
        # Parse JSON from stdout
        try:
            scan_results = json.loads(stdout_output)
            return scan_results
        except json.JSONDecodeError as e:
            LOGGER.error(
                "Failed to parse ScanCode JSON output for %s: %s", pkg, e)
            return None

    except subprocess.CalledProcessError as e:
        LOGGER.error("Error scanning %s repository at %s: %s",
                     pkg, extracted_path, e)
        return None
    finally:
        current_time2 = datetime.now()
        time_difference = current_time2 - current_time
        LOGGER.info("Elapsed time for %s: %s", pkg, time_difference)


def _extract_zip_contents(zip_file_path: Path, extract_to: Path) -> None:
    """
    Extract ZIP archive to the given directory. Logs and skips on corrupt archives.

    :param zip_file_path: Path to the ZIP file (Path object).
    :param extract_to: Directory to extract to (Path object).
    """
    if not zip_file_path.exists():
        LOGGER.error("The file %s does not exist.", zip_file_path)
        return

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
    except zipfile.BadZipFile as e:
        LOGGER.error("Failed to extract zip file %s: %s", zip_file_path, e)


def main():
    """
    example main function to demonstrate usage
    """
    path = Path(
        "/home/kamil/szkola/SE/projekt/licenses/LicenseSentinel/src/downloads/numpy-main.zip/numpy.zip")
    # Call the run_scancode function
    results = run_scancode(path, "requests")
    if results:
        print(f"Scan successful, found {len(results.get('files', []))} files")


if __name__ == "__main__":
    # Entry point for script execution
    main()
