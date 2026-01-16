import pytest
from pathlib import Path
from src.analyzer.package_metadata_fetcher import PackageMetadataFetcher
from src.entities.package_manager_fetcher import AbstractPackageManagerFetcher
from src.entities.abstract_dep_tree_builder import AbstractDepTreeBuilder
from src.entities.abstract_repo_downloader import AbstractRepoDownloader
from src.entities.pypi_metadata import PyPIMetadata

@pytest.fixture
def mock_pypi_client(mocker):
    return mocker.MagicMock(spec=AbstractPackageManagerFetcher)

@pytest.fixture
def mock_dep_builder(mocker):
    return mocker.MagicMock(spec=AbstractDepTreeBuilder)

@pytest.fixture
def mock_repo_downloader(mocker):
    return mocker.MagicMock(spec=AbstractRepoDownloader)

@pytest.fixture
def fetcher(mock_pypi_client, mock_dep_builder, mock_repo_downloader):
    return PackageMetadataFetcher(mock_pypi_client, mock_dep_builder, mock_repo_downloader)

def test_parse_requirements_file_success(fetcher, mocker):
    """Test parsing of a valid requirements.txt content."""
    # Use actual newline character for mock data
    content = "requests\nnumpy==1.0.0\n# comment"
    
    mocker.patch("builtins.open", mocker.mock_open(read_data=content))
    mocker.patch("os.path.exists", return_value=True) 
    
    result = fetcher._parse_requirements_file(Path("reqs.txt"))
            
    assert "requests" in result
    assert len(result) == 2

def test_build_package_metadata_flow(fetcher, mock_dep_builder, mock_pypi_client, tmp_path, mocker):
    """Test the main flow: parse -> build tree -> fetch metadata."""
    req_file = Path("dummy.txt")
    
    # Mock dependency tree building
    mock_dep_builder.create_venv.return_value = "venv_path"
    mock_dep_builder.get_tree_json.return_value = "json_tree"
    mock_dep_builder.build_map.return_value = {"pkgA": ["pkgB"], "pkgB": []}
    mock_dep_builder.has_cycles.return_value = False
    
    # Mock PyPI fetching
    mock_pypi_client.get_source_links.return_value = {
        "pkgA": {"license": "MIT", "link": "http://a"},
        "pkgB": {"license": "BSD", "link": "http://b"}
    }

    # Use patch context to mock internal methods and file I/O
    mocker.patch.object(fetcher, '_parse_requirements_file', return_value=["pkgA"])
    mocker.patch.object(fetcher, '_load_cache', return_value={})
    mocker.patch.object(fetcher, '_save_cache')
    # Patch PROJECT_ROOT to verify it doesn't try to write to real fs
    mocker.patch('src.analyzer.package_metadata_fetcher.PROJECT_ROOT', tmp_path)
    
    metadata, graph = fetcher.build_package_metadata(req_file, override_cache=True)
                
    assert len(metadata) == 3  # pkgA, pkgB, + Root
    assert graph["Root"] == ["pkgA"]
    assert graph["pkgA"] == ["pkgB"]
    
    pkg_a_meta = next(m for m in metadata if m.package == "pkgA")
    assert pkg_a_meta.license_type == "MIT"

def test_get_package_metadata_found(fetcher):
    """Test retrieving metadata for an existing package."""
    meta = PyPIMetadata("pkgA", "MIT", "http://a")
    fetcher.packages_metadata = [meta]
    
    res = fetcher.get_package_metadata("pkgA")
    assert res.package == "pkgA"
    assert res.license_type == "MIT"

def test_get_package_metadata_not_found(fetcher):
    """Test KeyError when package is not found."""
    fetcher.packages_metadata = []
    with pytest.raises(KeyError):
        fetcher.get_package_metadata("unknown")
