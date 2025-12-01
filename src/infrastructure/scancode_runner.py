"""
scancode_runner — ScanCode integration utilities

Provides simple helpers to run ScanCode on downloaded repositories and to
extract ZIP archives prior to scanning.

Public functions
- run_scancode(scan_path, output_path)
    Run ScanCode with two presets (license-only and Python-only) on `scan_path`
    and write JSON pretty-printed results to `output_path`. Logs failures.

- _extract_zip_contents(zip_file_path, extract_to)
    Extract ZIP archive to the given directory. Logs and skips on corrupt archives.

Notes
- Requires the `scancode` CLI on PATH.
- Uses subprocess to invoke ScanCode; caller is responsible for ensuring
  `scan_path` exists and `output_path` is writable.
- Logging is performed via infrastructure.logger_formatter.LoggerFormatter.
"""

import subprocess
import logging
import zipfile

from infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("SCANCODE WORKER", logging.INFO)

# Search for LICENSE files using ScanCode
SCANCOMMAND_LICENSE_FILE = [
    "scancode",
    "-l",
    "-p",
    "--license-text",
    "--license-text-diagnostics",
    "--json-pp"
]

SCANCOMMAND_PY_ONLY = [
    "scancode",
    "-l",
    "--license-text",
    "--license-text-diagnostics",
    "--include", "*.py",
    "--json-pp"
]


def run_scancode(scan_path, output_path):
    """
    Run ScanCode on the specified path and save the results to the output path.

    :param scan_path: The path to scan.
    :param output_path: The path to save the scan results.
    """

    cmd_license = SCANCOMMAND_LICENSE_FILE + [output_path, scan_path]
    cmd_python = SCANCOMMAND_PY_ONLY + [output_path, scan_path]

    try:
        result = subprocess.run(cmd_license,
                                check=True, capture_output=True, text=True)

        print(f"Scan completed: {scan_path}")

    except subprocess.CalledProcessError as e:
        LOGGER.error("Error scanning LICENSE only file %s: %s", scan_path, e)

    try:
        # Capture the output in memory
        result = subprocess.run(cmd_python, check=True,
                                capture_output=True, text=True)
        json_output = result.stdout
        print(json_output)
        print(f"Scan completed successfully. Results saved to {output_path}.")
    except subprocess.CalledProcessError as e:
        LOGGER.error(
            "Error scanning with Python-only filter for %s: %s", scan_path, e)


def _extract_zip_contents(zip_file_path, extract_to):
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
    except zipfile.BadZipFile as e:
        LOGGER.error("Failed to extract zip file %s: %s", zip_file_path, e)
