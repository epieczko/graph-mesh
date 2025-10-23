"""
Pytest configuration and shared fixtures.
"""
import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test artifacts."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_xsd_path():
    """Path to sample XSD schema for testing."""
    return Path(__file__).parent / "fixtures" / "sample.xsd"


@pytest.fixture
def sample_json_schema_path():
    """Path to sample JSON schema for testing."""
    return Path(__file__).parent / "fixtures" / "sample_json_schema.json"


@pytest.fixture
def fixtures_dir():
    """Path to fixtures directory."""
    return Path(__file__).parent / "fixtures"
