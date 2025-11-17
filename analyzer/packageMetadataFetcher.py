import re
from Infrastructure.PyPiClient import PyPiHandler
from Entities.pipyMetadata import PyPiMetadata

# packagesmetadata: list[PyPiMetadata] = []


def PyMetadataBuilder(file_path):
    """Reads a requirements.txt file and returns a list of dependencies.

        Args:
            file_path (str): The path to the requirements.txt file.
        Returns:
            list (str): A list of dependencies specified in the file.
        """
    # Tiro giù tutto l'albero con pipdeptree e poi verifico per ognuna repo vs pipy.
    # Dopodichè avrò raccolto tutte le licenze e proseguirò a fare un confronto di compatibilità
    # SOLO DEL REPO IN ESAME VS QUELLO
    packagesmetadata: list[PyPiMetadata] = []  # noqa: E501 If we will pass the whole tree this should be global

    dependencies = []
    pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.split("#")[0].strip()
                match = pattern.match(line)
                if match:
                    dependencies.append(match.group(1))

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

    results = PyPiHandler.getSourceLinks(dependencies)

    for pkg_name, metadata in results.items():
        packagesmetadata.append(PyPiMetadata(
            package=pkg_name,
            license=metadata['license'],
            link=metadata['link']
        ))

    # calls PyPiClient and retrieves links, constructing a PyPiMetadata object for each package
    # [question -> depth-first or breadth-first search? Depth-first in my opinion UPDATE!! I've found pipdeptree]
    # then calls RepoDownloader and downloads the repo for each package
    # then calls ScanCodeRunner and creates ScanCodeResults for each repo
    # given a package and its (PyPiMetadata, ScanCodeResults) pair, create PackageMetadata and check that the two licenses match
    # at this point, analyze whether all dependency licenses are compatible with the license of the project being analyzed

    # ↓ I'm not pratical with python but we should ensure encuplation in some way
    return packagesmetadata


def PyPiLicenseChecker():
    pass
