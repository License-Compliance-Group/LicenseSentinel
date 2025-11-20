import os

# Create program-wide logging facility
import logging
logger = logging.getLogger("LicenseSentinel")

from analyzer import packageMetadataFetcher
from Scripts import logger_formatter


def main():

    # Establish logging

    logger.debug("Working directory: %s" , os.getcwd())

    file_path = "requirements.txt"

    if not os.path.exists(file_path):
        logger.warning("File not found!")
    else:
        logger.debug("File loaded: ", file_path)

    finder = packageMetadataFetcher.PyMetadataBuilder(file_path)
    for pkg in finder:
        print(f"{pkg.package} | {pkg.license} | {pkg.link}")



if __name__ == "__main__":
    logger_formatter.LoggerFormatter.initialize(logging.DEBUG)
    main()
