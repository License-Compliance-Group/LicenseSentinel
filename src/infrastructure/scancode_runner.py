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
from datetime import datetime
import os
import multiprocessing
from multiprocessing.shared_memory import SharedMemory
import subprocess
import logging
import zipfile
import time

from infrastructure.logger_formatter import LoggerFormatter

LOGGER = LoggerFormatter.initialize("SCANCODE WORKER", logging.INFO)

# Search for LICENSE files using ScanCode

# SCANCOMMAND_LICENSE_FILE = ["scancode","-l","-p","--license-text","--license-text-diagnostics","--json-pp","-"]
# SCANCOMMAND_PY_ONLY = ["scancode","-l",    "--license-text","--license-text-diagnostics",    "--include", "'*.py'",    "--json-pp",    "-"  # stdout output]

SCANCOMMAND_ALL = [
    "scancode",
    "-l",
    "--license-text",
    "--license-text-diagnostics",
    "--include",
    "\"*.py\"",
    "--include",
    "\"LICENSE\"",
    "--json-pp",
    "-"
]
# Si possono scannerizzare cartelle multiple, ma non si possono avere cartelle diverse con opzioni diverse


def run_scancode(scan_path, pkg: str) -> json:
    """
    Run ScanCode on the specified path and save the results to the output path.

    :param scan_path: The ROOT path of the repo to scan.
    :param output_path: The path to save the scan results.
    """
    _extract_zip_contents(scan_path, scan_path + "_extracted")
    scan_path = scan_path + "_extracted"

    # cmd_license = SCANCOMMAND_LICENSE_FILE + [output_path, scan_path + "\\LICENSE"]  # NOQA
    # cmd_python = SCANCOMMAND_PY_ONLY + [output_path+"P", scan_path]
    # cmd_license = SCANCOMMAND_LICENSE_FILE + [scan_path + "\\LICENSE"]  # NOQA Scan only LICENSE file
    # cmd_python = SCANCOMMAND_PY_ONLY + [scan_path]  # Scan all .py files
    # Scan LICENSE and all .py files
    cwd = os.getcwd()
    print("Current Working Directory:", cwd)
    cmd_all = SCANCOMMAND_ALL + [scan_path]
    print(" ".join(cmd_all))

    current_time = datetime.now()
    try:

        result = subprocess.run(cmd_all, shell=True,
                                check=True, capture_output=True, text=True)
        capture_output = result.stdout
        print("Scan License completed: ", capture_output)

    except subprocess.CalledProcessError as e:
        LOGGER.error("Error scanning %s repository: %s -> %s",
                     pkg, scan_path, e)
    current_time2 = datetime.now()

    time_difference = current_time2 - current_time
    print("elapsed time: ", time_difference)


def _extract_zip_contents(zip_file_path, extract_to):
    """
    Extract ZIP archive to the given directory. Logs and skips on corrupt archives.
    """
    if not os.path.exists(zip_file_path):
        LOGGER.error("The file %s does not exist.", zip_file_path)
        return

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
    except zipfile.BadZipFile as e:
        LOGGER.error("Failed to extract zip file %s: %s", zip_file_path, e)


def main():
    path = "C:\\Users\\Dabaduck\\Desktop\\VisualStudio a caso\\scan_code\\requests-main"
    # Call the run_scancode function
    run_scancode(path, "output.json")


if __name__ == "__main__":
    # Entry point for script execution
    main()

# scancode -l --license-text --license-text-diagnostics --include "*.py" --json-pp output.json "C:\\Users\\Dabaduck\Desktop\VisualStudio a caso\scan_code\requests-main"


# scancode -l --license-text --license-text-diagnostics --include  "*.py" --json-pp, output.json, "C:\\Users\\Dabaduck\\Desktop\\VisualStudio a caso\\scan_code\\requests-main]"

# Scansiona tutto in cerca di LICENSE (possono essere + di uno) e file py in src
# scancode --license --license-text --license-text-diagnostics --json-pp output.json --include '*.py' 'LICENSE' src


# --------------*------X--------
#     \--------/      /
#        \-----------/

# PROVA QUESTA PROVA QUESTA PROVA QUESTA PROVA QUESTA PROVA QUESTA
# scancode -l --license-text --license-text-diagnostics --include "*.py" --include "LICENSE" --json-pp - "C:\\Users\\Dabaduck\Desktop\VisualStudio a caso\scan_code\requests-main"
# scancode -l --license-text --license-text-diagnostics --include "*.py" --json-pp output.json "C:\Users\Dabaduck\Desktop\VisualStudio a caso\scan_code\requests-main"
# scancode -lp --info   --license-score 0 --json-pp - --include "LICENSE" --include "README.md" --include "*.py" .

# scancode -l --license-text --license-text-diagnostics --include "*.py" --include "LICENSE" --json-pp - "C:\Users\Dabaduck\Desktop\VisualStudio a caso\scan_code\requests-main"
