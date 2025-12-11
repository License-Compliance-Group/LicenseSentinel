"""The main file of the project"""
import os

# Create program-wide logging facility
import logging
from infrastructure import pypi_client
from infrastructure import repo_downloader
from infrastructure import dep_tree_builder
from infrastructure.logger_formatter import LoggerFormatter

from analyzer import package_metadata_fetcher

logger = LoggerFormatter.initialize(__name__, logging.DEBUG)


def main():
    """The main function of the project."""
    # Establish logging

    logger.debug("Working directory: %s", os.getcwd())

    file_path = "requirements.txt"

    if not os.path.exists(file_path):
        logger.warning("File not found!")
        return

    logger.debug("File loaded: %s", file_path)

    pypi_client_instance = pypi_client.PyPiHandler()
    repo_downloader_instance = repo_downloader.RepoDownloader()
    dep_tree_builder_instance = dep_tree_builder.DepTreeBuilder()
    package_metadata_fetcher_instance = package_metadata_fetcher.PackageMetadataFetcher(
        pypi_client_instance,
        dep_tree_builder_instance,
        repo_downloader_instance
    )

    metadata_list = package_metadata_fetcher_instance.build_package_metadata(
        file_path)

    if not metadata_list:
        logger.warning("No package metadata found for %s", file_path)
        return

    header = f"{' PACKAGE':<20} {' LICENSE':<40} {' LINK'}"
    print("-" * (len(header) + 40))
    print(header)
    print("-" * (len(header) + 40))

    for name, metadata in metadata_list.items():
        print(f" {metadata.package:<20} {metadata.license_type:<40} {metadata.link}")

    dep_tree_builder_instance.print_full_tree(
        package_metadata_fetcher_instance.get_graph())


if __name__ == "__main__":
    main()
