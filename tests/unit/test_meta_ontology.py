"""
Unit tests for meta-ontology module.

Tests cover:
- MetaClass dataclass functionality
- META_CLASSES constant correctness
- Meta-ontology graph building
- Graph serialization
- Domain class attachment
- RDF structure validation
"""

from pathlib import Path

import pytest
from rdflib import Graph, RDF, RDFS, Literal, URIRef

from graph_mesh_core.meta_ontology import (
    META_ONTOLOGY_IRI,
    GM,
    MetaClass,
    META_CLASSES,
    build_meta_graph,
    serialize_meta_graph,
    add_domain_classes,
)


class TestMetaClass:
    """Test MetaClass dataclass."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_metaclass_creation(self):
        """Test creating a MetaClass instance."""
        mc = MetaClass("TestEntity", "A test entity")

        assert mc.name == "TestEntity"
        assert mc.comment == "A test entity"

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_metaclass_uri_generation(self):
        """Test URI generation for MetaClass."""
        mc = MetaClass("TestEntity", "A test entity")
        uri = mc.uri()

        assert isinstance(uri, URIRef)
        assert str(uri).startswith(META_ONTOLOGY_IRI)
        assert "TestEntity" in str(uri)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_metaclass_immutability(self):
        """Test that MetaClass is immutable (frozen)."""
        mc = MetaClass("TestEntity", "A test entity")

        with pytest.raises(Exception):  # FrozenInstanceError
            mc.name = "NewName"

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_metaclass_equality(self):
        """Test MetaClass equality comparison."""
        mc1 = MetaClass("Entity", "A thing")
        mc2 = MetaClass("Entity", "A thing")
        mc3 = MetaClass("Entity", "Different comment")

        assert mc1 == mc2
        assert mc1 != mc3


class TestMetaClasses:
    """Test META_CLASSES constant."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_meta_classes_is_tuple(self):
        """Test that META_CLASSES is a tuple."""
        assert isinstance(META_CLASSES, tuple)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_meta_classes_count(self):
        """Test that META_CLASSES contains expected number of classes."""
        # As per the requirements: Entity, Agent, Contract, Event, Location, Regulation, Metric
        assert len(META_CLASSES) == 7

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_meta_classes_names(self):
        """Test that all expected meta-classes are present."""
        expected_names = {
            "Entity", "Agent", "Contract", "Event",
            "Location", "Regulation", "Metric"
        }

        actual_names = {mc.name for mc in META_CLASSES}

        assert actual_names == expected_names

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_all_meta_classes_have_comments(self):
        """Test that all meta-classes have non-empty comments."""
        for mc in META_CLASSES:
            assert mc.comment
            assert len(mc.comment) > 0

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_meta_class_entity_exists(self):
        """Test that the base Entity class exists."""
        entity_classes = [mc for mc in META_CLASSES if mc.name == "Entity"]
        assert len(entity_classes) == 1

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_meta_classes_are_unique(self):
        """Test that all meta-class names are unique."""
        names = [mc.name for mc in META_CLASSES]
        assert len(names) == len(set(names))


class TestBuildMetaGraph:
    """Test meta-ontology graph building."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_build_meta_graph_returns_graph(self):
        """Test that build_meta_graph returns a Graph instance."""
        g = build_meta_graph()
        assert isinstance(g, Graph)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_graph_has_correct_namespace_binding(self):
        """Test that GM namespace is bound correctly."""
        g = build_meta_graph()

        # Check namespace binding
        namespaces = dict(g.namespaces())
        assert "gm" in namespaces
        assert META_ONTOLOGY_IRI in str(namespaces["gm"])

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_graph_contains_all_meta_classes(self):
        """Test that graph contains all META_CLASSES as rdfs:Class."""
        g = build_meta_graph()

        for mc in META_CLASSES:
            # Check that class exists
            assert (mc.uri(), RDF.type, RDFS.Class) in g

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_graph_contains_labels(self):
        """Test that all classes have rdfs:label."""
        g = build_meta_graph()

        for mc in META_CLASSES:
            labels = list(g.triples((mc.uri(), RDFS.label, None)))
            assert len(labels) == 1
            assert labels[0][2] == Literal(mc.name)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_graph_contains_comments(self):
        """Test that all classes have rdfs:comment."""
        g = build_meta_graph()

        for mc in META_CLASSES:
            comments = list(g.triples((mc.uri(), RDFS.comment, None)))
            assert len(comments) == 1
            assert comments[0][2] == Literal(mc.comment)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_graph_triple_count(self):
        """Test that graph has expected number of triples."""
        g = build_meta_graph()

        # Each meta-class has 3 triples: type, label, comment
        expected_triples = len(META_CLASSES) * 3

        assert len(g) == expected_triples

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_build_meta_graph_is_deterministic(self):
        """Test that building graph multiple times produces same result."""
        g1 = build_meta_graph()
        g2 = build_meta_graph()

        # Graphs should be isomorphic
        assert g1.isomorphic(g2)


class TestSerializeMetaGraph:
    """Test meta-ontology serialization."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_serialize_to_turtle(self, temp_dir):
        """Test serialization in Turtle format."""
        output_path = temp_dir / "meta.ttl"

        result = serialize_meta_graph(output_path, format="turtle")

        assert result == output_path
        assert output_path.exists()

        # Verify content by parsing
        g = Graph()
        g.parse(str(output_path), format="turtle")
        assert len(g) > 0

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_serialize_to_xml(self, temp_dir):
        """Test serialization in RDF/XML format."""
        output_path = temp_dir / "meta.owl"

        result = serialize_meta_graph(output_path, format="xml")

        assert result == output_path
        assert output_path.exists()

        # Verify content
        g = Graph()
        g.parse(str(output_path), format="xml")
        assert len(g) > 0

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_serialize_creates_parent_directories(self, temp_dir):
        """Test that parent directories are created if they don't exist."""
        output_path = temp_dir / "nested" / "deep" / "meta.ttl"

        serialize_meta_graph(output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_serialized_graph_content_matches(self, temp_dir):
        """Test that serialized graph contains all expected content."""
        output_path = temp_dir / "meta.ttl"

        serialize_meta_graph(output_path)

        # Parse and verify
        g = Graph()
        g.parse(str(output_path))

        # Should have all META_CLASSES
        for mc in META_CLASSES:
            assert (mc.uri(), RDF.type, RDFS.Class) in g
            assert (mc.uri(), RDFS.label, Literal(mc.name)) in g
            assert (mc.uri(), RDFS.comment, Literal(mc.comment)) in g

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_serialize_to_ntriples(self, temp_dir):
        """Test serialization in N-Triples format."""
        output_path = temp_dir / "meta.nt"

        serialize_meta_graph(output_path, format="nt")

        assert output_path.exists()

        g = Graph()
        g.parse(str(output_path), format="nt")
        assert len(g) == len(META_CLASSES) * 3


class TestAddDomainClasses:
    """Test domain class attachment functionality."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_add_single_domain_class(self):
        """Test adding a single domain class."""
        g = Graph()
        class_iri = "http://example.org/domain#Product"

        result = add_domain_classes(g, [class_iri])

        assert result is g  # Returns same graph
        assert (URIRef(class_iri), RDF.type, RDFS.Class) in g
        assert (URIRef(class_iri), RDFS.subClassOf, GM["Entity"]) in g

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_add_multiple_domain_classes(self):
        """Test adding multiple domain classes."""
        g = Graph()
        class_iris = [
            "http://example.org/domain#Product",
            "http://example.org/domain#Order",
            "http://example.org/domain#Customer"
        ]

        add_domain_classes(g, class_iris)

        # All classes should be added
        for iri in class_iris:
            assert (URIRef(iri), RDF.type, RDFS.Class) in g
            assert (URIRef(iri), RDFS.subClassOf, GM["Entity"]) in g

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_add_domain_classes_to_existing_graph(self):
        """Test adding domain classes to a graph with existing content."""
        g = build_meta_graph()
        initial_size = len(g)

        class_iris = ["http://example.org/domain#Product"]
        add_domain_classes(g, class_iris)

        # Graph should have additional triples
        assert len(g) > initial_size

        # Original content should still be there
        for mc in META_CLASSES:
            assert (mc.uri(), RDF.type, RDFS.Class) in g

        # New content should be there
        assert (URIRef(class_iris[0]), RDFS.subClassOf, GM["Entity"]) in g

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_add_domain_classes_empty_list(self):
        """Test adding no domain classes (empty list)."""
        g = Graph()
        initial_size = len(g)

        add_domain_classes(g, [])

        # Graph should be unchanged
        assert len(g) == initial_size

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_domain_classes_hierarchy(self):
        """Test that domain classes form correct hierarchy with Entity."""
        g = build_meta_graph()
        domain_class = "http://example.org/Product"

        add_domain_classes(g, [domain_class])

        # Domain class should be subclass of Entity
        entity_uri = GM["Entity"]
        assert (URIRef(domain_class), RDFS.subClassOf, entity_uri) in g

        # Entity should still be an rdfs:Class
        assert (entity_uri, RDF.type, RDFS.Class) in g


class TestGraphStructure:
    """Test overall graph structure and correctness."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_no_duplicate_triples(self):
        """Test that graph contains no duplicate triples."""
        g = build_meta_graph()

        # Convert to set to remove duplicates
        triples_list = list(g)
        triples_set = set(triples_list)

        assert len(triples_list) == len(triples_set)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_all_subjects_are_gm_namespace(self):
        """Test that all class subjects use GM namespace."""
        g = build_meta_graph()

        for s, p, o in g:
            if p == RDF.type and o == RDFS.Class:
                assert str(s).startswith(META_ONTOLOGY_IRI)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_graph_consistency(self):
        """Test that graph structure is consistent."""
        g = build_meta_graph()

        # Every class should have exactly 1 label and 1 comment
        classes = set(s for s, p, o in g if p == RDF.type and o == RDFS.Class)

        for cls in classes:
            labels = list(g.triples((cls, RDFS.label, None)))
            comments = list(g.triples((cls, RDFS.comment, None)))

            assert len(labels) == 1, f"Class {cls} should have exactly 1 label"
            assert len(comments) == 1, f"Class {cls} should have exactly 1 comment"


class TestGMNamespace:
    """Test GM namespace constant."""

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_gm_namespace_structure(self):
        """Test that GM namespace has correct structure."""
        gm_str = str(GM)
        assert gm_str.startswith("https://w3id.org/")
        assert "graph-mesh" in gm_str
        assert "meta-ontology" in gm_str

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_gm_namespace_term_access(self):
        """Test accessing terms through GM namespace."""
        entity = GM["Entity"]
        assert isinstance(entity, URIRef)
        assert "Entity" in str(entity)

    @pytest.mark.unit
    @pytest.mark.ontology
    def test_meta_ontology_iri_format(self):
        """Test META_ONTOLOGY_IRI constant format."""
        assert META_ONTOLOGY_IRI.startswith("https://")
        assert not META_ONTOLOGY_IRI.endswith("#")
        assert not META_ONTOLOGY_IRI.endswith("/")
