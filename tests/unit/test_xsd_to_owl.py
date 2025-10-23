"""
Unit tests for XSD to OWL converter.

Tests cover:
- Safe IRI generation
- Namespace handling
- Complex type traversal
- Attribute mapping to DatatypeProperty
- Element mapping to ObjectProperty
- XSD type to RDF range mapping
- Multiple XSD file merging
- Conversion report generation
"""

import os
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, URIRef, Literal

from graph_mesh_ingest.xsd_to_owl import (
    local_name_of,
    safe_local,
    iri_for,
    xsd_range_for_simple,
    convert_xsd_to_owl,
    convert_xsd_list_to_owl,
)


# ============================================================================
# Tests for Utility Functions
# ============================================================================

class TestLocalNameOf:
    """Test local name extraction from qualified names."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_extract_from_qname(self):
        """Test extracting local name from {namespace}LocalName format."""
        qname = "{http://example.org/schema}Person"
        assert local_name_of(qname) == "Person"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_plain_name(self):
        """Test handling plain names without namespace."""
        assert local_name_of("Person") == "Person"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_empty_string(self):
        """Test handling empty strings."""
        assert local_name_of("") == "Unnamed"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_namespace_only(self):
        """Test handling namespace without local name."""
        assert local_name_of("{http://example.org/schema}") == "Unnamed"


class TestSafeLocal:
    """Test safe local name generation for URIs."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_alphanumeric_preserved(self):
        """Test that alphanumeric characters are preserved."""
        assert safe_local("Person123") == "Person123"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_special_chars_replaced(self):
        """Test that special characters are replaced with underscores."""
        assert safe_local("My-Type") == "My-Type"  # hyphen is allowed
        assert safe_local("My.Type") == "My.Type"  # dot is allowed
        assert safe_local("My_Type") == "My_Type"  # underscore is allowed
        assert safe_local("My Type") == "My_Type"  # space becomes underscore
        assert safe_local("My@Type") == "My_Type"  # @ becomes underscore

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_qname_extraction_and_safety(self):
        """Test extraction and safety conversion in one step."""
        qname = "{http://example.org}My Type!"
        assert safe_local(qname) == "My_Type_"


class TestIriFor:
    """Test IRI generation from namespace and local name."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_namespace_with_hash(self):
        """Test IRI generation with namespace ending in #."""
        ns = "http://example.org/schema#"
        local = "Person"
        iri = iri_for(ns, local)
        assert str(iri) == "http://example.org/schema#Person"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_namespace_with_slash(self):
        """Test IRI generation with namespace ending in /."""
        ns = "http://example.org/schema/"
        local = "Person"
        iri = iri_for(ns, local)
        assert str(iri) == "http://example.org/schema/Person"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_namespace_without_terminator(self):
        """Test that # is added if namespace doesn't end with / or #."""
        ns = "http://example.org/schema"
        local = "Person"
        iri = iri_for(ns, local)
        assert str(iri) == "http://example.org/schema#Person"

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_none_namespace_uses_fallback(self):
        """Test that None namespace uses fallback."""
        iri = iri_for(None, "Person")
        assert str(iri).startswith("https://graph-mesh.org/schema/")
        assert str(iri).endswith("Person")

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_unsafe_local_name_sanitized(self):
        """Test that unsafe characters in local name are sanitized."""
        ns = "http://example.org/schema#"
        local = "My Type!"
        iri = iri_for(ns, local)
        assert str(iri) == "http://example.org/schema#My_Type_"


class TestXsdRangeForSimple:
    """Test XSD type to RDF range mapping."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_integer_types(self):
        """Test mapping of integer types."""
        # Mock simple type objects
        class MockType:
            def __init__(self, name):
                self.name = name
                self.base_type = None

        int_type = MockType("{http://www.w3.org/2001/XMLSchema}integer")
        assert xsd_range_for_simple(int_type) == XSD.integer

        long_type = MockType("{http://www.w3.org/2001/XMLSchema}long")
        assert xsd_range_for_simple(long_type) == XSD.integer

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_decimal_types(self):
        """Test mapping of decimal/float types."""
        class MockType:
            def __init__(self, name):
                self.name = name
                self.base_type = None

        decimal_type = MockType("{http://www.w3.org/2001/XMLSchema}decimal")
        assert xsd_range_for_simple(decimal_type) == XSD.decimal

        float_type = MockType("{http://www.w3.org/2001/XMLSchema}float")
        assert xsd_range_for_simple(float_type) == XSD.decimal

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_date_types(self):
        """Test mapping of date/time types."""
        class MockType:
            def __init__(self, name):
                self.name = name
                self.base_type = None

        date_type = MockType("{http://www.w3.org/2001/XMLSchema}date")
        assert xsd_range_for_simple(date_type) == XSD.date

        datetime_type = MockType("{http://www.w3.org/2001/XMLSchema}dateTime")
        assert xsd_range_for_simple(datetime_type) == XSD.dateTime

        time_type = MockType("{http://www.w3.org/2001/XMLSchema}time")
        assert xsd_range_for_simple(time_type) == XSD.time

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_boolean_type(self):
        """Test mapping of boolean type."""
        class MockType:
            def __init__(self, name):
                self.name = name
                self.base_type = None

        bool_type = MockType("{http://www.w3.org/2001/XMLSchema}boolean")
        assert xsd_range_for_simple(bool_type) == XSD.boolean

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_unknown_type_defaults_to_string(self):
        """Test that unknown types default to string."""
        class MockType:
            def __init__(self):
                self.name = None
                self.base_type = None

        unknown_type = MockType()
        assert xsd_range_for_simple(unknown_type) == XSD.string


# ============================================================================
# Tests for XSD to OWL Conversion
# ============================================================================

class TestConvertXsdToOwl:
    """Test full XSD to OWL conversion."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_convert_simple_xsd(self, simple_xsd_file, temp_dir):
        """Test conversion of simple XSD schema."""
        output_path = temp_dir / "simple.owl"

        result = convert_xsd_to_owl(str(simple_xsd_file), str(output_path))

        assert result == str(output_path)
        assert output_path.exists()

        # Parse and verify the output
        g = Graph()
        g.parse(str(output_path))

        # Check that classes were created
        classes = list(g.triples((None, RDF.type, OWL.Class)))
        assert len(classes) > 0

        # Check for Person class
        person_classes = [c for c in classes if "Person" in str(c[0])]
        assert len(person_classes) > 0

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_convert_complex_xsd(self, complex_xsd_file, temp_dir):
        """Test conversion of complex XSD with nested types."""
        output_path = temp_dir / "complex.owl"

        result = convert_xsd_to_owl(str(complex_xsd_file), str(output_path))

        assert result == str(output_path)
        assert output_path.exists()

        # Parse and verify
        g = Graph()
        g.parse(str(output_path))

        # Should have multiple classes (Address, Employee, Department, Company)
        classes = list(g.triples((None, RDF.type, OWL.Class)))
        assert len(classes) >= 3

        # Check for specific classes
        class_names = [str(c[0]) for c in classes]
        assert any("Address" in name for name in class_names)
        assert any("Employee" in name for name in class_names)

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_namespace_preservation(self, simple_xsd_file, temp_dir):
        """Test that namespace from XSD is preserved in OWL."""
        output_path = temp_dir / "namespaced.owl"

        convert_xsd_to_owl(str(simple_xsd_file), str(output_path))

        g = Graph()
        g.parse(str(output_path))

        # Check that the target namespace is used
        classes = list(g.triples((None, RDF.type, OWL.Class)))
        assert len(classes) > 0

        # At least one class should use the test namespace
        class_uris = [str(c[0]) for c in classes]
        assert any("test.example.org" in uri for uri in class_uris)

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_datatype_properties_created(self, complex_xsd_file, temp_dir):
        """Test that XSD attributes become OWL DatatypeProperties."""
        output_path = temp_dir / "datatypes.owl"

        convert_xsd_to_owl(str(complex_xsd_file), str(output_path))

        g = Graph()
        g.parse(str(output_path))

        # Check for DatatypeProperties
        datatype_props = list(g.triples((None, RDF.type, OWL.DatatypeProperty)))
        assert len(datatype_props) > 0

        # Check for specific properties
        prop_names = [str(p[0]) for p in datatype_props]
        assert any("employeeId" in name or "department" in name for name in prop_names)

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_object_properties_created(self, complex_xsd_file, temp_dir):
        """Test that XSD elements become OWL ObjectProperties."""
        output_path = temp_dir / "objects.owl"

        convert_xsd_to_owl(str(complex_xsd_file), str(output_path))

        g = Graph()
        g.parse(str(output_path))

        # Check for ObjectProperties
        object_props = list(g.triples((None, RDF.type, OWL.ObjectProperty)))
        assert len(object_props) > 0

        # Check for specific properties
        prop_names = [str(p[0]) for p in object_props]
        assert any("address" in name.lower() for name in prop_names)

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_conversion_report_generated(self, simple_xsd_file, temp_dir):
        """Test that conversion report is generated."""
        output_dir = temp_dir / "with_report"
        output_dir.mkdir()
        output_path = output_dir / "output.owl"

        convert_xsd_to_owl(str(simple_xsd_file), str(output_path))

        report_path = output_dir / "conversion_report.txt"
        assert report_path.exists()

        # Check report content
        report_content = report_path.read_text()
        assert "Classes:" in report_content
        assert "ObjectProperties:" in report_content
        assert "DatatypeProperties:" in report_content

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_output_directory_created(self, simple_xsd_file, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        output_path = temp_dir / "nested" / "dir" / "output.owl"

        convert_xsd_to_owl(str(simple_xsd_file), str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_custom_base_uri(self, simple_xsd_file, temp_dir):
        """Test conversion with custom base URI."""
        output_path = temp_dir / "custom_base.owl"
        custom_uri = "http://custom.example.org/ontology/"

        convert_xsd_to_owl(str(simple_xsd_file), str(output_path), base_uri=custom_uri)

        g = Graph()
        g.parse(str(output_path))

        # The graph should contain triples (may use target namespace over base_uri)
        assert len(g) > 0


class TestConvertXsdListToOwl:
    """Test multi-file XSD to OWL conversion."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_merge_multiple_xsd_files(self, multiple_xsd_files, temp_dir):
        """Test merging multiple XSD files into one OWL ontology."""
        output_path = temp_dir / "merged.owl"

        result = convert_xsd_list_to_owl(
            [str(f) for f in multiple_xsd_files],
            str(output_path)
        )

        assert result == str(output_path)
        assert output_path.exists()

        # Parse and verify
        g = Graph()
        g.parse(str(output_path))

        # Should have classes from both files
        classes = list(g.triples((None, RDF.type, OWL.Class)))
        assert len(classes) >= 2  # At least Identifier and Entity

        # Check for classes from both schemas
        class_names = [str(c[0]) for c in classes]
        # Should have types from both base and extended schemas
        assert any("Identifier" in name or "Entity" in name for name in class_names)

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_merge_single_file(self, simple_xsd_file, temp_dir):
        """Test that merge works with single file."""
        output_path = temp_dir / "single_merged.owl"

        result = convert_xsd_list_to_owl([str(simple_xsd_file)], str(output_path))

        assert result == str(output_path)
        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))
        assert len(g) > 0

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_temporary_files_cleaned_up(self, multiple_xsd_files, temp_dir):
        """Test that temporary files are cleaned up during merge."""
        output_path = temp_dir / "cleanup_test.owl"

        convert_xsd_list_to_owl(
            [str(f) for f in multiple_xsd_files],
            str(output_path)
        )

        # Check that .tmp.owl files don't exist
        temp_files = list(temp_dir.glob("*.tmp.owl"))
        assert len(temp_files) == 0


# ============================================================================
# Integration Tests with Real Data
# ============================================================================

class TestRealWorldXSD:
    """Test conversion with realistic XSD schemas."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_product_catalog_conversion(self, test_data_dir, temp_dir):
        """Test conversion of product catalog XSD."""
        xsd_file = test_data_dir / "xsd" / "product_catalog.xsd"
        if not xsd_file.exists():
            pytest.skip("Product catalog XSD not found")

        output_path = temp_dir / "product_catalog.owl"
        convert_xsd_to_owl(str(xsd_file), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Verify Product class exists
        classes = list(g.triples((None, RDF.type, OWL.Class)))
        class_names = [str(c[0]) for c in classes]
        assert any("Product" in name for name in class_names)

        # Verify properties exist
        props = list(g.triples((None, RDF.type, OWL.DatatypeProperty)))
        assert len(props) > 0

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_xsd_with_annotations(self, test_data_dir, temp_dir):
        """Test that XSD annotations are handled gracefully."""
        xsd_file = test_data_dir / "xsd" / "product_catalog.xsd"
        if not xsd_file.exists():
            pytest.skip("Product catalog XSD not found")

        output_path = temp_dir / "annotated.owl"

        # Should not raise even with annotations
        convert_xsd_to_owl(str(xsd_file), str(output_path))

        assert output_path.exists()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_empty_xsd_schema(self, temp_dir):
        """Test handling of minimal XSD schema."""
        minimal_xsd = temp_dir / "minimal.xsd"
        minimal_xsd.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
</xs:schema>''')

        output_path = temp_dir / "minimal.owl"

        # Should not raise
        convert_xsd_to_owl(str(minimal_xsd), str(output_path))

        assert output_path.exists()

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_xsd_with_special_characters(self, temp_dir):
        """Test XSD with special characters in names."""
        special_xsd = temp_dir / "special.xsd"
        special_xsd.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://test.org/special">
    <xs:complexType name="My-Complex.Type">
        <xs:attribute name="my-attr" type="xs:string"/>
    </xs:complexType>
</xs:schema>''')

        output_path = temp_dir / "special.owl"

        # Should handle special chars by sanitizing
        convert_xsd_to_owl(str(special_xsd), str(output_path))

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path))

        # Verify conversion happened (special chars should be sanitized in URIs)
        classes = list(g.triples((None, RDF.type, OWL.Class)))
        assert len(classes) > 0

    @pytest.mark.unit
    @pytest.mark.xsd
    def test_nonexistent_xsd_raises_error(self, temp_dir):
        """Test that nonexistent XSD file raises appropriate error."""
        nonexistent = temp_dir / "nonexistent.xsd"
        output_path = temp_dir / "output.owl"

        with pytest.raises(Exception):  # xmlschema will raise
            convert_xsd_to_owl(str(nonexistent), str(output_path))
