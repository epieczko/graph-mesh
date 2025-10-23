"""
Unit tests for JSON Schema to OWL converter.

Tests cover:
- Basic JSON Schema to OWL conversion
- Property extraction and mapping
- Custom base URI handling
- Edge cases and error handling
"""

import json
from pathlib import Path

import pytest
from rdflib import Graph, RDF, RDFS, OWL, Literal

from graph_mesh_ingest.json_to_owl import convert_jsonschema_to_owl


class TestConvertJsonSchemaToOwl:
    """Test JSON Schema to OWL conversion."""

    @pytest.mark.unit
    @pytest.mark.json
    def test_convert_simple_json_schema(self, simple_json_schema_file, temp_dir):
        """Test conversion of simple JSON schema."""
        output_path = temp_dir / "simple.owl"

        result = convert_jsonschema_to_owl(str(simple_json_schema_file), str(output_path))

        assert result == str(output_path)
        assert output_path.exists()

        # Parse and verify
        g = Graph()
        g.parse(str(output_path))

        # Check that properties were created as ObjectProperties
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(props) > 0

        # Check for specific properties (name, age, email)
        prop_names = [str(p[0]) for p in props]
        assert any("name" in name for name in prop_names)

    @pytest.mark.unit
    @pytest.mark.json
    def test_properties_have_labels(self, simple_json_schema_file, temp_dir):
        """Test that converted properties have rdfs:label."""
        output_path = temp_dir / "labeled.owl"

        convert_jsonschema_to_owl(str(simple_json_schema_file), str(output_path))

        g = Graph()
        g.parse(str(output_path))

        # Check that properties have labels
        labels = list(g.triples((None, RDFS.label, None)))
        assert len(labels) > 0

    @pytest.mark.unit
    @pytest.mark.json
    def test_custom_base_uri(self, simple_json_schema_file, temp_dir):
        """Test conversion with custom base URI."""
        output_path = temp_dir / "custom_base.owl"
        custom_uri = "http://custom.example.org/ontology/"

        convert_jsonschema_to_owl(
            str(simple_json_schema_file),
            str(output_path),
            base_uri=custom_uri
        )

        g = Graph()
        g.parse(str(output_path))

        # Check that custom namespace is used
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(props) > 0

        # At least one property should use custom URI
        prop_uris = [str(p[0]) for p in props]
        assert any(custom_uri in uri for uri in prop_uris)

    @pytest.mark.unit
    @pytest.mark.json
    def test_complex_nested_schema(self, complex_json_schema, temp_dir):
        """Test conversion of complex nested JSON schema."""
        # Create temp JSON schema file
        json_file = temp_dir / "complex.json"
        json_file.write_text(json.dumps(complex_json_schema))

        output_path = temp_dir / "complex.owl"

        convert_jsonschema_to_owl(str(json_file), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Should have properties for top-level properties
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        prop_names = [str(p[0]) for p in props]

        # Check for top-level properties
        assert any("companyName" in name for name in prop_names)
        assert any("employees" in name for name in prop_names)
        assert any("address" in name for name in prop_names)

    @pytest.mark.unit
    @pytest.mark.json
    def test_output_directory_created(self, simple_json_schema_file, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        output_path = temp_dir / "nested" / "dir" / "output.owl"

        convert_jsonschema_to_owl(str(simple_json_schema_file), str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.unit
    @pytest.mark.json
    def test_user_profile_conversion(self, test_data_dir, temp_dir):
        """Test conversion of user profile JSON schema."""
        json_file = test_data_dir / "json" / "user_profile.json"
        if not json_file.exists():
            pytest.skip("User profile JSON schema not found")

        output_path = temp_dir / "user_profile.owl"

        convert_jsonschema_to_owl(str(json_file), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Verify properties exist
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(props) > 0

        prop_names = [str(p[0]) for p in props]
        assert any("userId" in name or "username" in name for name in prop_names)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.unit
    @pytest.mark.json
    def test_empty_json_schema(self, temp_dir):
        """Test handling of JSON schema with no properties."""
        empty_schema = {"$schema": "http://json-schema.org/draft-07/schema#"}
        json_file = temp_dir / "empty.json"
        json_file.write_text(json.dumps(empty_schema))

        output_path = temp_dir / "empty.owl"

        # Should not raise
        convert_jsonschema_to_owl(str(json_file), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Should have no properties
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(props) == 0

    @pytest.mark.unit
    @pytest.mark.json
    def test_json_schema_with_special_property_names(self, temp_dir):
        """Test JSON schema with special characters in property names."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "properties": {
                "my-property": {"type": "string"},
                "my.property": {"type": "string"},
                "my_property": {"type": "string"}
            }
        }
        json_file = temp_dir / "special.json"
        json_file.write_text(json.dumps(schema))

        output_path = temp_dir / "special.owl"

        # Should handle special chars
        convert_jsonschema_to_owl(str(json_file), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Should have 3 properties
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(props) == 3

    @pytest.mark.unit
    @pytest.mark.json
    def test_nonexistent_json_file_raises_error(self, temp_dir):
        """Test that nonexistent JSON file raises appropriate error."""
        nonexistent = temp_dir / "nonexistent.json"
        output_path = temp_dir / "output.owl"

        with pytest.raises(FileNotFoundError):
            convert_jsonschema_to_owl(str(nonexistent), str(output_path))

    @pytest.mark.unit
    @pytest.mark.json
    def test_invalid_json_raises_error(self, temp_dir):
        """Test that invalid JSON raises appropriate error."""
        invalid_json = temp_dir / "invalid.json"
        invalid_json.write_text("{ invalid json }")

        output_path = temp_dir / "output.owl"

        with pytest.raises(json.JSONDecodeError):
            convert_jsonschema_to_owl(str(invalid_json), str(output_path))

    @pytest.mark.unit
    @pytest.mark.json
    def test_json_without_properties_key(self, temp_dir):
        """Test JSON schema without 'properties' key."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Test",
            "type": "object"
            # No properties key
        }
        json_file = temp_dir / "no_props.json"
        json_file.write_text(json.dumps(schema))

        output_path = temp_dir / "no_props.owl"

        # Should not raise, just create empty ontology
        convert_jsonschema_to_owl(str(json_file), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Should have no properties
        props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(props) == 0
