"""Definition of the LicenseCompatibilityAnalyzer class.
This class aggressively tries to create a license file, downloading one
if possible, unless a compliant offline version exists."""
import os
import pathlib
import json
from datetime import datetime
from infrastructure.connectivity import Connectivity as io


from src.infrastructure.logger_formatter import LoggerFormatter
logger = LoggerFormatter.initialize(__name__,
LoggerFormatter.WARNING)

class LicenseCompatibilityAnalyzer:
    """Analyzes cross-compatibility of multiple licenses.
    Handles calculations using a matrix file generously provided by OSADL
    https://osadl.org
    """

    def __init__(self, path = str(pathlib.Path.cwd()) + "/src/data/matrix.json"):
        """Constructor
        The default path is (project root)/src/data/matrix.json
        """

        self.path = path
        logger.info("Seeking license file at: %s", self.path)
        if not self.matrix_file_present():
            logger.info("License file not present.")
        self._json = None


    @property
    def json(self):
        """Private JSON property"""
        return self._json

    @json.setter
    def set_json(self, content):
        """Sets _json to content"""
        self._json = content

    @json.getter
    def get_json(self):
        """Get _json property's value"""
        return self._json


    def matrix_file_present(self):
        """Checks if the required matrix file is present
        Returns:
            bool: present or not
        """
        return os.path.isfile(self.path)

    def delete_matrix_file(self):
        """Deletes the matrix file if it's present
        """
        if self.matrix_file_present():
            os.remove(self.path)


    def download_wrapper(self, url =\
        "https://www.osadl.org/fileadmin/checklists/matrixseqexpl.json",
        attempts = 2, timeout = 30):
        """A user-friendly wrapper around the download.
        Checks connectivity, downloads and writes to a file.

        Args:
            url (str, optional): The URL to try downloading from. Defaults to\
            https://www.osadl.org/fileadmin/checklists/matrixseqexpl.json.
            attempts (int, optional): How many download attempts will happen\
            before the script gives up. Defaults to 2.
        """
        if not io.verify_internet_access():
            return None
        for i in range(1, attempts + 1):
            if i > 1:
                logger.warning("Download failed, trying again...")
            logger.info("Downloading the file (attempt %d/%d). This"+
            " will take up to %d seconds, depending on your newtork quality.",
            i, attempts, timeout)
            response = io.download_file(url,
            timeout)
            if response is not None:
                break

        logger.debug("Download successful.")
        return response



    def check_timestamp(self):
        """Compares offline and online timestamps, if possible.

        Returns:
            bool: True if the file is good enough OR we're offline, as\
                 verification is then not possible
        """
        if self.json is None:
            # We need something to compare against, a load is justified
            self.update_json()

        if self.json is None:
            logger.error("No JSON could be found, aborting")
            return False

        local_timestamp = self.get_local_timestamp()
        online_timestamp = self.get_online_timestamp()
        if online_timestamp is None or local_timestamp is None:
            logger.warning("Unable to verify file timestamp. Continuing with\
                 the offline version.")
            logger.warning("Using the offline version may cause returned data\
                 to be inaccurate.")
            return True
        return online_timestamp <= local_timestamp

    def get_local_timestamp(self):
        """Returns the cached JSON timestamp
        Note: this assumes class' JSON field was updated

        Returns:
            str: The cached timestamp
        """
        return datetime.fromisoformat(self.get_json['timestamp'])


    def get_online_timestamp(self, timeout = 30):
        """A convenience wrapper around download_file.
        Downloads a small string from a specified URL"""

        url = 'https://www.osadl.org/fileadmin/checklists/timestamp'
        timestamp = io.download_file(url, timeout, 512).text.strip()
        return datetime.fromisoformat(timestamp)


    def update_json(self):
        """Updates classes' JSON field, getting the data from offline\
             or the web. 
            Note: this function will perform I/O - avoid when possible.

        Returns:
            bool: True if update was successful
        """
        # offline version has priority
        if self.matrix_file_present():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    read_json = json.load(f)
            except json.JSONDecodeError as ex:
                logger.warning("Could not read local license file, because an\
                     exception occurred: %s, downloading.", ex)
            else:
                self.set_json = read_json
                return True
        try: # pylint: disable=no-else-return
             # huh? this is not even an else statement
            response = self.download_wrapper()
            if response is None:
                return False
            read_json = response.json()

            # We have the file, save it for future use
            # By now we are sure that the response contains valid JSON
            if not io.safe_write(self.path,
                                                           response.text):
                logger.error("Matrix file not written!")

            # Cache the JSON immediately
            # to avoid a redundant disk read
            self.set_json = read_json

        except json.JSONDecodeError as ex:
            logger.error("An unexpected error happened when downloading\
                 the online file: %s", ex)
            return False
        else:
            self.set_json = read_json
            return True


if __name__ == "__main__":
    lca = LicenseCompatibilityAnalyzer()
