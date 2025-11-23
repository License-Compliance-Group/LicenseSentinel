import re
from infrastructure.pypi_client import PyPiHandler
from entities.pypi_metadata import PyPiMetadata

_packagesmetadata: list[PyPiMetadata] = []


def PyMetadataBuilder(file_path):
    """Reads a requirements.txt file and returns a list of dependencies.

        Args:
            file_path (str): The path to the requirements.txt file.
        Returns:
            list (str): A list of dependencies specified in the file.
        """
    # packagesmetadata: list[PyPiMetadata] = []  # noqa: E501 If we will pass the whole tree this should be global

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
        print(f"File not found: {file_path}")
        return []
    except OSError as e:
        print(f"Error reading file {file_path}: {e}")
        return []
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Unexpected error parsing {file_path}: {e}")
        return []


    # Pass requirement to treebuilder to get full dependency tree
    results = PyPiHandler.get_source_links(dependencies)

    for pkg_name, metadata in results.items():
        _packagesmetadata.append(PyPiMetadata(
            package=pkg_name,
            license_type=metadata['license'],
            link=metadata['link']
        ))
        
    # The process should stop here. The user then could click on a dependency on the interactive tree to see its details.
    # At this point the user could launch a check license from source code (ScanCode part)
    # Finally an option "check all tree licenses from source code" outside of the tree 
    # will launch the Downlaod and ScanCode partfor all dependencies.

    # calls PyPiClient and retrieves links, constructing a PyPiMetadata object for each package
    # then calls RepoDownloader and downloads the repo for each package
    # then calls ScanCodeRunner and creates ScanCodeResults for each repo
    # given a package and its (PyPiMetadata, ScanCodeResults) pair, create PackageMetadata and check that the two licenses match
    # at this point, analyze whether all dependency licenses are compatible with the license of the project being analyzed

    # ↓ I'm not pratical with python but we should ensure encuplation in some way
    return _packagesmetadata


def PyPiLicenseChecker():
    pass
