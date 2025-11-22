"""
Creates PackageMetadata from a requirements.txt file
"""
import re
import logging
from infrastructure.pypi_client import PyPiHandler
from entities.pypi_metadata import PyPiMetadata

logger = logging.getLogger(__name__)



# packagesmetadata: list[PyPiMetadata] = []


def py_metadata_builder(file_path):
    """Reads a requirements.txt file and returns a list of dependencies.

        Args:
            file_path (str): The path to the requirements.txt file.
        Returns:
            list (str): A list of dependencies specified in the file.
        """
    # Tiro giù tutto l'albero con pipdeptree e poi verifico
    # per ognuna repo vs pipy.
    # Dopodichè avrò raccolto tutte le licenze e proseguirò a fare un
    # confronto di compatibilità
    # SOLO DEL REPO IN ESAME VS QUELLO
    # noqa: E501 If we will pass the whole tree this should be global
    packagesmetadata: list[PyPiMetadata] = []

    dependencies = []
    pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.split("#")[0].strip()
                match = pattern.match(line)
                if match:
                    dependencies.append(match.group(1))

    except FileNotFoundError:
        logger.error("File not found: %s ", file_path)
    except IOError as e:
        logger.error("An I/O error occurred: %s", e)

    results = PyPiHandler.get_source_links(dependencies)

    for pkg_name, metadata in results.items():
        packagesmetadata.append(PyPiMetadata(
            package=pkg_name,
            license_name=metadata['license'],
            link=metadata['link']
        ))

    # calls PyPiClient and retrieves links, constructing a
    # PyPiMetadata object for each package
    # [question -> depth-first or breadth-first search?
    # Depth-first in my opinion UPDATE!! I've found pipdeptree]
    # then calls RepoDownloader and downloads the repo for each package
    # then calls ScanCodeRunner and creates ScanCodeResults for each repo
    # given a package and its (PyPiMetadata, ScanCodeResults) pair, create
    # PackageMetadata and check that the two licenses match
    # at this point, analyze whether all dependency licenses are compatible
    # with the license of the project being analyzed

    # ↓ I'm not pratical with python but we should ensure
    # encuplation in some way
    return packagesmetadata


def pypi_license_checker():
    """Checks the license of a PyPI-hosted package"""
