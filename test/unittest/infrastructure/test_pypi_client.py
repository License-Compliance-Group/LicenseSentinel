"""Unit tests for PyPiHandler class."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Optional

from src.infrastructure.pypi_client import PyPiHandler


class TestPyPiHandlerGetSourceLinks:
    """Tests for PyPiHandler.get_source_links method."""

    @patch.object(PyPiHandler, "_get_source_links_async")
    def test_get_source_links_single_package(self, mock_async):
        """Test fetching source links for a single package."""
        expected_result = {
            "requests": {
                "license": "Apache 2.0",
                "link": "https://github.com/psf/requests"
            }
        }
        mock_async.return_value = expected_result
        
        handler = PyPiHandler()
        
        with patch("asyncio.run", return_value=expected_result):
            result = handler.get_source_links(["requests"])
        
        assert "requests" in result
        assert result["requests"]["license"] is not None

    @patch.object(PyPiHandler, "_get_source_links_async")
    def test_get_source_links_multiple_packages(self, mock_async):
        """Test fetching source links for multiple packages."""
        expected_result = {
            "requests": {"license": "Apache 2.0", "link": "https://github.com/psf/requests"},
            "numpy": {"license": "BSD", "link": "https://github.com/numpy/numpy"}
        }
        mock_async.return_value = expected_result
        
        handler = PyPiHandler()
        
        with patch("asyncio.run", return_value=expected_result):
            result = handler.get_source_links(["requests", "numpy"])
        
        assert len(result) == 2

    @patch.object(PyPiHandler, "_get_source_links_async")
    def test_get_source_links_empty_list(self, mock_async):
        """Test fetching source links with empty package list."""
        expected_result = {}
        mock_async.return_value = expected_result
        
        handler = PyPiHandler()
        
        with patch("asyncio.run", return_value=expected_result):
            result = handler.get_source_links([])
        
        assert result == {}

    @patch.object(PyPiHandler, "_get_source_links_async")
    def test_get_source_links_custom_timeout(self, mock_async):
        """Test get_source_links with custom timeout."""
        expected_result = {}
        mock_async.return_value = expected_result
        
        handler = PyPiHandler()
        
        with patch("asyncio.run", return_value=expected_result):
            result = handler.get_source_links(["requests"], timeout=20)
        
        assert result == {}

    @patch("asyncio.run")
    @patch.object(PyPiHandler, "_get_source_links_async")
    def test_get_source_links_runtime_error_fallback(self, mock_async, mock_run):
        """Test that get_source_links falls back on RuntimeError."""
        expected_result = {"requests": {"license": "Apache 2.0", "link": None}}
        
        # First call raises RuntimeError, second succeeds
        mock_run.side_effect = RuntimeError("Event loop already running")
        mock_async.return_value = expected_result
        
        handler = PyPiHandler()
        
        with patch("asyncio.new_event_loop"), \
             patch("asyncio.set_event_loop"), \
             patch.object(asyncio.AbstractEventLoop, "run_until_complete", return_value=expected_result):
            result = handler.get_source_links(["requests"])
        
        assert "requests" in result


class TestPyPiHandlerProcessSinglePackage:
    """Tests for PyPiHandler._process_single_package method."""

    @patch.object(PyPiHandler, "fetch_package_json")
    def test_process_single_package_valid(self, mock_fetch):
        """Test processing a valid package."""
        mock_fetch.return_value = {
            "info": {
                "license": "Apache 2.0",
                "project_urls": {
                    "Source": "https://github.com/psf/requests"
                },
                "classifiers": []
            }
        }
        
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("requests", 10)
        
        assert pkg_name == "requests"
        assert data["license"] is not None
        assert data["link"] is not None

    def test_process_single_package_invalid_name(self):
        """Test processing a package with invalid name."""
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("invalid package!", 10)
        
        assert pkg_name == "invalid package!"
        assert data["license"] == "Unknown"
        assert data["link"] is None

    @patch.object(PyPiHandler, "fetch_package_json")
    def test_process_single_package_fetch_fails(self, mock_fetch):
        """Test processing when fetch fails."""
        mock_fetch.return_value = None
        
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("nonexistent", 10)
        
        assert pkg_name == "nonexistent"
        assert data["license"] == "Unknown"
        assert data["link"] is None

    @patch.object(PyPiHandler, "fetch_package_json")
    def test_process_single_package_no_project_urls(self, mock_fetch):
        """Test processing when project_urls is missing."""
        mock_fetch.return_value = {
            "info": {
                "license": "MIT",
                "project_urls": None,
                "classifiers": []
            }
        }
        
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("requests", 10)
        
        assert pkg_name == "requests"
        assert data["link"] is None

    @patch.object(PyPiHandler, "fetch_package_json")
    def test_process_single_package_extracts_source_code_link(self, mock_fetch):
        """Test that Source Code link is properly extracted."""
        mock_fetch.return_value = {
            "info": {
                "license": "MIT",
                "project_urls": {
                    "Source Code": "https://github.com/example/repo"
                },
                "classifiers": []
            }
        }
        
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("requests", 10)
        
        assert data["link"] == "https://github.com/example/repo"

    def test_process_single_package_non_string_input(self):
        """Test processing non-string package name."""
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package(123, 10)
        
        assert data["license"] == "Unknown"
        assert data["link"] is None


class TestPyPiHandlerExtractLicense:
    """Tests for PyPiHandler.extract_license method."""

    def test_extract_license_from_classifiers(self):
        """Test extracting license from classifiers."""
        info = {
            "classifiers": [
                "License :: OSI Approved :: Apache Software License"
            ]
        }
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert "Apache" in result

    def test_extract_license_from_license_field(self):
        """Test extracting license from license field."""
        info = {
            "license": "MIT License",
            "classifiers": []
        }
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert result == "MIT License"

    def test_extract_license_from_license_expression(self):
        """Test extracting license from license_expression field."""
        info = {
            "license_expression": "MIT OR Apache-2.0",
            "classifiers": []
        }
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert "MIT" in result or "Apache" in result

    def test_extract_license_classifier_priority(self):
        """Test that classifiers have priority over other fields."""
        info = {
            "classifiers": [
                "License :: OSI Approved :: MIT License"
            ],
            "license": "Apache 2.0"
        }
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert "MIT" in result

    def test_extract_license_unknown(self):
        """Test that Unknown is returned when no license is found."""
        info = {
            "classifiers": [],
            "license": None,
            "license_expression": None
        }
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert result == "Unknown"

    def test_extract_license_empty_fields(self):
        """Test extraction with empty string fields."""
        info = {
            "classifiers": [],
            "license": "",
            "license_expression": "   "
        }
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert result == "Unknown"

    def test_extract_license_missing_fields(self):
        """Test extraction with missing fields."""
        info = {}
        
        handler = PyPiHandler()
        result = handler.extract_license(info)
        
        assert result == "Unknown"


class TestPyPiHandlerFetchPackageJson:
    """Tests for PyPiHandler.fetch_package_json method."""

    @patch("requests.get")
    def test_fetch_package_json_success(self, mock_get):
        """Test successful JSON fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "info": {
                "name": "requests",
                "license": "Apache 2.0"
            }
        }
        mock_get.return_value = mock_response
        
        handler = PyPiHandler()
        result = handler.fetch_package_json("requests", 10)
        
        assert result is not None
        assert "info" in result

    @patch("requests.get")
    def test_fetch_package_json_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        import requests
        mock_get.side_effect = requests.HTTPError()
        
        handler = PyPiHandler()
        result = handler.fetch_package_json("nonexistent", 10)
        
        assert result is None

    @patch("requests.get")
    def test_fetch_package_json_connection_error(self, mock_get):
        """Test handling of connection errors."""
        import requests
        mock_get.side_effect = requests.ConnectionError()
        
        handler = PyPiHandler()
        result = handler.fetch_package_json("requests", 10)
        
        assert result is None

    @patch("requests.get")
    def test_fetch_package_json_timeout(self, mock_get):
        """Test handling of timeout."""
        import requests
        mock_get.side_effect = requests.Timeout()
        
        handler = PyPiHandler()
        result = handler.fetch_package_json("requests", 1)
        
        assert result is None

    @patch("requests.get")
    def test_fetch_package_json_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        handler = PyPiHandler()
        result = handler.fetch_package_json("requests", 10)
        
        assert result is None

    @patch("requests.get")
    def test_fetch_package_json_custom_timeout(self, mock_get):
        """Test fetch_package_json with custom timeout."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {}}
        mock_get.return_value = mock_response
        
        handler = PyPiHandler()
        handler.fetch_package_json("requests", 30)
        
        # Verify timeout was passed
        assert mock_get.call_args[1]["timeout"] == 30

    @patch("requests.get")
    def test_fetch_package_json_url_format(self, mock_get):
        """Test that correct URL is used."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        handler = PyPiHandler()
        handler.fetch_package_json("requests", 10)
        
        # Verify correct URL is called
        assert "pypi.org/pypi/requests" in mock_get.call_args[0][0]


class TestPyPiHandlerIntegration:
    """Integration tests for PyPiHandler."""

    @patch("requests.get")
    def test_end_to_end_license_and_link_extraction(self, mock_get):
        """Test complete flow of extracting license and link."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "info": {
                "name": "requests",
                "license": None,
                "classifiers": [
                    "License :: OSI Approved :: Apache Software License"
                ],
                "project_urls": {
                    "Source": "https://github.com/psf/requests"
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("requests", 10)
        
        assert pkg_name == "requests"
        assert data["license"] != "Unknown"
        assert data["link"] == "https://github.com/psf/requests"

    @patch("requests.get")
    def test_multiple_package_names_validation(self, mock_get):
        """Test processing multiple packages with validation."""
        handler = PyPiHandler()
        
        # Valid name
        pkg1, data1 = handler._process_single_package("valid-package", 10)
        assert pkg1 == "valid-package"
        
        # Invalid name
        pkg2, data2 = handler._process_single_package("invalid package!", 10)
        assert data2["license"] == "Unknown"

    @patch.object(PyPiHandler, "fetch_package_json")
    def test_project_urls_extraction_priority(self, mock_fetch):
        """Test that correct project URL is selected based on priority."""
        mock_fetch.return_value = {
            "info": {
                "license": "MIT",
                "project_urls": {
                    "Homepage": "https://example.com",
                    "Source": "https://github.com/example/repo",
                    "Documentation": "https://docs.example.com"
                },
                "classifiers": []
            }
        }
        
        handler = PyPiHandler()
        pkg_name, data = handler._process_single_package("requests", 10)
        
        # Source should have priority
        assert "github.com" in data["link"]
