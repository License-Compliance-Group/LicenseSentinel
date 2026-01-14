# pylint: disable=missing-function-docstring, missing-module-docstring, invalid-name
# I test non richiedono docstring formali e i nomi come test_xxx sono standard pytest.

import pytest
from src.entities.pypi_metadata import PyPIMetadata


# Test del costruttore
def test_init_valid_data():
    # Verifica che il costruttore accetti valori validi
    meta = PyPIMetadata("requests", "Apache-2.0", "https://example.com")

    assert meta.package == "requests"
    assert meta.license_type == "Apache-2.0"
    assert meta.link == "https://example.com"


def test_init_empty_package_raises():
    # Il costruttore deve sollevare un errore se il package è vuoto
    with pytest.raises(ValueError):
        PyPIMetadata("", "MIT", "https://example.com")


# Test proprietà: package
def test_set_valid_package():
    # Verifica che il setter accetti un valore valido
    meta = PyPIMetadata("pkg", None, None)
    meta.package = "newpkg"
    assert meta.package == "newpkg"


def test_set_empty_package_raises():
    # Il setter deve sollevare un errore se il package è vuoto
    meta = PyPIMetadata("pkg", None, None)
    with pytest.raises(ValueError):
        meta.package = ""



# Test proprietà: license_type
def test_set_license_type():
    # Verifica che il setter aggiorni correttamente il valore
    meta = PyPIMetadata("pkg", "MIT", None)
    meta.license_type = "Apache-2.0"
    assert meta.license_type == "Apache-2.0"


def test_set_license_type_none():
    # Verifica che il setter accetti None
    meta = PyPIMetadata("pkg", "MIT", None)
    meta.license_type = None
    assert meta.license_type is None


# Test proprietà: link
def test_set_link():
    # Verifica che il setter aggiorni correttamente il link
    meta = PyPIMetadata("pkg", None, "https://example.com")
    meta.link = "https://new.com"
    assert meta.link == "https://new.com"


def test_set_link_none():
    # Verifica che il setter accetti None
    meta = PyPIMetadata("pkg", None, "https://example.com")
    meta.link = None
    assert meta.link is None


# Test metodo __repr__
def test_repr_contains_fields():
    # Verifica che __repr__ contenga i valori principali
    meta = PyPIMetadata("pkg", "MIT", "https://example.com")
    rep = repr(meta)

    assert "pkg" in rep
    assert "MIT" in rep
    assert "https://example.com" in rep
