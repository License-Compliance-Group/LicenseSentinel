"""The main file of the project"""
import os

# Create program-wide logging facility
import logging
from infrastructure import pypi_client
from infrastructure import repo_downloader
from infrastructure import dep_tree_builder

from analyzer import package_metadata_fetcher
from infrastructure import scancode_runner
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

        file_path = "requirements.txt"
    pypi_client_instance = pypi_client.PyPiHandler()
    repo_downloader_instance = repo_downloader.RepoDownloader()
    dep_tree_builder_instance = dep_tree_builder.DepTreeBuilder()
    package_metadata_fetcher_instance = package_metadata_fetcher.PackageMetadataFetcher(
        pypi_client_instance,
        dep_tree_builder_instance,
        repo_downloader_instance
    )
    finder = package_metadata_fetcher_instance.build_package_metadata(
        file_path)
    for pkg in finder:
        print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")
    # finder = package_metadata_fetcher.\
    # build_package_metadata(file_path) # pylint: disable=unused-variable

    # for pkg in finder:
    #    print(f"{pkg.package} | {pkg.license_type} | {pkg.link}")


if __name__ == "__main__":
    main()
