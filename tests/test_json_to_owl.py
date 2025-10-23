"""
Tests for JSON Schema to OWL conversion.
"""
import pytest
import json
from pathlib import Path
from rdflib import Graph
from graph_mesh_ingest.json_to_owl import convert_json_schema_to_owl


class TestJSONToOWL:
    """Test suite for JSON Schema to OWL conversion."""

    @pytest.fixture
    def simple_json_schema(self):
        """Simple JSON schema for testing."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Person",
            "type": "object",
            "properties": {
                "firstName": {
                    "type": "string",
                    "description": "The person's first name"
                },
                "lastName": {
                    "type": "string",
                    "description": "The person's last name"
                },
                "age": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Age in years"
                }
            },
            "required": ["firstName", "lastName"]
        }

    def test_convert_simple_json_schema(self, simple_json_schema, temp_dir):
        """Test conversion of a simple JSON schema."""
        schema_path = temp_dir / "person_schema.json"
        schema_path.write_text(json.dumps(simple_json_schema, indent=2))

        output_path = temp_dir / "person.owl"
        convert_json_schema_to_owl(str(schema_path), str(output_path))

        # Verify output exists
        assert output_path.exists(), "OWL output file should be created"

        # Parse and validate OWL
        graph = Graph()
        graph.parse(str(output_path), format="turtle")
        assert len(graph) > 0, "Converted OWL graph should not be empty"

    def test_json_schema_properties_conversion(self, simple_json_schema, temp_dir):
        """Test that JSON schema properties are converted to OWL properties."""
        schema_path = temp_dir / "person_schema.json"
        schema_path.write_text(json.dumps(simple_json_schema, indent=2))

        output_path = temp_dir / "person.owl"
        convert_json_schema_to_owl(str(schema_path), str(output_path))

        # Parse OWL
        graph = Graph()
        graph.parse(str(output_path), format="turtle")

        # Should contain properties for firstName, lastName, age
        owl_content = graph.serialize(format="turtle")
        assert "firstName" in owl_content or "first_name" in owl_content.lower(), \
            "firstName property should be represented in OWL"
