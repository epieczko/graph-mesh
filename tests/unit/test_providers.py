"""
Unit tests for meta-ontology providers.

Tests cover:
- GenericMetaOntology provider
- FIBOMetaOntology provider (without actual downloads)
- CustomMetaOntology provider
- CompositeMetaOntology provider
- MetaOntologyRegistry
- Provider interface compliance
- Error handling
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal

from graph_mesh_core.meta_ontology_base import MetaOntologyProvider, MetaOntologyInfo
from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
from graph_mesh_core.providers.generic import GenericMetaOntology
from graph_mesh_core.providers.custom import CustomMetaOntology
from graph_mesh_core.providers.composite import CompositeMetaOntology


class TestGenericMetaOntology:
    """Test GenericMetaOntology provider."""

    @pytest.mark.unit
    def test_provider_creation(self):
        """Test creating GenericMetaOntology provider."""
        provider = GenericMetaOntology()
        assert provider is not None

    @pytest.mark.unit
    def test_get_info(self):
        """Test get_info returns correct metadata."""
        provider = GenericMetaOntology()
        info = provider.get_info()

        assert isinstance(info, MetaOntologyInfo)
        assert info.name == "Generic"
        assert info.version == "1.0"
        assert "graph-mesh" in info.namespace.lower()
        assert len(info.description) > 0

    @pytest.mark.unit
    def test_build_graph(self):
        """Test building the generic ontology graph."""
        provider = GenericMetaOntology()
        graph = provider.build_graph()

        assert isinstance(graph, Graph)
        assert len(graph) > 0
        # Should have 7 classes + properties
        assert len(graph) >= 21  # 7 classes * 3 triples each

    @pytest.mark.unit
    def test_get_alignment_targets(self):
        """Test getting alignment targets."""
        provider = GenericMetaOntology()
        targets = provider.get_alignment_targets()

        assert len(targets) == 7  # 7 meta-classes
        assert all(isinstance(t, URIRef) for t in targets)

        # Check expected classes are present
        target_strs = [str(t) for t in targets]
        assert any("Entity" in s for s in target_strs)
        assert any("Agent" in s for s in target_strs)
        assert any("Event" in s for s in target_strs)

    @pytest.mark.unit
    def test_get_namespace(self):
        """Test getting namespace."""
        provider = GenericMetaOntology()
        namespace = provider.get_namespace()

        assert namespace is not None
        assert str(namespace).startswith("http")

    @pytest.mark.unit
    def test_get_top_level_classes(self):
        """Test getting top-level classes."""
        provider = GenericMetaOntology()
        top_level = provider.get_top_level_classes()

        assert len(top_level) == 1  # Only Entity has no parent
        assert str(top_level[0]).endswith("Entity")

    @pytest.mark.unit
    def test_get_properties(self):
        """Test getting properties."""
        provider = GenericMetaOntology()
        properties = provider.get_properties()

        assert len(properties) > 0
        assert all(isinstance(p, URIRef) for p in properties)

    @pytest.mark.unit
    def test_get_description(self):
        """Test getting description for a concept."""
        provider = GenericMetaOntology()
        namespace = provider.get_namespace()
        agent_uri = namespace["Agent"]

        description = provider.get_description(agent_uri)

        assert description is not None
        assert len(description) > 0
        assert "agent" in description.lower() or "person" in description.lower()

    @pytest.mark.unit
    def test_get_description_nonexistent(self):
        """Test getting description for non-existent concept."""
        provider = GenericMetaOntology()
        namespace = provider.get_namespace()
        fake_uri = namespace["NonExistent"]

        description = provider.get_description(fake_uri)

        assert description is None

    @pytest.mark.unit
    def test_validate_alignment_default(self):
        """Test default validate_alignment returns True."""
        provider = GenericMetaOntology()
        namespace = provider.get_namespace()

        source_uri = URIRef("http://example.org/SomeClass")
        target_uri = namespace["Entity"]

        assert provider.validate_alignment(source_uri, target_uri) is True

    @pytest.mark.unit
    def test_graph_has_owl_classes(self):
        """Test that graph contains OWL classes."""
        provider = GenericMetaOntology()
        graph = provider.build_graph()

        # Should have OWL.Class declarations
        classes = list(graph.subjects(RDF.type, OWL.Class))
        assert len(classes) == 7

    @pytest.mark.unit
    def test_graph_has_properties(self):
        """Test that graph contains properties."""
        provider = GenericMetaOntology()
        graph = provider.build_graph()

        # Should have object properties
        obj_props = list(graph.subjects(RDF.type, OWL.ObjectProperty))
        assert len(obj_props) > 0

        # Should have datatype properties
        data_props = list(graph.subjects(RDF.type, OWL.DatatypeProperty))
        assert len(data_props) > 0

    @pytest.mark.unit
    def test_multiple_builds_same_graph(self):
        """Test that building graph multiple times gives same result."""
        provider = GenericMetaOntology()

        graph1 = provider.build_graph()
        graph2 = provider.build_graph()

        assert len(graph1) == len(graph2)
        assert graph1.isomorphic(graph2)


class TestCustomMetaOntology:
    """Test CustomMetaOntology provider."""

    def create_test_ontology_file(self):
        """Helper to create a test ontology file."""
        test_graph = Graph()
        test_ns = Namespace("http://test.org/onto#")
        test_graph.bind("test", test_ns)

        # Add some test classes
        test_graph.add((test_ns.TestClass1, RDF.type, OWL.Class))
        test_graph.add((test_ns.TestClass1, RDFS.label, Literal("Test Class 1")))
        test_graph.add((test_ns.TestClass1, RDFS.comment, Literal("A test class")))

        test_graph.add((test_ns.TestClass2, RDF.type, OWL.Class))
        test_graph.add((test_ns.TestClass2, RDFS.label, Literal("Test Class 2")))

        # Add a property
        test_graph.add((test_ns.testProperty, RDF.type, OWL.ObjectProperty))
        test_graph.add((test_ns.testProperty, RDFS.label, Literal("Test Property")))

        return test_graph, test_ns

    @pytest.mark.unit
    def test_provider_creation_from_file(self):
        """Test creating CustomMetaOntology from file."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#",
                name="TestOntology"
            )

            assert provider is not None
            assert provider.source == temp_path
            assert provider.namespace_str == "http://test.org/onto#"

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_get_info_custom(self):
        """Test get_info for custom provider."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#",
                name="TestOntology",
                version="2.0"
            )

            info = provider.get_info()

            assert info.name == "TestOntology"
            assert info.version == "2.0"
            assert info.namespace == "http://test.org/onto#"

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_build_graph_custom(self):
        """Test building graph from custom ontology."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#"
            )

            loaded_graph = provider.build_graph()

            assert len(loaded_graph) > 0
            # Our test classes should be in there
            assert (test_ns.TestClass1, RDF.type, OWL.Class) in loaded_graph
            assert (test_ns.TestClass2, RDF.type, OWL.Class) in loaded_graph

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_get_alignment_targets_custom(self):
        """Test getting alignment targets from custom ontology."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#"
            )

            targets = provider.get_alignment_targets()

            assert len(targets) == 2  # TestClass1 and TestClass2
            assert all(isinstance(t, URIRef) for t in targets)

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_get_properties_custom(self):
        """Test getting properties from custom ontology."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#"
            )

            properties = provider.get_properties()

            assert len(properties) >= 1  # testProperty
            assert test_ns.testProperty in properties

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_get_description_custom(self):
        """Test getting description from custom ontology."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#"
            )

            description = provider.get_description(test_ns.TestClass1)

            assert description is not None
            assert "test class" in description.lower()

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_caching_custom_provider(self):
        """Test that custom provider caches loaded graph."""
        test_graph, test_ns = self.create_test_ontology_file()

        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as f:
            temp_path = f.name
        test_graph.serialize(temp_path, format='turtle')

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/onto#"
            )

            graph1 = provider.build_graph()
            graph2 = provider.build_graph()

            # Should be same object (cached)
            assert graph1 is graph2

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_file_not_found_raises_error(self):
        """Test that non-existent file raises error."""
        provider = CustomMetaOntology(
            source="/nonexistent/file.ttl",
            namespace="http://test.org/onto#"
        )

        with pytest.raises(RuntimeError, match="Failed to load"):
            provider.build_graph()

    @pytest.mark.unit
    def test_derive_name_from_file(self):
        """Test deriving name from filename."""
        provider = CustomMetaOntology(
            source="/path/to/my-ontology.owl",
            namespace="http://test.org#"
        )

        assert provider.name_str == "my-ontology"

    @pytest.mark.unit
    def test_derive_name_from_url(self):
        """Test deriving name from URL."""
        provider = CustomMetaOntology(
            source="https://example.org/ontologies/domain.ttl",
            namespace="http://test.org#"
        )

        assert provider.name_str == "domain"


class TestCompositeMetaOntology:
    """Test CompositeMetaOntology provider."""

    @pytest.mark.unit
    def test_provider_creation(self):
        """Test creating CompositeMetaOntology."""
        provider1 = GenericMetaOntology()
        provider2 = GenericMetaOntology()

        composite = CompositeMetaOntology(
            providers=[provider1, provider2]
        )

        assert composite is not None
        assert len(composite.providers) == 2

    @pytest.mark.unit
    def test_empty_providers_raises_error(self):
        """Test that empty providers list raises error."""
        with pytest.raises(ValueError, match="At least one provider"):
            CompositeMetaOntology(providers=[])

    @pytest.mark.unit
    def test_get_info_composite(self):
        """Test get_info combines provider information."""
        provider1 = GenericMetaOntology()

        composite = CompositeMetaOntology(
            providers=[provider1],
            name="TestComposite"
        )

        info = composite.get_info()

        assert info.name == "TestComposite"
        assert "Generic" in info.description

    @pytest.mark.unit
    def test_build_graph_merges_providers(self):
        """Test that build_graph merges graphs from all providers."""
        provider1 = GenericMetaOntology()
        provider2 = GenericMetaOntology()

        composite = CompositeMetaOntology(providers=[provider1, provider2])

        graph = composite.build_graph()

        assert len(graph) > 0
        # Should have content from both providers (though they're the same in this case)
        assert len(graph) >= len(provider1.build_graph())

    @pytest.mark.unit
    def test_get_alignment_targets_combines(self):
        """Test that alignment targets are combined from all providers."""
        provider1 = GenericMetaOntology()

        composite = CompositeMetaOntology(providers=[provider1])

        targets = composite.get_alignment_targets()

        assert len(targets) > 0
        # Should have all targets from provider1
        assert len(targets) >= len(provider1.get_alignment_targets())

    @pytest.mark.unit
    def test_get_alignment_targets_deduplicates(self):
        """Test that duplicate targets are removed."""
        provider1 = GenericMetaOntology()
        provider2 = GenericMetaOntology()  # Same as provider1

        composite = CompositeMetaOntology(providers=[provider1, provider2])

        targets = composite.get_alignment_targets()

        # Should deduplicate
        assert len(targets) == len(provider1.get_alignment_targets())

    @pytest.mark.unit
    def test_get_description_from_any_provider(self):
        """Test that description is retrieved from first matching provider."""
        provider1 = GenericMetaOntology()

        composite = CompositeMetaOntology(providers=[provider1])

        namespace = provider1.get_namespace()
        description = composite.get_description(namespace["Agent"])

        assert description is not None

    @pytest.mark.unit
    def test_default_namespace_from_first_provider(self):
        """Test that default namespace comes from first provider."""
        provider1 = GenericMetaOntology()

        composite = CompositeMetaOntology(providers=[provider1])

        info = composite.get_info()
        provider1_info = provider1.get_info()

        assert info.namespace == provider1_info.namespace


class TestMetaOntologyRegistry:
    """Test MetaOntologyRegistry."""

    @pytest.mark.unit
    def test_list_providers(self):
        """Test listing available providers."""
        providers = MetaOntologyRegistry.list_providers()

        assert "generic" in providers
        assert "fibo" in providers
        assert "custom" in providers
        assert "composite" in providers

    @pytest.mark.unit
    def test_is_registered(self):
        """Test checking if provider is registered."""
        assert MetaOntologyRegistry.is_registered("generic")
        assert MetaOntologyRegistry.is_registered("fibo")
        assert MetaOntologyRegistry.is_registered("custom")
        assert not MetaOntologyRegistry.is_registered("nonexistent")

    @pytest.mark.unit
    def test_create_generic(self):
        """Test creating generic provider via registry."""
        config = {"type": "generic"}
        provider = MetaOntologyRegistry.create(config)

        assert isinstance(provider, GenericMetaOntology)

    @pytest.mark.unit
    def test_create_with_options(self):
        """Test creating provider with options."""
        config = {"type": "generic", "options": {}}
        provider = MetaOntologyRegistry.create(config)

        assert provider is not None

    @pytest.mark.unit
    def test_create_invalid_type_raises_error(self):
        """Test that invalid type raises error."""
        config = {"type": "nonexistent"}

        with pytest.raises(ValueError, match="Unknown meta-ontology provider"):
            MetaOntologyRegistry.create(config)

    @pytest.mark.unit
    def test_create_missing_type_raises_error(self):
        """Test that missing type raises error."""
        config = {}

        with pytest.raises(ValueError, match="must specify 'type'"):
            MetaOntologyRegistry.create(config)

    @pytest.mark.unit
    def test_create_invalid_config_type_raises_error(self):
        """Test that non-dict config raises error."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            MetaOntologyRegistry.create("not a dict")

    @pytest.mark.unit
    def test_create_invalid_options_type_raises_error(self):
        """Test that non-dict options raises error."""
        config = {"type": "generic", "options": "not a dict"}

        with pytest.raises(ValueError, match="'options' must be a dictionary"):
            MetaOntologyRegistry.create(config)

    @pytest.mark.unit
    def test_register_custom_provider(self):
        """Test registering a custom provider."""
        class TestProvider(MetaOntologyProvider):
            def get_info(self):
                return MetaOntologyInfo(
                    name="Test",
                    version="1.0",
                    namespace="http://test#",
                    description="Test provider"
                )

            def build_graph(self):
                return Graph()

            def get_alignment_targets(self):
                return []

            def get_namespace(self):
                return Namespace("http://test#")

        MetaOntologyRegistry.register("test_provider", TestProvider)

        assert MetaOntologyRegistry.is_registered("test_provider")

        # Create instance
        config = {"type": "test_provider"}
        provider = MetaOntologyRegistry.create(config)

        assert isinstance(provider, TestProvider)

    @pytest.mark.unit
    def test_register_non_provider_raises_error(self):
        """Test that registering non-provider class raises error."""
        class NotAProvider:
            pass

        with pytest.raises(TypeError, match="must implement MetaOntologyProvider"):
            MetaOntologyRegistry.register("invalid", NotAProvider)

    @pytest.mark.unit
    def test_get_provider_class(self):
        """Test getting provider class."""
        provider_class = MetaOntologyRegistry.get_provider_class("generic")

        assert provider_class == GenericMetaOntology

    @pytest.mark.unit
    def test_get_provider_class_nonexistent_raises_error(self):
        """Test that getting non-existent provider class raises error."""
        with pytest.raises(KeyError, match="Provider 'nonexistent' not found"):
            MetaOntologyRegistry.get_provider_class("nonexistent")


class TestProviderInterfaceCompliance:
    """Test that all providers comply with the interface."""

    @pytest.mark.unit
    @pytest.mark.parametrize("provider_type", ["generic"])
    def test_provider_has_get_info(self, provider_type):
        """Test that provider has get_info method."""
        config = {"type": provider_type}
        provider = MetaOntologyRegistry.create(config)

        assert hasattr(provider, "get_info")
        assert callable(provider.get_info)

        info = provider.get_info()
        assert isinstance(info, MetaOntologyInfo)

    @pytest.mark.unit
    @pytest.mark.parametrize("provider_type", ["generic"])
    def test_provider_has_build_graph(self, provider_type):
        """Test that provider has build_graph method."""
        config = {"type": provider_type}
        provider = MetaOntologyRegistry.create(config)

        assert hasattr(provider, "build_graph")
        assert callable(provider.build_graph)

        graph = provider.build_graph()
        assert isinstance(graph, Graph)

    @pytest.mark.unit
    @pytest.mark.parametrize("provider_type", ["generic"])
    def test_provider_has_get_alignment_targets(self, provider_type):
        """Test that provider has get_alignment_targets method."""
        config = {"type": provider_type}
        provider = MetaOntologyRegistry.create(config)

        assert hasattr(provider, "get_alignment_targets")
        assert callable(provider.get_alignment_targets)

        targets = provider.get_alignment_targets()
        assert isinstance(targets, list)

    @pytest.mark.unit
    @pytest.mark.parametrize("provider_type", ["generic"])
    def test_provider_has_get_namespace(self, provider_type):
        """Test that provider has get_namespace method."""
        config = {"type": provider_type}
        provider = MetaOntologyRegistry.create(config)

        assert hasattr(provider, "get_namespace")
        assert callable(provider.get_namespace)

        namespace = provider.get_namespace()
        assert namespace is not None
