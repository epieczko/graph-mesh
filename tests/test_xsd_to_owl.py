"""
Tests for XSD to OWL conversion.
"""
import pytest
from pathlib import Path
from rdflib import Graph
from graph_mesh_ingest.xsd_to_owl import convert_xsd_to_owl


class TestXSDToOWL:
    """Test suite for XSD to OWL conversion."""

    @pytest.fixture
    def simple_xsd_content(self):
        """Simple XSD schema for testing."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://example.org/test"
           xmlns:tns="http://example.org/test"
           elementFormDefault="qualified">

    <xs:element name="Person" type="tns:PersonType"/>

    <xs:complexType name="PersonType">
        <xs:sequence>
            <xs:element name="firstName" type="xs:string"/>
            <xs:element name="lastName" type="xs:string"/>
            <xs:element name="age" type="xs:integer" minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>
</xs:schema>'''

    def test_convert_simple_xsd(self, simple_xsd_content, temp_dir):
        """Test conversion of a simple XSD schema."""
        xsd_path = temp_dir / "person.xsd"
        xsd_path.write_text(simple_xsd_content)

        output_path = temp_dir / "person.owl"
        convert_xsd_to_owl(str(xsd_path), str(output_path))

        # Verify output exists
        assert output_path.exists(), "OWL output file should be created"

        # Parse and validate OWL
        graph = Graph()
        graph.parse(str(output_path), format="turtle")
        assert len(graph) > 0, "Converted OWL graph should not be empty"

    def test_xsd_namespace_handling(self, simple_xsd_content, temp_dir):
        """Test that namespace from XSD is preserved in OWL."""
        xsd_path = temp_dir / "person.xsd"
        xsd_path.write_text(simple_xsd_content)

        output_path = temp_dir / "person.owl"
        convert_xsd_to_owl(str(xsd_path), str(output_path))

        # Parse OWL and check for namespace
        graph = Graph()
        graph.parse(str(output_path), format="turtle")

        # Verify namespace preservation
        namespaces = dict(graph.namespaces())
        assert any("example.org/test" in ns for ns in namespaces.values()), \
            "Target namespace should be preserved in OWL"

    def test_invalid_xsd_handling(self, temp_dir):
        """Test error handling for invalid XSD."""
        invalid_xsd = temp_dir / "invalid.xsd"
        invalid_xsd.write_text("This is not valid XML")

        output_path = temp_dir / "output.owl"

        # Should handle gracefully or raise appropriate exception
        with pytest.raises((Exception, ValueError)):
            convert_xsd_to_owl(str(invalid_xsd), str(output_path))
