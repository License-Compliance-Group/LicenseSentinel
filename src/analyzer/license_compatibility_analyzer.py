"""Definition of the LicenseCompatibilityAnalyzer class.
This class aggressively tries to create a license file, downloading one
if possible, unless a compliant offline version exists."""
import os
from pathlib import Path
import json
import itertools
from abc import abstractmethod, ABC
from datetime import datetime
from time import time

from infrastructure.connectivity import Connectivity as io
from infrastructure.logger_formatter import LoggerFormatter
logger = LoggerFormatter.initialize(__name__,
LoggerFormatter.INFO)
class CompatibilityCalcStrategy(ABC): # pylint: disable=too-few-public-methods
    # This class is meant for a single purpose.
    """Abstract Strategy class for compatibility calculation algorithms"""
    @abstractmethod
    def calculate_license_compatibility(self, licenses):
        """Calculate the compatibility between a list of licenses.

        Args:
            licenses (List[str]): A flat list of license names to check for compatibility.

        Returns:
            tuple: (result as "Yes"/"No"/"Same", explanation)
        """

class FullCompatibilityCalc(CompatibilityCalcStrategy): # pylint: disable=too-few-public-methods
    # This class is meant for a single purpose.
    """ Regular mode: just check every possible unique pair"""
    def calculate_license_compatibility(self, licenses):
        """The abstract implementation

        Args:
            licenses (List[str]): A flat list of license names

        Returns:
            (str, str): (result as "Yes"/"No"/"Same", explanation)
        """
        # don't check dupes
        licenses = set(licenses)
        for (license_a, license_b) in itertools.combinations(licenses, 2):
            license_a = license_a.lower()
            license_b = license_b.lower()
            result = LicenseCompatibilityAnalyzer.compare_licenses(
                license_a, license_b)
            if result is None or result[0] != "Yes":
                return result
        return ("Yes", "n.a.")

_LAST_ONLINE_CHECK = 0 # pylint:disable=invalid-name
                       # this variable is expected by pylint to be
                       # both snake_case and PASCAL_CASE. good luck.
                       # This variable is intended to be common
                       # across all instances. It need not be thread-safe.

class LicenseCompatibilityAnalyzer:
    """Analyzes cross-compatibility of multiple licenses.
    Handles calculations using a matrix file generously provided by OSADL
    https://osadl.org
    """

    # pylint: disable=too-many-instance-attributes
    # The thing confuses properties and attributes

    _license_matrix = ""
    _compat_calc_strategy = FullCompatibilityCalc()
    _last_comparison_result = ("None", "You have to perform a comparison first\
        ! You should use calculate_license_compatibility() for that.")

    def __init__(self, strategy=None, path=None):
        """Constructor
        The default path is (project root)/src/data/matrix.json
        """
        if strategy is None:
            self._compat_calc_strategy = FullCompatibilityCalc()
        else:
            self.compat_calc_strategy = strategy

        if path is None:
            path = Path.joinpath(Path.cwd(),"src","data","matrix.json")
        self.path = str(path)
        logger.info("Seeking license file at: %s", self.path)
        if not self.matrix_file_present():
            logger.info("License file not present.")

    @property
    def compat_calc_strategy(self):
        """The strategy property.

        Returns:
            CompatibilityCalcStrategy: The current strategy used for
            license compatibility calculation.
        """
        return self._compat_calc_strategy
    @compat_calc_strategy.setter
    def compat_calc_strategy(self, content):
        self._compat_calc_strategy = content

    @property
    def last_online_check(self):
        """Last time a successful online verification happened.
        Used to prevent excessive remote pinging.
        
        Returns:
            last_online_check: epoch time since last succesful check,
                0 if none ever happened
        """
        return _LAST_ONLINE_CHECK
    @last_online_check.setter
    def last_online_check(self, value):
        _LAST_ONLINE_CHECK = value # pylint:disable=invalid-name

    @property
    def last_comparison_result(self):
        """The last comparison's result.

        Returns:
            (str, str): (result, explanation)
        """
        return self._last_comparison_result
    @last_comparison_result.setter
    def last_comparison_result(self, value):
        self._last_comparison_result = value

    @property
    def license_matrix(self):
        """Get _license_matrix property's value"""
        if len(self._license_matrix) == 0:
            self.update_license_matrix()
            if len(self._license_matrix) == 0:
                logger.error("Unable to update license info!")
                return ""
        return self._license_matrix


    @license_matrix.setter
    def license_matrix(self, content):
        """Sets _license_matrix to content"""
        self._license_matrix = content


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
        if time() - 5 * 1000 * 60 > self.last_online_check: # 5 minutes
            if not io.verify_internet_access():
                return None
            self.last_online_check = time()
        for i in range(1, attempts + 1):
            if i > 1:
                logger.warning("Download failed, trying again...")
            logger.info("Downloading the file (attempt %d/%d). This"+
            " will take up to %d seconds, depending on your network quality.",
            i, attempts, timeout)
            response = io.download_file(url,
            timeout)
            if response is not None:
                break

        if response is not None:
            logger.debug("Download successful.")
        else:
            logger.warning("All download attempts failed.")
        return response



    def check_timestamp(self):
        """Compares offline and online timestamps, if possible.

        Returns:
            bool: True if the file is good enough OR we're offline, as\
                 verification is then not possible
        """
        if self.license_matrix is None or len(self.license_matrix) == 0:
            # We need something to compare against, a load is justified
            self.update_license_matrix()

        if self.license_matrix is None or len(self.license_matrix) == 0:
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
        return datetime.fromisoformat(self.license_matrix['timestamp'])


    def get_online_timestamp(self, timeout = 30):
        """A convenience wrapper around download_file.
        Downloads a small string from a specified URL"""

        url = 'https://www.osadl.org/fileadmin/checklists/timestamp'
        response = io.download_file(url, timeout, 512)
        if response is None:
            return None
        timestamp = response.text.strip()
        return datetime.fromisoformat(timestamp)


    def update_license_matrix(self):
        """Updates classes' license matrix field, getting the data from offline
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
                self.license_matrix = read_json
                return True
        # Don't attempt downloading when offline.
        if not io.verify_internet_access():
            self.license_matrix = ''
            return False
        try: # pylint: disable=no-else-return
             # huh? this is not even an else statement
            response = self.download_wrapper()
            if response is None:
                return False
            read_json = response.json()

            # We have the file, save it for future use
            # By now we are sure that the response contains valid JSON
            if not io.safe_write(self.path,response.text):
                logger.error("Matrix file not written!")

            # Cache the JSON immediately
            # to avoid a redundant disk read
            self.license_matrix = read_json

        except json.JSONDecodeError as ex:
            logger.error("An unexpected error happened when downloading\
                 the online file: %s", ex)
            return False
        else:
            self.license_matrix = read_json
            return True

    def extract_raw_licenses(self, json_path):
        """
        This method conflates a scancode JSON file to a raw list of licenses.
         For now it accepts a path, it might later accept a file descriptor
         or whatever else necessary
        

        Args:
            json_path (str): a string containing the file path

        Returns:
            list: A list of licenses used.
        """
        raw_json = io.safe_read(json_path)
        if raw_json is None:
            logger.error("Could not load JSON file at: %s", json_path)
            return None
        licenses_json = json.loads(raw_json)
        licenses = []
        for file_entry in licenses_json.get('files', []):
            detections = file_entry.get('license_detections', [])
            if isinstance(detections, dict) and 'license-expression' \
                in detections:
                licenses.append(detections['license-expression'])
        logger.debug("Detected licenses: %s", licenses)
        return licenses

    @classmethod
    def compare_licenses(cls, lic_a, lic_b):
        """Compare two licenses for compatibility and return the result.

        Args:
            lic_a (str): The name of the first license.
            lic_b (str): The name of the second license.

        Returns:
            tuple: (compatibility, explanation) if found, otherwise (None, None).
        """
        # OSADL license compatibility arrays seem to be alphabetically sorted
        # It's nowhere in the docs, so we won't rely on that
        # if it ever gets confirmed, we can use much more efficient binary
        # search. For now, linear will have to do.
        # Twice.
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        instance = cls._instance
        for lic in instance.license_matrix['licenses']:
            if lic['name'].lower() == lic_a.lower():
                for compat in lic['compatibilities']:
                    if compat['name'].lower() == lic_b.lower():
                        notice = (compat['compatibility'],
                                    compat['explanation'])
                        logger.debug("Notice detected: %s", notice)
                        return notice

                logger.warning('Unknown license type for lic_b: %s \
                    (lic_a: %s found)', lic_b, lic_a)
                return (None, None)
        logger.warning('Unknown license type for lic_a: %s', lic_a)
        return (None, None)

    def calculate_license_compatibility(self, licenses):
        """Calculate license compatibility of the project using currently 
        selected strategy.

        Args:
            licenses (List[str]): A flat list of license names
        """
        self.last_comparison_result = self.compat_calc_strategy.\
            calculate_license_compatibility(licenses)


if __name__ == "__main__":
    # note: these are NOT tests in any way or fashion
    # this is a quick-and-dirty method to check if stuff works
    lca = LicenseCompatibilityAnalyzer(FullCompatibilityCalc())
    lca.extract_raw_licenses(str(Path.cwd())
                             + '/src/data/licenses.json')
    lca.compare_licenses('afl-2.0', 'afl-2.1') # known compatible
    lca.calculate_license_compatibility(['afl-2.0', 'afl-2.1'])
