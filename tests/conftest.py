"""
Pytest configuration and shared fixtures for graph-mesh tests.

This module provides fixtures for:
- Temporary directories and file management
- Sample test data (XSD, JSON schemas, ontologies)
- Mock Docker containers for matcher testing
- RDF graph comparison utilities
- Pipeline configuration helpers
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest
import yaml
from rdflib import Graph, Namespace, URIRef


# ============================================================================
# Path and Directory Fixtures
# ============================================================================

@pytest.fixture
def test_data_dir() -> Path:
    """Return the path to the test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test artifacts."""
    return tmp_path


@pytest.fixture
def artifacts_dir(temp_dir):
    """Create a temporary artifacts directory structure."""
    artifacts = temp_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "converted").mkdir(exist_ok=True)
    (artifacts / "mappings").mkdir(exist_ok=True)
    return artifacts


# ============================================================================
# Sample XSD Data Fixtures
# ============================================================================

@pytest.fixture
def simple_xsd_content() -> str:
    """Provide a simple XSD schema for testing."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:test="http://test.example.org/schema"
           targetNamespace="http://test.example.org/schema"
           elementFormDefault="qualified">

    <xs:complexType name="Person">
        <xs:sequence>
            <xs:element name="name" type="xs:string"/>
            <xs:element name="age" type="xs:integer"/>
            <xs:element name="email" type="xs:string" minOccurs="0"/>
        </xs:sequence>
        <xs:attribute name="id" type="xs:string" use="required"/>
    </xs:complexType>

    <xs:element name="Person" type="test:Person"/>
</xs:schema>'''


@pytest.fixture
def complex_xsd_content() -> str:
    """Provide a complex XSD schema with nested types and references."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:company="http://company.example.org/schema"
           targetNamespace="http://company.example.org/schema"
           elementFormDefault="qualified">

    <xs:complexType name="Address">
        <xs:sequence>
            <xs:element name="street" type="xs:string"/>
            <xs:element name="city" type="xs:string"/>
            <xs:element name="zipCode" type="xs:string"/>
            <xs:element name="country" type="xs:string"/>
        </xs:sequence>
    </xs:complexType>

    <xs:complexType name="Employee">
        <xs:sequence>
            <xs:element name="firstName" type="xs:string"/>
            <xs:element name="lastName" type="xs:string"/>
            <xs:element name="birthDate" type="xs:date"/>
            <xs:element name="salary" type="xs:decimal"/>
            <xs:element name="active" type="xs:boolean"/>
            <xs:element name="address" type="company:Address"/>
        </xs:sequence>
        <xs:attribute name="employeeId" type="xs:string" use="required"/>
        <xs:attribute name="department" type="xs:string"/>
    </xs:complexType>

    <xs:complexType name="Department">
        <xs:sequence>
            <xs:element name="name" type="xs:string"/>
            <xs:element name="manager" type="company:Employee" minOccurs="0"/>
            <xs:element name="employees" type="company:Employee" minOccurs="0" maxOccurs="unbounded"/>
        </xs:sequence>
    </xs:complexType>

    <xs:element name="Company">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="department" type="company:Department" maxOccurs="unbounded"/>
            </xs:sequence>
            <xs:attribute name="name" type="xs:string" use="required"/>
        </xs:complexType>
    </xs:element>
</xs:schema>'''


@pytest.fixture
def simple_xsd_file(temp_dir, simple_xsd_content) -> Path:
    """Create a temporary XSD file with simple schema."""
    xsd_file = temp_dir / "simple.xsd"
    xsd_file.write_text(simple_xsd_content)
    return xsd_file


@pytest.fixture
def complex_xsd_file(temp_dir, complex_xsd_content) -> Path:
    """Create a temporary XSD file with complex schema."""
    xsd_file = temp_dir / "complex.xsd"
    xsd_file.write_text(complex_xsd_content)
    return xsd_file


@pytest.fixture
def multiple_xsd_files(temp_dir) -> List[Path]:
    """Create multiple related XSD files for multi-file conversion testing."""
    # Base types schema
    base_xsd = temp_dir / "base_types.xsd"
    base_xsd.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:base="http://base.example.org/schema"
           targetNamespace="http://base.example.org/schema">
    <xs:complexType name="Identifier">
        <xs:simpleContent>
            <xs:extension base="xs:string">
                <xs:attribute name="scheme" type="xs:string"/>
            </xs:extension>
        </xs:simpleContent>
    </xs:complexType>
</xs:schema>''')

    # Extended schema importing base
    extended_xsd = temp_dir / "extended.xsd"
    extended_xsd.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:ext="http://extended.example.org/schema"
           xmlns:base="http://base.example.org/schema"
           targetNamespace="http://extended.example.org/schema">
    <xs:import namespace="http://base.example.org/schema" schemaLocation="base_types.xsd"/>
    <xs:complexType name="Entity">
        <xs:sequence>
            <xs:element name="id" type="base:Identifier"/>
            <xs:element name="name" type="xs:string"/>
        </xs:sequence>
    </xs:complexType>
</xs:schema>''')

    return [base_xsd, extended_xsd]


# ============================================================================
# Sample JSON Schema Data Fixtures
# ============================================================================

@pytest.fixture
def simple_json_schema() -> Dict[str, Any]:
    """Provide a simple JSON schema for testing."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://test.example.org/person-schema",
        "title": "Person",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["name"]
    }


@pytest.fixture
def complex_json_schema() -> Dict[str, Any]:
    """Provide a complex JSON schema with nested objects."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://test.example.org/company-schema",
        "title": "Company",
        "type": "object",
        "properties": {
            "companyName": {"type": "string"},
            "employees": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "firstName": {"type": "string"},
                        "lastName": {"type": "string"},
                        "position": {"type": "string"},
                        "salary": {"type": "number"}
                    },
                    "required": ["firstName", "lastName"]
                }
            },
            "address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                    "country": {"type": "string"}
                }
            }
        },
        "required": ["companyName"]
    }


@pytest.fixture
def simple_json_schema_file(temp_dir, simple_json_schema) -> Path:
    """Create a temporary JSON schema file."""
    import json
    json_file = temp_dir / "simple_schema.json"
    json_file.write_text(json.dumps(simple_json_schema, indent=2))
    return json_file


# ============================================================================
# Sample Ontology Fixtures
# ============================================================================

@pytest.fixture
def sample_ontology_graph() -> Graph:
    """Create a sample RDF graph for testing."""
    g = Graph()
    NS = Namespace("http://test.example.org/ontology#")

    # Add some triples
    g.add((NS.Person, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
           URIRef("http://www.w3.org/2002/07/owl#Class")))
    g.add((NS.name, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
           URIRef("http://www.w3.org/2002/07/owl#DatatypeProperty")))

    return g


@pytest.fixture
def sample_ontology_file(temp_dir, sample_ontology_graph) -> Path:
    """Create a temporary ontology file in Turtle format."""
    owl_file = temp_dir / "sample.owl"
    sample_ontology_graph.serialize(destination=str(owl_file), format="turtle")
    return owl_file


# ============================================================================
# Pipeline Manifest Fixtures
# ============================================================================

@pytest.fixture
def simple_manifest_dict(simple_xsd_file) -> Dict[str, Any]:
    """Provide a simple pipeline manifest configuration."""
    return {
        "name": "test-pipeline",
        "sources": [
            {
                "id": "test-source",
                "fetch": {
                    "type": "local",
                    "path": str(simple_xsd_file)
                },
                "convert": {
                    "type": "xsd"
                }
            }
        ],
        "matchers": ["LogMap"]
    }


@pytest.fixture
def simple_manifest_file(temp_dir, simple_manifest_dict) -> Path:
    """Create a temporary manifest YAML file."""
    manifest_file = temp_dir / "test_manifest.yaml"
    manifest_file.write_text(yaml.dump(simple_manifest_dict))
    return manifest_file


@pytest.fixture
def multi_source_manifest_dict(simple_xsd_file, simple_json_schema_file) -> Dict[str, Any]:
    """Provide a manifest with multiple sources."""
    return {
        "name": "multi-source-pipeline",
        "sources": [
            {
                "id": "xsd-source",
                "fetch": {"type": "local", "path": str(simple_xsd_file)},
                "convert": {"type": "xsd"}
            },
            {
                "id": "json-source",
                "fetch": {"type": "local", "path": str(simple_json_schema_file)},
                "convert": {"type": "json"}
            }
        ],
        "matchers": ["LogMap", "AML"]
    }


# ============================================================================
# Mock Docker Fixtures
# ============================================================================

@pytest.fixture
def mock_docker_client():
    """Provide a mocked Docker client for testing matchers."""
    mock_client = MagicMock()
    mock_container = MagicMock()

    # Configure the mock container
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"Matcher completed successfully"

    # Configure the mock client
    mock_client.containers.run.return_value = mock_container
    mock_client.ping.return_value = True

    return mock_client


@pytest.fixture
def mock_docker_unavailable():
    """Provide a mocked Docker client that simulates Docker being unavailable."""
    mock_client = MagicMock()
    mock_client.ping.side_effect = Exception("Docker daemon not running")
    return mock_client


# ============================================================================
# RDF Comparison Utilities
# ============================================================================

@pytest.fixture
def rdf_graph_comparator():
    """Provide a utility function for comparing RDF graphs."""
    def compare_graphs(graph1: Graph, graph2: Graph) -> Dict[str, Any]:
        """
        Compare two RDF graphs and return differences.

        Returns:
            Dict with keys: 'equal', 'only_in_g1', 'only_in_g2'
        """
        iso = graph1.isomorphic(graph2)
        only_in_g1 = set(graph1) - set(graph2)
        only_in_g2 = set(graph2) - set(graph1)

        return {
            "equal": iso,
            "only_in_g1": only_in_g1,
            "only_in_g2": only_in_g2,
            "triple_count_g1": len(graph1),
            "triple_count_g2": len(graph2)
        }

    return compare_graphs


@pytest.fixture
def assert_owl_class_exists():
    """Provide a utility to check if an OWL class exists in a graph."""
    def check_class(graph: Graph, class_uri: str) -> bool:
        """Check if a class URI exists in the graph as an owl:Class."""
        OWL = Namespace("http://www.w3.org/2002/07/owl#")
        RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")

        class_ref = URIRef(class_uri)
        return (class_ref, RDF.type, OWL.Class) in graph

    return check_class


# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Ensure test data directory exists
    test_dir = Path(__file__).parent
    data_dir = test_dir / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "xsd").mkdir(exist_ok=True)
    (data_dir / "json").mkdir(exist_ok=True)
    (data_dir / "ontology").mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark tests based on path
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Auto-mark based on test name
        if "xsd" in item.nodeid.lower():
            item.add_marker(pytest.mark.xsd)
        if "json" in item.nodeid.lower():
            item.add_marker(pytest.mark.json)
        if "docker" in item.nodeid.lower():
            item.add_marker(pytest.mark.docker)
        if "property" in item.nodeid.lower() or "hypothesis" in item.nodeid.lower():
            item.add_marker(pytest.mark.property)
