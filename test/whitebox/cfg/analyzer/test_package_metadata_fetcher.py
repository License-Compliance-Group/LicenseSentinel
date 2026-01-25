"""
CFG Coverage Tests for package_metadata_fetcher.py

This module implements control flow graph coverage testing based on the CFG
extracted by py2cfg. It aims for path coverage where possible, falling back
to edge coverage or block coverage.

Note: The current code does not have if __name__ == "__main__" block,
but the CFG indicates it should. Testing only the import path that exists.

From the CFG log, the file has blocks:
- Block 1: Import statements and class definition (executed on import)
- Block 247: if __name__ == "__main__" check (not present in current code)
- Block 248: Main execution body (calls pypi_license_checker()) (not present in current code)

Paths to cover:
1. Import path: Block 1 (executed on import)
2. All conditional paths in methods with complex logic
"""

import sys
import os
import json
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
from src.license_hierarchy.analyzer.package_metadata_fetcher import PackageMetadataFetcher
from src.license_hierarchy.entities.pypi_metadata import PyPIMetadata

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestPackageMetadataFetcher(unittest.TestCase):
    """Test class for CFG coverage of package_metadata_fetcher.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_pypi_client = MagicMock()
        self.mock_dep_builder = MagicMock()
        self.mock_repo_downloader = MagicMock()

        # Mock the dep builder methods
        self.mock_dep_builder.create_venv.return_value = '/tmp/test_venv'
        self.mock_dep_builder.install_packages.return_value = None
        self.mock_dep_builder.get_tree_json.return_value = {'requests': []}
        self.mock_dep_builder.build_map.return_value = {'requests': []}
        self.mock_dep_builder.has_cycles.return_value = False

        # Mock pypi client with dynamic return based on input
        def mock_get_source_links(packages_list):
            result = {}
            for pkg in packages_list:
                if pkg == 'requests':
                    result[pkg] = {'license': 'Apache-2.0', 'link': 'https://github.com/psf/requests'}
                elif pkg == 'flask':
                    result[pkg] = {'license': 'BSD', 'link': 'https://github.com/pallets/flask'}
                else:
                    result[pkg] = {'license': 'MIT', 'link': None}
            return result

        self.mock_pypi_client.get_source_links.side_effect = mock_get_source_links

        self.fetcher = PackageMetadataFetcher(
            self.mock_pypi_client,
            self.mock_dep_builder,
            self.mock_repo_downloader
        )

    def test_block_coverage_import(self):
        """Test Block 1 coverage - import and class definition"""
        # Importing the module executes Block 1
        from src.license_hierarchy.analyzer import package_metadata_fetcher

        # Verify the class is available (Block 1 executed)
        self.assertTrue(hasattr(package_metadata_fetcher, 'PackageMetadataFetcher'))

    def test_class_instantiation(self):
        """Test class instantiation and basic functionality"""
        fetcher = PackageMetadataFetcher(
            self.mock_pypi_client,
            self.mock_dep_builder,
            self.mock_repo_downloader
        )

        # Verify Block 1 executed (class instantiated)
        self.assertIsInstance(fetcher, PackageMetadataFetcher)

    def test_pypi_license_checker_raises(self):
        """Test that pypi_license_checker raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.fetcher.pypi_license_checker()

    def test_build_package_metadata_path_coverage(self):
        """Test path coverage for build_package_metadata method"""
        # Create a temporary requirements.txt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('requests\n')
            temp_file = Path(f.name)

        try:
            # Path 1: Normal execution
            metadata, graph = self.fetcher.build_package_metadata(temp_file)
            self.assertIsInstance(metadata, list)
            self.assertIsInstance(graph, dict)

            # Path 2: Override cache
            metadata, graph = self.fetcher.build_package_metadata(temp_file, override_cache=True)
            self.assertIsInstance(metadata, list)

        finally:
            temp_file.unlink()

    def test_get_package_metadata_path_coverage(self):
        """Test path coverage for get_package_metadata method"""
        # First build some metadata
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('requests\n')
            temp_file = Path(f.name)

        try:
            self.fetcher.build_package_metadata(temp_file)

            # Path 1: Found package (exact match)
            meta = self.fetcher.get_package_metadata('requests')
            self.assertIsNotNone(meta)
            self.assertEqual(meta.package, 'requests')

            # Path 2: Found package (case-insensitive match)
            meta = self.fetcher.get_package_metadata('REQUESTS')
            self.assertIsNotNone(meta)
            self.assertEqual(meta.package, 'requests')

            # Path 3: Package not found
            with self.assertRaises(KeyError):
                self.fetcher.get_package_metadata('nonexistent')

            # Path 4: None package_name
            with self.assertRaises(KeyError):
                self.fetcher.get_package_metadata(None)

        finally:
            temp_file.unlink()

    @patch('src.license_hierarchy.analyzer.package_metadata_fetcher.PackageMetadataFetcher.cache_file')
    def test_load_cache_path_coverage(self, mock_cache_file):
        """Test path coverage for _load_cache method"""
        # Mock cache file property
        mock_cache_file.__get__ = MagicMock(return_value=Path('/tmp/test_cache.json'))

        # Path 1: Cache file exists and loads successfully
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"test": "data"}')), \
             patch('json.load', return_value={'test': 'data'}):
            result = self.fetcher._load_cache()
            self.assertEqual(result, {'test': 'data'})

        # Path 2: Cache file exists but JSON loading fails
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('json.load', side_effect=json.JSONDecodeError('test', 'test', 0)):
            result = self.fetcher._load_cache()
            self.assertEqual(result, {})

        # Path 3: Cache file exists but open fails (OSError)
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', side_effect=OSError('test')):
            result = self.fetcher._load_cache()
            self.assertEqual(result, {})

        # Path 4: Cache file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            result = self.fetcher._load_cache()
            self.assertEqual(result, {})

    @patch('src.license_hierarchy.analyzer.package_metadata_fetcher.PackageMetadataFetcher.cache_file')
    def test_save_cache_path_coverage(self, mock_cache_file):
        """Test path coverage for _save_cache method"""
        # Mock cache file property
        mock_cache_file.__get__ = MagicMock(return_value=Path('/tmp/test_cache.json'))

        # Path 1: Save succeeds
        with patch('builtins.open', mock_open()), \
             patch('json.dump') as mock_dump:
            self.fetcher._save_cache({'test': 'data'})
            mock_dump.assert_called_once()

        # Path 2: Save fails with OSError
        with patch('builtins.open', side_effect=OSError('test')):
            # Should not raise, just log warning
            self.fetcher._save_cache({'test': 'data'})

    def test_parse_requirements_file_path_coverage(self):
        """Test path coverage for _parse_requirements_file method"""
        # Path 1: File not found
        result = self.fetcher._parse_requirements_file(Path('/nonexistent/file.txt'))
        self.assertEqual(result, [])

        # Path 2: Valid file with various formats
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('# Comment line\n')
            f.write('requests>=2.0.0\n')
            f.write('flask\n')
            f.write('django==3.2.0\n')
            f.write('\n')  # Empty line
            f.write('invalid-package-name!\n')  # Invalid format
            temp_file = Path(f.name)

        try:
            result = self.fetcher._parse_requirements_file(temp_file)
            # Should contain valid packages but not comments, empty lines, or unsafe formats
            # Invalid formats are normalized back into compliance, if possible.
            self.assertIn('requests', result)
            self.assertIn('flask', result)
            self.assertIn('django', result)
            self.assertIn('invalid-package-name', result)
            self.assertEqual(len(result), 4)  # Only valid/made-valid packages

        finally:
            temp_file.unlink()

        # Path 3: File with potentially unsafe package names
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('safe-package\n')
            f.write('../unsafe\n')
            f.write('/absolute/path\n')
            f.write('.hidden\n')
            temp_file = Path(f.name)

        try:
            result = self.fetcher._parse_requirements_file(temp_file)
            # Should only contain the safe package
            self.assertEqual(result, ['safe-package'])

        finally:
            temp_file.unlink()

        # Path 4: File with package name too long
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('normal-package\n')
            f.write('a' * 150 + '\n')  # Too long
            temp_file = Path(f.name)

        try:
            result = self.fetcher._parse_requirements_file(temp_file)
            # Should only contain the normal package
            self.assertEqual(result, ['normal-package'])

        finally:
            temp_file.unlink()

    def test_deptree_handler_path_coverage(self):
        """Test path coverage for _deptree_handler method"""
        # Path 1: No cycles detected
        self.mock_dep_builder.has_cycles.return_value = False
        graph, all_packages = self.fetcher._deptree_handler(['requests'])
        self.assertIsInstance(graph, dict)
        self.assertIsInstance(all_packages, set)

        # Path 2: Cycles detected
        self.mock_dep_builder.has_cycles.return_value = True
        graph, all_packages = self.fetcher._deptree_handler(['requests'])
        self.assertIsInstance(graph, dict)
        self.assertIsInstance(all_packages, set)

    def test_load_pypi_metadata_path_coverage(self):
        """Test path coverage for _load_pypi_metadata method"""
        packages = {'requests', 'flask'}

        # Path 1: Override cache = True
        result = self.fetcher._load_pypi_metadata(packages, override_cache=True)
        self.assertIsInstance(result, dict)
        self.mock_pypi_client.get_source_links.assert_called_with(list(packages))

        # Reset mock
        self.mock_pypi_client.reset_mock()

        # Path 2: Override cache = False, all packages cached
        with patch.object(self.fetcher, '_load_cache', return_value={
            'requests': {'license': 'MIT', 'link': None},
            'flask': {'license': 'BSD', 'link': None}
        }):
            result = self.fetcher._load_pypi_metadata(packages, override_cache=False)
            self.assertIsInstance(result, dict)
            # Should not call get_source_links since all cached
            self.mock_pypi_client.get_source_links.assert_not_called()

        # Path 3: Override cache = False, some packages missing from cache
        with patch.object(self.fetcher, '_load_cache', return_value={
            'requests': {'license': 'MIT', 'link': None}
            # flask missing
        }), \
             patch.object(self.fetcher, '_save_cache') as mock_save:
            result = self.fetcher._load_pypi_metadata(packages, override_cache=False)
            self.assertIsInstance(result, dict)
            # Should call get_source_links for missing packages
            self.mock_pypi_client.get_source_links.assert_called_with(['flask'])
            # Should update cache
            mock_save.assert_called()

    def test_download_sources_path_coverage(self):
        """Test path coverage for download_sources method"""
        # Create a fresh fetcher for each test to avoid mock state issues
        fresh_fetcher = PackageMetadataFetcher(
            self.mock_pypi_client,
            self.mock_dep_builder,
            MagicMock()  # Fresh repo downloader mock
        )

        package_urls = {
            'pkg1': 'https://github.com/user/repo1',
            'pkg2': 'https://github.com/user/repo2',
            'pkg3': None  # No URL
        }

        # Mock DOWNLOAD_DIRECTORY to use temp dir
        with patch('src.license_hierarchy.analyzer.package_metadata_fetcher.DOWNLOAD_DIRECTORY', Path('/tmp')):
            # Path 1: Override cache = True
            fresh_fetcher.download_sources(package_urls, override_cache=True)
            # Should call download_repos with all valid URLs
            fresh_fetcher.repo_downloader.download_repos.assert_called()

            # Path 2: Override cache = False, some files cached
            fresh_fetcher2 = PackageMetadataFetcher(
                self.mock_pypi_client,
                self.mock_dep_builder,
                MagicMock()
            )
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True  # All files cached
                fresh_fetcher2.download_sources(package_urls, override_cache=False)
                # Should not call download_repos
                fresh_fetcher2.repo_downloader.download_repos.assert_not_called()

            # Path 3: Override cache = False, no cached files
            fresh_fetcher3 = PackageMetadataFetcher(
                self.mock_pypi_client,
                self.mock_dep_builder,
                MagicMock()
            )
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = False  # No files cached
                fresh_fetcher3.download_sources(package_urls, override_cache=False)
                # Should call download_repos for valid URLs
                fresh_fetcher3.repo_downloader.download_repos.assert_called()

            # Path 4: No valid repository links
            fresh_fetcher4 = PackageMetadataFetcher(
                self.mock_pypi_client,
                self.mock_dep_builder,
                MagicMock()
            )
            fresh_fetcher4.download_sources({'pkg1': None, 'pkg2': None}, override_cache=False)
            # Should not call download_repos
            fresh_fetcher4.repo_downloader.download_repos.assert_not_called()

    def test_build_package_metadata_error_paths(self):
        """Test error paths in build_package_metadata method"""
        # Path 1: No dependencies found (empty requirements file)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('# Just comments\n\n')
            temp_file = Path(f.name)

        try:
            with self.assertRaises(RuntimeError):
                self.fetcher.build_package_metadata(temp_file)
        finally:
            temp_file.unlink()

        # Path 2: Dependency tree building fails
        self.mock_dep_builder.build_map.side_effect = RuntimeError("Build failed")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('requests\n')
            temp_file = Path(f.name)

        try:
            metadata, graph = self.fetcher.build_package_metadata(temp_file)
            self.assertEqual(metadata, [])
            self.assertEqual(graph, {})
        finally:
            temp_file.unlink()
            self.mock_dep_builder.build_map.side_effect = None

    def test_get_graph_method(self):
        """Test get_graph method returns a deep copy"""
        # Set up some graph data
        self.fetcher.graph = {'test': ['dep1', 'dep2']}

        result = self.fetcher.get_graph()
        self.assertEqual(result, {'test': ['dep1', 'dep2']})

        # Modify the result and ensure original is unchanged (deep copy)
        result['test'].append('dep3')
        self.assertEqual(self.fetcher.graph, {'test': ['dep1', 'dep2']})

    def test_get_package_metadata_malformed_object(self):
        """Test get_package_metadata with malformed PyPIMetadata object"""
        # Create a malformed metadata object
        malformed_meta = MagicMock()
        malformed_meta.package = None  # Missing package attribute
        self.fetcher.packages_metadata = [malformed_meta]

        with self.assertRaises(ValueError):
            self.fetcher.get_package_metadata('test')


if __name__ == '__main__':
    # Run the tests to achieve CFG coverage
    unittest.main()
