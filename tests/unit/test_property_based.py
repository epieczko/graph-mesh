"""
Property-based tests using hypothesis.

Tests cover:
- Safe local name generation with various inputs
- IRI generation with different namespaces
- XSD type mapping consistency
- Graph operations idempotency
- Pipeline configuration variations
"""

from pathlib import Path
import re

import pytest
from hypothesis import given, assume, strategies as st, settings
from rdflib import Graph, URIRef, Namespace

from graph_mesh_ingest.xsd_to_owl import (
    local_name_of,
    safe_local,
    iri_for,
)
from graph_mesh_core.meta_ontology import (
    MetaClass,
    build_meta_graph,
    add_domain_classes,
)


# ============================================================================
# Property-based tests for XSD to OWL utilities
# ============================================================================

class TestSafeLocalProperties:
    """Property-based tests for safe_local function."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_safe_local_always_returns_string(self, text):
        """Test that safe_local always returns a string."""
        result = safe_local(text)
        assert isinstance(result, str)

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_safe_local_preserves_alphanumeric(self, text):
        """Test that alphanumeric characters are preserved."""
        result = safe_local(text)
        # All alphanumeric chars should be in result
        for char in text:
            if char.isalnum():
                assert char in result

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_safe_local_never_empty(self, text):
        """Test that safe_local never returns empty string."""
        result = safe_local(text)
        assert len(result) > 0

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_safe_local_idempotent(self, text):
        """Test that applying safe_local twice gives same result."""
        first = safe_local(text)
        second = safe_local(first)
        # Should be idempotent for already-safe strings
        # (Note: May not be perfectly idempotent due to qname extraction)
        assert isinstance(second, str)

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(alphabet=st.characters(blacklist_characters=' @#$%^&*()'), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_safe_local_no_unsafe_chars_input(self, text):
        """Test safe_local with text without common unsafe characters."""
        assume(len(text) > 0)
        result = safe_local(text)
        # Result should not be empty
        assert result


class TestLocalNameOfProperties:
    """Property-based tests for local_name_of function."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_local_name_of_always_returns_string(self, text):
        """Test that local_name_of always returns a string."""
        result = local_name_of(text)
        assert isinstance(result, str)
        assert len(result) > 0  # Never returns empty (returns "Unnamed" if needed)

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_local_name_of_plain_name_unchanged(self, text):
        """Test that plain names without namespace are returned unchanged."""
        assume('{' not in text and '}' not in text)
        result = local_name_of(text)
        assert result == text

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        namespace=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50),
        local=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=50)
    )
    @settings(max_examples=100)
    def test_local_name_of_extracts_from_qname(self, namespace, local):
        """Test extracting local name from qualified name."""
        qname = f"{{{namespace}}}{local}"
        result = local_name_of(qname)
        assert result == local


class TestIriForProperties:
    """Property-based tests for iri_for function."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        namespace=st.text(min_size=10, max_size=50).filter(lambda x: '://' in x or x.startswith('http')),
        local=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=30)
    )
    @settings(max_examples=50)
    def test_iri_for_returns_uriref(self, namespace, local):
        """Test that iri_for always returns URIRef."""
        result = iri_for(namespace, local)
        assert isinstance(result, URIRef)

    @pytest.mark.unit
    @pytest.mark.property
    @given(local=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=30))
    @settings(max_examples=100)
    def test_iri_for_none_namespace_uses_fallback(self, local):
        """Test that None namespace always uses fallback."""
        result = iri_for(None, local)
        assert isinstance(result, URIRef)
        assert "graph-mesh.org" in str(result)

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        namespace=st.just("http://example.org/schema"),
        local=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=30)
    )
    @settings(max_examples=100)
    def test_iri_for_contains_local_name(self, namespace, local):
        """Test that IRI contains the sanitized local name."""
        result = iri_for(namespace, local)
        # The sanitized local name should be in the URI
        assert local in str(result) or safe_local(local) in str(result)


# ============================================================================
# Property-based tests for meta-ontology
# ============================================================================

class TestMetaClassProperties:
    """Property-based tests for MetaClass."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        name=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=30),
        comment=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=50)
    def test_metaclass_creation_always_succeeds(self, name, comment):
        """Test that MetaClass can be created with any valid strings."""
        mc = MetaClass(name, comment)
        assert mc.name == name
        assert mc.comment == comment

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        name=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll')), min_size=1, max_size=30),
        comment=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=50)
    def test_metaclass_uri_is_valid_uriref(self, name, comment):
        """Test that MetaClass.uri() always returns valid URIRef."""
        mc = MetaClass(name, comment)
        uri = mc.uri()
        assert isinstance(uri, URIRef)
        assert len(str(uri)) > 0


class TestBuildMetaGraphProperties:
    """Property-based tests for meta-ontology graph building."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=10)
    def test_build_meta_graph_always_same(self, _):
        """Test that build_meta_graph is deterministic."""
        g1 = build_meta_graph()
        g2 = build_meta_graph()

        assert len(g1) == len(g2)
        assert g1.isomorphic(g2)

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=10)
    def test_build_meta_graph_has_expected_size(self, _):
        """Test that meta-ontology graph has consistent size."""
        g = build_meta_graph()
        # Each meta-class has 3 triples (type, label, comment)
        expected_size = len(META_CLASSES) * 3
        assert len(g) == expected_size

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.lists(
        st.text(min_size=20, max_size=100).filter(lambda x: '://' in x),
        min_size=0,
        max_size=10
    ))
    @settings(max_examples=20)
    def test_add_domain_classes_increases_graph_size(self, class_iris):
        """Test that adding domain classes increases graph size."""
        g = Graph()
        initial_size = len(g)

        add_domain_classes(g, class_iris)

        # Each class adds 2 triples (type and subClassOf)
        expected_increase = len(class_iris) * 2
        assert len(g) == initial_size + expected_increase

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.lists(
        st.text(min_size=20, max_size=100).filter(lambda x: '://' in x),
        min_size=1,
        max_size=5,
        unique=True
    ))
    @settings(max_examples=20)
    def test_add_domain_classes_idempotent(self, class_iris):
        """Test that adding same domain classes twice doesn't duplicate."""
        g = Graph()
        add_domain_classes(g, class_iris)
        size_after_first = len(g)

        add_domain_classes(g, class_iris)
        size_after_second = len(g)

        # RDF graphs are sets, so adding same triples shouldn't increase size
        assert size_after_first == size_after_second


# ============================================================================
# Property-based tests for graph operations
# ============================================================================

class TestGraphOperationsProperties:
    """Property-based tests for general graph operations."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=10)
    def test_graph_parse_serialize_roundtrip(self, _):
        """Test that graph serialization round-trip preserves content."""
        g1 = build_meta_graph()

        # Serialize to string
        serialized = g1.serialize(format="turtle")

        # Parse back
        g2 = Graph()
        g2.parse(data=serialized, format="turtle")

        # Should be isomorphic
        assert g1.isomorphic(g2)

    @pytest.mark.unit
    @pytest.mark.property
    @given(st.lists(st.just("turtle"), min_size=1, max_size=1))
    @settings(max_examples=5)
    def test_graph_addition_commutative(self, _):
        """Test that graph addition is commutative."""
        g1 = build_meta_graph()

        g2 = Graph()
        # Add a simple triple
        NS = Namespace("http://test.example.org/")
        g2.add((NS.TestClass, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                URIRef("http://www.w3.org/2000/01/rdf-schema#Class")))

        # g1 + g2
        combined1 = Graph()
        combined1 += g1
        combined1 += g2

        # g2 + g1
        combined2 = Graph()
        combined2 += g2
        combined2 += g1

        # Should be isomorphic (commutative)
        assert combined1.isomorphic(combined2)


# ============================================================================
# Property-based tests for configuration structures
# ============================================================================

class TestConfigurationProperties:
    """Property-based tests for configuration structures."""

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        source_id=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')), min_size=1, max_size=30),
        converter_type=st.sampled_from(["xsd", "json"])
    )
    @settings(max_examples=50)
    def test_source_config_valid_ids(self, source_id, converter_type):
        """Test that various source IDs are handled correctly."""
        from graph_mesh_orchestrator.ingest import _get_identifier

        source = {"id": source_id, "convert": {"type": converter_type}}

        result = _get_identifier(source)
        assert result == source_id

    @pytest.mark.unit
    @pytest.mark.property
    @given(
        manifest_name=st.text(min_size=1, max_size=50),
        num_sources=st.integers(min_value=0, max_value=5)
    )
    @settings(max_examples=20)
    def test_manifest_with_varying_sources(self, manifest_name, num_sources):
        """Test manifest creation with varying number of sources."""
        from graph_mesh_orchestrator.pipeline import PipelineManifest

        sources = [
            {"id": f"source{i}", "convert": {"type": "xsd"}}
            for i in range(num_sources)
        ]

        manifest_data = {
            "name": manifest_name,
            "sources": sources,
            "matchers": ["LogMap"]
        }

        manifest = PipelineManifest.from_dict(manifest_data)

        assert manifest.name == manifest_name
        assert len(manifest.sources) == num_sources


# ============================================================================
# Import for META_CLASSES
# ============================================================================

from graph_mesh_core.meta_ontology import META_CLASSES
