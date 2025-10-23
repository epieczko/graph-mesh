"""
Integration tests for pluggable meta-ontology provider system.

Tests cover:
- Pipeline execution with different meta-ontology providers
- Generic provider (default)
- FIBO provider (with caching)
- Custom provider (from file)
- Provider information in artifacts
- Artifact naming based on provider
"""

import tempfile
from pathlib import Path
import pytest
from rdflib import Graph, Namespace, RDF, OWL, RDFS, URIRef, Literal

from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
from graph_mesh_core.providers.generic import GenericMetaOntology
from graph_mesh_core.providers.custom import CustomMetaOntology
from graph_mesh_orchestrator.models import (
    PipelineManifest,
    MetaOntologyConfig,
    MetaOntologyType,
)


class TestMetaOntologyProviderIntegration:
    """Test meta-ontology provider integration with pipeline."""

    @pytest.mark.integration
    def test_registry_create_generic(self):
        """Test creating generic provider via registry."""
        config = {"type": "generic"}
        provider = MetaOntologyRegistry.create(config)

        assert provider is not None
        info = provider.get_info()
        assert info.name == "Generic"
        assert info.version == "1.0"

        graph = provider.build_graph()
        assert len(graph) > 0

    @pytest.mark.integration
    def test_registry_create_generic_with_options(self):
        """Test generic provider ignores options gracefully."""
        config = {"type": "generic", "options": {}}
        provider = MetaOntologyRegistry.create(config)

        assert provider is not None
        graph = provider.build_graph()
        assert len(graph) > 0

    @pytest.mark.integration
    def test_registry_create_custom_from_memory(self):
        """Test creating custom provider from in-memory ontology."""
        # Create a simple test ontology
        test_graph = Graph()
        test_ns = Namespace("http://test.org/onto#")
        test_graph.bind("test", test_ns)

        # Add some classes
        test_graph.add((test_ns.TestClass, RDF.type, OWL.Class))
        test_graph.add((test_ns.TestClass, RDFS.label, Literal("Test Class")))

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            test_graph.serialize(f, format='turtle')
            temp_path = f.name

        try:
            # Create provider from file
            config = {
                "type": "custom",
                "options": {
                    "source": temp_path,
                    "namespace": "http://test.org/onto#",
                    "name": "TestOntology"
                }
            }

            provider = MetaOntologyRegistry.create(config)
            assert provider is not None

            info = provider.get_info()
            assert info.name == "TestOntology"

            graph = provider.build_graph()
            assert len(graph) > 0

            # Verify our test class is in there
            assert (test_ns.TestClass, RDF.type, OWL.Class) in graph

        finally:
            # Cleanup
            Path(temp_path).unlink()

    @pytest.mark.integration
    def test_manifest_with_generic_provider(self):
        """Test pipeline manifest with generic provider."""
        manifest_data = {
            "name": "test-pipeline",
            "meta_ontology": {
                "type": "generic"
            },
            "sources": [
                {
                    "id": "test-source",
                    "fetch": {"type": "local", "path": "/tmp/test.xsd"},
                    "convert": {"type": "xsd"}
                }
            ]
        }

        manifest = PipelineManifest.model_validate(manifest_data)

        assert manifest.meta_ontology.type == MetaOntologyType.GENERIC
        assert manifest.name == "test-pipeline"

    @pytest.mark.integration
    def test_manifest_with_fibo_provider(self):
        """Test pipeline manifest with FIBO provider."""
        manifest_data = {
            "name": "financial-pipeline",
            "meta_ontology": {
                "type": "fibo",
                "options": {
                    "modules": ["FND", "LOAN"],
                    "cache_dir": "/tmp/fibo-cache"
                }
            },
            "sources": [
                {
                    "id": "mismo",
                    "fetch": {"type": "local", "path": "/tmp/mismo.xsd"},
                    "convert": {"type": "xsd"}
                }
            ]
        }

        manifest = PipelineManifest.model_validate(manifest_data)

        assert manifest.meta_ontology.type == MetaOntologyType.FIBO
        assert manifest.meta_ontology.options["modules"] == ["FND", "LOAN"]
        assert manifest.meta_ontology.options["cache_dir"] == "/tmp/fibo-cache"

    @pytest.mark.integration
    def test_manifest_with_custom_provider(self):
        """Test pipeline manifest with custom provider."""
        manifest_data = {
            "name": "custom-pipeline",
            "meta_ontology": {
                "type": "custom",
                "options": {
                    "source": "https://example.org/onto.owl",
                    "namespace": "https://example.org/onto#",
                    "name": "CustomDomain"
                }
            },
            "sources": [
                {
                    "id": "test-source",
                    "fetch": {"type": "local", "path": "/tmp/test.json"},
                    "convert": {"type": "json"}
                }
            ]
        }

        manifest = PipelineManifest.model_validate(manifest_data)

        assert manifest.meta_ontology.type == MetaOntologyType.CUSTOM
        assert manifest.meta_ontology.options["source"] == "https://example.org/onto.owl"
        assert manifest.meta_ontology.options["name"] == "CustomDomain"

    @pytest.mark.integration
    def test_manifest_default_to_generic(self):
        """Test that manifest defaults to generic provider when not specified."""
        manifest_data = {
            "name": "default-pipeline",
            "sources": [
                {
                    "id": "test-source",
                    "fetch": {"type": "local", "path": "/tmp/test.xsd"},
                    "convert": {"type": "xsd"}
                }
            ]
        }

        manifest = PipelineManifest.model_validate(manifest_data)

        # Should default to generic
        assert manifest.meta_ontology.type == MetaOntologyType.GENERIC

    @pytest.mark.integration
    def test_provider_alignment_targets(self):
        """Test getting alignment targets from provider."""
        config = {"type": "generic"}
        provider = MetaOntologyRegistry.create(config)

        targets = provider.get_alignment_targets()

        assert len(targets) == 7  # Generic has 7 classes
        assert all(isinstance(t, URIRef) for t in targets)

    @pytest.mark.integration
    def test_provider_namespace(self):
        """Test getting namespace from provider."""
        config = {"type": "generic"}
        provider = MetaOntologyRegistry.create(config)

        namespace = provider.get_namespace()

        assert namespace is not None
        assert str(namespace).startswith("http")

    @pytest.mark.integration
    def test_provider_description_retrieval(self):
        """Test getting descriptions for concepts."""
        config = {"type": "generic"}
        provider = MetaOntologyRegistry.create(config)

        namespace = provider.get_namespace()
        agent_uri = namespace["Agent"]

        description = provider.get_description(agent_uri)

        assert description is not None
        assert "agent" in description.lower() or "person" in description.lower()

    @pytest.mark.integration
    def test_registry_list_providers(self):
        """Test listing available providers."""
        providers = MetaOntologyRegistry.list_providers()

        assert "generic" in providers
        assert "fibo" in providers
        assert "custom" in providers
        assert "composite" in providers

    @pytest.mark.integration
    def test_registry_is_registered(self):
        """Test checking if provider is registered."""
        assert MetaOntologyRegistry.is_registered("generic")
        assert MetaOntologyRegistry.is_registered("fibo")
        assert MetaOntologyRegistry.is_registered("custom")
        assert not MetaOntologyRegistry.is_registered("nonexistent")

    @pytest.mark.integration
    def test_invalid_provider_type_raises_error(self):
        """Test that invalid provider type raises error."""
        config = {"type": "nonexistent"}

        with pytest.raises(ValueError, match="Unknown meta-ontology provider"):
            MetaOntologyRegistry.create(config)

    @pytest.mark.integration
    def test_generic_provider_properties(self):
        """Test that generic provider exposes properties."""
        provider = GenericMetaOntology()

        properties = provider.get_properties()

        assert len(properties) > 0  # Should have object and datatype properties
        assert all(isinstance(p, URIRef) for p in properties)

    @pytest.mark.integration
    def test_generic_provider_top_level_classes(self):
        """Test that generic provider returns top-level classes."""
        provider = GenericMetaOntology()

        top_level = provider.get_top_level_classes()

        assert len(top_level) == 1  # Only Entity has no parent
        assert top_level[0].endswith("Entity")


class TestProviderCaching:
    """Test provider caching behavior."""

    @pytest.mark.integration
    def test_generic_provider_graph_reuse(self):
        """Test that generic provider can be called multiple times."""
        provider = GenericMetaOntology()

        graph1 = provider.build_graph()
        graph2 = provider.build_graph()

        # Should return same content
        assert len(graph1) == len(graph2)

    @pytest.mark.integration
    def test_custom_provider_caching(self):
        """Test that custom provider caches loaded graph."""
        # Create test ontology
        test_graph = Graph()
        test_ns = Namespace("http://test.org/cached#")
        test_graph.add((test_ns.CachedClass, RDF.type, OWL.Class))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            test_graph.serialize(f, format='turtle')
            temp_path = f.name

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org/cached#"
            )

            # First call
            graph1 = provider.build_graph()
            # Second call should use cached graph
            graph2 = provider.build_graph()

            assert len(graph1) == len(graph2)

        finally:
            Path(temp_path).unlink()


class TestBackwardCompatibility:
    """Test backward compatibility with old API."""

    @pytest.mark.integration
    def test_old_build_meta_graph_still_works(self):
        """Test that old build_meta_graph() function still works."""
        from graph_mesh_core.meta_ontology import build_meta_graph

        graph = build_meta_graph()

        assert len(graph) > 0
        # Should still be generic ontology
        assert any("Entity" in str(s) for s, p, o in graph)

    @pytest.mark.integration
    def test_old_serialize_meta_graph_still_works(self):
        """Test that old serialize_meta_graph() function still works."""
        from graph_mesh_core.meta_ontology import serialize_meta_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test-meta.ttl"

            result = serialize_meta_graph(output_path)

            assert result.exists()
            assert result == output_path

            # Should be valid turtle
            graph = Graph()
            graph.parse(str(result), format='turtle')
            assert len(graph) > 0

    @pytest.mark.integration
    def test_old_constants_still_available(self):
        """Test that old constants are still exported."""
        from graph_mesh_core.meta_ontology import (
            GM,
            META_CLASSES,
            META_OBJECT_PROPERTIES,
            META_DATA_PROPERTIES,
        )

        assert GM is not None
        assert len(META_CLASSES) == 7
        assert len(META_OBJECT_PROPERTIES) > 0
        assert len(META_DATA_PROPERTIES) > 0
