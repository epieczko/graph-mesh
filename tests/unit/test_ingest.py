"""
Unit tests for ingest dispatcher.

Tests cover:
- Converter registry
- Source identifier extraction
- Convert config extraction
- Single file ingestion (XSD, JSON)
- Multi-file XSD ingestion
- Error handling for missing converters
- Error handling for missing fetched paths
- Output directory creation
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from rdflib import Graph

from graph_mesh_orchestrator.ingest import (
    CONVERTER_REGISTRY,
    _get_identifier,
    _get_convert_config,
    run_ingest,
)


class TestConverterRegistry:
    """Test converter registry configuration."""

    @pytest.mark.unit
    def test_registry_has_xsd_converter(self):
        """Test that XSD converter is registered."""
        assert "xsd" in CONVERTER_REGISTRY
        assert callable(CONVERTER_REGISTRY["xsd"])

    @pytest.mark.unit
    def test_registry_has_json_converter(self):
        """Test that JSON converter is registered."""
        assert "json" in CONVERTER_REGISTRY
        assert callable(CONVERTER_REGISTRY["json"])

    @pytest.mark.unit
    def test_registry_keys(self):
        """Test that registry has expected converter types."""
        assert set(CONVERTER_REGISTRY.keys()) == {"xsd", "json"}


class TestGetIdentifier:
    """Test source identifier extraction."""

    @pytest.mark.unit
    def test_extract_from_object_with_identifier_attr(self):
        """Test extracting identifier from object with 'identifier' attribute."""
        source = Mock()
        source.identifier = "test-source"

        result = _get_identifier(source)

        assert result == "test-source"

    @pytest.mark.unit
    def test_extract_from_dict_with_id_key(self):
        """Test extracting identifier from dict with 'id' key."""
        source = {"id": "test-source", "other": "data"}

        result = _get_identifier(source)

        assert result == "test-source"

    @pytest.mark.unit
    def test_dict_id_converted_to_string(self):
        """Test that non-string id values are converted to strings."""
        source = {"id": 123}

        result = _get_identifier(source)

        assert result == "123"
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_raises_key_error_when_missing(self):
        """Test that KeyError is raised when identifier is missing."""
        source = {"other": "data"}

        with pytest.raises(KeyError, match="identifier"):
            _get_identifier(source)

    @pytest.mark.unit
    def test_prefers_identifier_attr_over_dict_id(self):
        """Test that 'identifier' attribute takes precedence over dict 'id'."""
        source = Mock()
        source.identifier = "from-attr"
        # Mock also acts like a dict, but identifier should take precedence

        result = _get_identifier(source)

        assert result == "from-attr"


class TestGetConvertConfig:
    """Test convert configuration extraction."""

    @pytest.mark.unit
    def test_extract_from_object_with_convert_attr(self):
        """Test extracting convert config from object with 'convert' attribute."""
        source = Mock()
        source.convert = {"type": "xsd", "merge": True}

        result = _get_convert_config(source)

        assert result == {"type": "xsd", "merge": True}

    @pytest.mark.unit
    def test_extract_from_dict_with_convert_key(self):
        """Test extracting convert config from dict with 'convert' key."""
        source = {"id": "test", "convert": {"type": "json"}}

        result = _get_convert_config(source)

        assert result == {"type": "json"}

    @pytest.mark.unit
    def test_returns_empty_dict_when_missing(self):
        """Test that empty dict is returned when convert config is missing."""
        source = {"id": "test"}

        result = _get_convert_config(source)

        assert result == {}

    @pytest.mark.unit
    def test_none_convert_returns_empty_dict(self):
        """Test that None convert value returns empty dict."""
        source = Mock()
        source.convert = None

        result = _get_convert_config(source)

        assert result == {}


class TestRunIngest:
    """Test main ingest orchestration."""

    @pytest.mark.unit
    def test_single_xsd_file_ingestion(self, simple_xsd_file, temp_dir):
        """Test ingesting a single XSD file."""
        source = {
            "id": "test-xsd",
            "convert": {"type": "xsd"}
        }
        fetched_paths = {"test-xsd": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        assert "test-xsd" in results
        assert results["test-xsd"].exists()
        assert results["test-xsd"].suffix == ".owl"

        # Verify OWL file is valid
        g = Graph()
        g.parse(str(results["test-xsd"]))
        assert len(g) > 0

    @pytest.mark.unit
    def test_single_json_file_ingestion(self, simple_json_schema_file, temp_dir):
        """Test ingesting a single JSON schema file."""
        source = {
            "id": "test-json",
            "convert": {"type": "json"}
        }
        fetched_paths = {"test-json": str(simple_json_schema_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        assert "test-json" in results
        assert results["test-json"].exists()
        assert results["test-json"].suffix == ".owl"

        # Verify OWL file is valid
        g = Graph()
        g.parse(str(results["test-json"]))
        assert len(g) > 0

    @pytest.mark.unit
    def test_multiple_xsd_files_ingestion(self, multiple_xsd_files, temp_dir):
        """Test ingesting multiple XSD files (merge scenario)."""
        source = {
            "id": "multi-xsd",
            "convert": {"type": "xsd", "merge": True}
        }
        fetched_paths = {"multi-xsd": [str(f) for f in multiple_xsd_files]}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        assert "multi-xsd" in results
        assert results["multi-xsd"].exists()

        # Verify merged OWL file
        g = Graph()
        g.parse(str(results["multi-xsd"]))
        assert len(g) > 0

    @pytest.mark.unit
    def test_multiple_sources(self, simple_xsd_file, simple_json_schema_file, temp_dir):
        """Test ingesting multiple different sources."""
        sources = [
            {"id": "source-1", "convert": {"type": "xsd"}},
            {"id": "source-2", "convert": {"type": "json"}}
        ]
        fetched_paths = {
            "source-1": str(simple_xsd_file),
            "source-2": str(simple_json_schema_file)
        }
        workdir = temp_dir / "artifacts"

        results = run_ingest(sources, fetched_paths, workdir)

        assert len(results) == 2
        assert "source-1" in results
        assert "source-2" in results
        assert results["source-1"].exists()
        assert results["source-2"].exists()

    @pytest.mark.unit
    def test_default_converter_type_is_xsd(self, simple_xsd_file, temp_dir):
        """Test that default converter type is 'xsd' when not specified."""
        source = {
            "id": "default-test",
            "convert": {}  # No type specified
        }
        fetched_paths = {"default-test": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        assert "default-test" in results
        assert results["default-test"].exists()

    @pytest.mark.unit
    def test_output_directory_structure(self, simple_xsd_file, temp_dir):
        """Test that output directory structure is created correctly."""
        source = {"id": "struct-test", "convert": {"type": "xsd"}}
        fetched_paths = {"struct-test": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        # Should create: workdir/converted/source-id/source-id.owl
        expected_dir = workdir / "converted" / "struct-test"
        assert expected_dir.exists()
        assert expected_dir.is_dir()
        assert results["struct-test"].parent == expected_dir

    @pytest.mark.unit
    def test_converted_root_directory_created(self, simple_xsd_file, temp_dir):
        """Test that converted root directory is created."""
        source = {"id": "root-test", "convert": {"type": "xsd"}}
        fetched_paths = {"root-test": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        run_ingest([source], fetched_paths, workdir)

        converted_root = workdir / "converted"
        assert converted_root.exists()
        assert converted_root.is_dir()


class TestIngestErrorHandling:
    """Test error handling in ingest stage."""

    @pytest.mark.unit
    def test_missing_converter_raises_error(self, simple_xsd_file, temp_dir):
        """Test that unknown converter type raises KeyError."""
        source = {
            "id": "invalid-test",
            "convert": {"type": "unknown-format"}
        }
        fetched_paths = {"invalid-test": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        with pytest.raises(KeyError, match="No ingest converter registered"):
            run_ingest([source], fetched_paths, workdir)

    @pytest.mark.unit
    def test_missing_fetched_path_raises_error(self, temp_dir):
        """Test that missing fetched path raises KeyError."""
        source = {"id": "missing-test", "convert": {"type": "xsd"}}
        fetched_paths = {}  # No path for this source
        workdir = temp_dir / "artifacts"

        with pytest.raises(KeyError, match="No fetched artifact found"):
            run_ingest([source], fetched_paths, workdir)

    @pytest.mark.unit
    def test_source_without_identifier_raises_error(self, simple_xsd_file, temp_dir):
        """Test that source without identifier raises KeyError."""
        source = {"convert": {"type": "xsd"}}  # No id
        fetched_paths = {"some-id": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        with pytest.raises(KeyError, match="identifier"):
            run_ingest([source], fetched_paths, workdir)

    @pytest.mark.unit
    def test_empty_sources_returns_empty_dict(self, temp_dir):
        """Test that empty sources list returns empty results."""
        sources = []
        fetched_paths = {}
        workdir = temp_dir / "artifacts"

        results = run_ingest(sources, fetched_paths, workdir)

        assert results == {}

    @pytest.mark.unit
    def test_nonexistent_input_file_propagates_error(self, temp_dir):
        """Test that error from converter is propagated."""
        source = {"id": "bad-file", "convert": {"type": "xsd"}}
        fetched_paths = {"bad-file": "/nonexistent/file.xsd"}
        workdir = temp_dir / "artifacts"

        with pytest.raises(Exception):  # xmlschema will raise
            run_ingest([source], fetched_paths, workdir)


class TestIngestWithSourceObjects:
    """Test ingest with object-based source configurations."""

    @pytest.mark.unit
    def test_source_object_with_attributes(self, simple_xsd_file, temp_dir):
        """Test ingesting with source object (not dict)."""
        source = Mock()
        source.identifier = "obj-source"
        source.convert = {"type": "xsd"}

        fetched_paths = {"obj-source": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        assert "obj-source" in results
        assert results["obj-source"].exists()


class TestIngestOutputVerification:
    """Test output file verification."""

    @pytest.mark.unit
    def test_output_path_follows_convention(self, simple_xsd_file, temp_dir):
        """Test that output path follows naming convention."""
        source = {"id": "my-source", "convert": {"type": "xsd"}}
        fetched_paths = {"my-source": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        output_path = results["my-source"]

        # Path should be: workdir/converted/my-source/my-source.owl
        assert output_path.name == "my-source.owl"
        assert output_path.parent.name == "my-source"
        assert output_path.parent.parent.name == "converted"

    @pytest.mark.unit
    def test_output_is_valid_owl(self, simple_xsd_file, temp_dir):
        """Test that output is valid OWL/RDF."""
        source = {"id": "valid-test", "convert": {"type": "xsd"}}
        fetched_paths = {"valid-test": str(simple_xsd_file)}
        workdir = temp_dir / "artifacts"

        results = run_ingest([source], fetched_paths, workdir)

        # Should be parseable as RDF
        g = Graph()
        g.parse(str(results["valid-test"]))

        # Should have some OWL content
        from rdflib import OWL
        owl_classes = list(g.triples((None, None, OWL.Class)))
        assert len(owl_classes) > 0
