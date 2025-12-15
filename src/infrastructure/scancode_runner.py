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


class ScanCodeRunner():
    """Adapter that implements ScanEngine Protocol using subprocess to call scancode."""

    def run_scan(self, scan_path: Path, pkg: str) -> Optional[dict]:
        """
        Run ScanCode on the specified path and return the JSON results.

        :param scan_path: The ZIP file path or extracted root to scan.
        :param pkg: Package name for logging purposes.
        :return: Parsed JSON dict from ScanCode output, or None on failure.
        """
        extracted_path = scan_path.parent / f"{scan_path.stem}_extracted"

        if not self._extract_zip_contents(scan_path, extracted_path):
            LOGGER.error(
                "Skipping ScanCode for %s due to extraction failure.", pkg)
            return None

        cmd_all = SCANCOMMAND_ALL + [str(extracted_path)]
        LOGGER.info("Running ScanCode command: %s", " ".join(cmd_all))

        start_time = datetime.now()
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
                elapsed = datetime.now() - start_time
                LOGGER.info("Elapsed time for %s: %s", pkg, elapsed)
                return scan_results
            except json.JSONDecodeError as e:
                LOGGER.error(
                    "Failed to parse ScanCode JSON output for %s: %s", pkg, e)
                return None

        except subprocess.CalledProcessError as e:
            LOGGER.error("Error scanning %s repository at %s: %s",
                         pkg, extracted_path, e)
            return None

    def _extract_zip_contents(self, zip_file_path: Path, extract_to: Path) -> bool:
        """
        Extract ZIP archive to the given directory. Logs and skips on corrupt archives.

        :param zip_file_path: Path to the ZIP file (Path object).
        :param extract_to: Directory to extract to (Path object).
        :return: True on success, False on failure.
        """
        if not zip_file_path.exists():
            LOGGER.error("The file %s does not exist.", zip_file_path)
            return False

        try:
            extract_to.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        except zipfile.BadZipFile as e:
            LOGGER.error("Failed to extract zip file %s: %s", zip_file_path, e)
            return False
        except IOError as e:
            LOGGER.error("Unexpected error extracting %s: %s",
                         zip_file_path, e)
            return False
        return True


def main() -> None:
    """Example main to demonstrate usage (adjust path before running)."""
    example_path = Path(
        "tmpvenv/repo_downloads/somepkg-main.zip")
    engine = ScanCodeRunner()
    results = engine.run_scan(example_path, "somepkg")
    if results:
        print(f"Scan successful, found {len(results.get('files', []))} files")


if __name__ == "__main__":
    main()
