# pylint: disable=missing-function-docstring, missing-module-docstring, invalid-name, missing-class-docstring

from pathlib import Path
from typing import Optional, Dict, Any

import pytest

from src.license_sentinel.entities.scan_engine import ScanEngine


def test_protocol_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ScanEngine()  # type: ignore


def test_run_scan_not_implemented():
    class DummyEngine(ScanEngine):
        def run_scan(self, scan_path, pkg, override_cache):
            raise NotImplementedError

        def scan_for_license(self, scan_path, pkg, override_cache):
            raise NotImplementedError

    engine = DummyEngine()

    with pytest.raises(NotImplementedError):
        engine.run_scan(Path("."), "pkg", False)


def test_scan_for_license_not_implemented():
    class DummyEngine(ScanEngine):
        def run_scan(self, scan_path, pkg, override_cache):
            raise NotImplementedError

        def scan_for_license(self, scan_path, pkg, override_cache):
            raise NotImplementedError

    engine = DummyEngine()

    with pytest.raises(NotImplementedError):
        engine.scan_for_license(Path("."), "pkg", False)


def test_valid_concrete_implementation():
    class ConcreteEngine(ScanEngine):
        def run_scan(
            self, scan_path: Path, pkg: str, override_cache: Optional[bool]
        ) -> Optional[Dict[str, Any]]:
            return {"license": "MIT"}

        def scan_for_license(
            self, scan_path: Path, pkg: str, override_cache: Optional[bool]
        ) -> tuple[str]:
            return ("MIT",)

    engine = ConcreteEngine()

    assert engine.run_scan(Path("."), "pkg", False) == {"license": "MIT"}
    assert engine.scan_for_license(Path("."), "pkg", False) == ("MIT",)


def test_incomplete_implementation_fails():
    class BadEngine(ScanEngine):
        def run_scan(self, scan_path, pkg, override_cache):
            return None

        def scan_for_license(self, scan_path, pkg, override_cache):
            raise NotImplementedError

    engine = BadEngine()

    assert engine.run_scan(Path("."), "pkg", False) is None

    with pytest.raises(NotImplementedError):
        engine.scan_for_license(Path("."), "pkg", False)
