"""The Connectivity class is responsible for the I/O that the program does."""

import requests
from src.infrastructure.logger_formatter import LoggerFormatter
logger = LoggerFormatter.initialize(__name__)

class Connectivity:
    """Implementation of the class"""

    @staticmethod
    def safe_write(path, content):
        """Safely write to a file. Does not raise.
        Note: if a file does not exist, this will create one.

        Args:
            path (path): A path to write to
            content (any): Whatever to put into the file

        Yields:
            bool: Was the write successful?
        """
        try:
            # w+ instead of w just makes the file instead of throwing.
            with open(path, 'w+', encoding='utf-8') as f:
                f.write(content)
        except IOError as ex:
            logger.warning("Could not create file: %s", ex)
            return False
        return True

    @staticmethod
    def safe_read(path):
        """Safely read from a file. Does not raise.

        Args:
            path (path): A path to read from

        Yields:
            content: File's contents, None if read failed
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, AttributeError) as ex:
            logger.warning("Could not read from file: %s", ex)
            return None
        return content
    @staticmethod
    def verify_internet_access(host = "https://example.com",timeout = 30):
        """We need internet access to download the matrix file."""
        # Connect to a known-up server
        try:
            logger.info("Verifying internet access. This will take up to %d" +
            "seconds, depending on your network quality.", timeout)
            req = requests.head(host, timeout=timeout)
            req.raise_for_status()
            return True
        except requests.HTTPError as e:
            logger.warning("Checking internet connection failed, status code %s.",
            format(e.response.status_code))
        except requests.ConnectionError:
            logger.warning("No internet connection available.")
        return False

    @staticmethod
    def download_file(url, timeout = 30, max_size = 5 * 1024 * 1024):
        """Download any file from anywhere. Basically a discount curl.

        Args:
            url (str): URL to the resource
            timeout (int, optional): Amount (in seconds), after which a\
                 download will be considered failed. Defaults to 30.
            max_size (int, optional): Maximum size of payload (in bytes).\
                 Defaults to 5*1024*1024 = 5MB.

        Raises:
            ValueError: Server indicates a response will be too large.
            ValueError: Request timed out or an I/O error happened.

        Returns:
            Response: A response object, None on a failure.
        """
        if not Connectivity.verify_internet_access():
            logger.warning('Offline: cannot download file.')
            return None
        # Try downloading
        try:
            logger.debug('Downloading from %s...', url)
            response = requests.get(url, timeout = timeout)
            response.raise_for_status()
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > max_size:
                raise ValueError('Response too large')

        except (requests.exceptions.Timeout, ValueError) as ex:
            logger.error("Could not download a file from %s, because an "+
            "exception occurred: %s", url, ex)
            return None
        return response
