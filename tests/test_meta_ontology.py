"""
Tests for meta-ontology creation and validation.
"""
import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from graph_mesh_core.meta_ontology import build_meta_graph, serialize_meta_graph


class TestMetaOntology:
    """Test suite for meta-ontology functionality."""

    def test_build_meta_graph(self):
        """Test that meta-ontology graph is created correctly."""
        graph = build_meta_graph()

        # Verify graph is not empty
        assert len(graph) > 0, "Meta-ontology graph should not be empty"

        # Verify namespace
        META = Namespace("http://graph-mesh.org/meta#")

        # Check for core meta-classes
        expected_classes = [
            "Entity", "Agent", "Contract", "Event",
            "Location", "Regulation", "Metric"
        ]

        for class_name in expected_classes:
            class_uri = META[class_name]
            assert (class_uri, RDF.type, OWL.Class) in graph, \
                f"{class_name} should be defined as OWL Class"

    def test_serialize_meta_graph(self, temp_dir):
        """Test that meta-ontology can be serialized to file."""
        output_path = temp_dir / "meta_ontology.ttl"
        serialize_meta_graph(str(output_path))

        # Verify file was created
        assert output_path.exists(), "Serialized file should exist"

        # Verify file is not empty
        assert output_path.stat().st_size > 0, "Serialized file should not be empty"

        # Verify it can be parsed back
        graph = Graph()
        graph.parse(str(output_path), format="turtle")
        assert len(graph) > 0, "Deserialized graph should not be empty"

    def test_meta_graph_structure(self):
        """Test structural properties of meta-ontology."""
        graph = build_meta_graph()

        # Count OWL classes
        owl_classes = list(graph.subjects(RDF.type, OWL.Class))
        assert len(owl_classes) >= 7, \
            "Should have at least 7 core meta-classes"

        # Verify all classes have labels
        for owl_class in owl_classes:
            labels = list(graph.objects(owl_class, RDFS.label))
            assert len(labels) > 0, \
                f"Class {owl_class} should have an rdfs:label"
