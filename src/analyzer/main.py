"""The main file of the project"""
import os

# Create program-wide logging facility
import logging
from analyzer import package_metadata_fetcher
from infrastructure.logger_formatter import LoggerFormatter

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)

def main():
    """The main function of the project."""
    # Establish logging

    logger.debug("Working directory: %s", os.getcwd())

    file_path = "requirements.txt"

    if not os.path.exists(file_path):
        logger.warning("File not found!")
    else:
        logger.debug("File loaded: %s", file_path)

    finder = package_metadata_fetcher.PyMetadataBuilder(file_path)
    for pkg in finder:
        print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")



if __name__ == "__main__":
    main()
