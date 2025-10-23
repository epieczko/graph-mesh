"""
Unit tests for meta-ontology provider error handling.

Tests cover:
- Invalid configurations
- File not found errors
- Network failures (mocked)
- Invalid ontology files
- Provider creation failures
- Graceful degradation
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL

from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
from graph_mesh_core.providers.custom import CustomMetaOntology
from graph_mesh_core.providers.fibo import FIBOMetaOntology, FIBO_MODULES
from graph_mesh_core.providers.composite import CompositeMetaOntology


class TestCustomProviderErrors:
    """Test error handling in CustomMetaOntology provider."""

    @pytest.mark.unit
    def test_file_not_found(self):
        """Test that missing file raises RuntimeError."""
        provider = CustomMetaOntology(
            source="/nonexistent/path/to/file.owl",
            namespace="http://test.org#"
        )

        with pytest.raises(RuntimeError, match="Failed to load"):
            provider.build_graph()

    @pytest.mark.unit
    def test_invalid_rdf_file(self):
        """Test that invalid RDF file raises RuntimeError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            f.write("This is not valid RDF/Turtle syntax <<<>>>")
            temp_path = f.name

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org#"
            )

            with pytest.raises(RuntimeError, match="Failed to load"):
                provider.build_graph()

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    def test_empty_ontology_file(self):
        """Test that empty ontology file is handled."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
            # Write minimal valid turtle
            f.write("@prefix : <http://test.org#> .")
            temp_path = f.name

        try:
            provider = CustomMetaOntology(
                source=temp_path,
                namespace="http://test.org#"
            )

            graph = provider.build_graph()
            # Should succeed but have minimal content
            assert len(graph) >= 0

        finally:
            Path(temp_path).unlink()

    @pytest.mark.unit
    @patch('urllib.request.urlopen')
    def test_url_download_failure(self, mock_urlopen):
        """Test that URL download failure raises RuntimeError."""
        mock_urlopen.side_effect = Exception("Network error")

        provider = CustomMetaOntology(
            source="https://example.org/onto.owl",
            namespace="http://test.org#"
        )

        with pytest.raises(RuntimeError, match="Failed to load"):
            provider.build_graph()

    @pytest.mark.unit
    @patch('urllib.request.urlopen')
    def test_url_timeout(self, mock_urlopen):
        """Test that URL timeout raises RuntimeError."""
        import socket
        mock_urlopen.side_effect = socket.timeout("Connection timed out")

        provider = CustomMetaOntology(
            source="https://example.org/onto.owl",
            namespace="http://test.org#"
        )

        with pytest.raises(RuntimeError, match="Failed to load"):
            provider.build_graph()


class TestFIBOProviderErrors:
    """Test error handling in FIBOMetaOntology provider."""

    @pytest.mark.unit
    def test_invalid_module_name(self):
        """Test that invalid module name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid FIBO modules"):
            FIBOMetaOntology(modules=["INVALID_MODULE"])

    @pytest.mark.unit
    def test_multiple_invalid_modules(self):
        """Test that multiple invalid modules are reported."""
        with pytest.raises(ValueError, match="INVALID1"):
            FIBOMetaOntology(modules=["INVALID1", "INVALID2", "FND"])

    @pytest.mark.unit
    def test_empty_modules_list(self):
        """Test that empty modules list uses defaults."""
        # Should not raise, should use defaults
        provider = FIBOMetaOntology(modules=None)
        assert provider.modules == ["FND", "LOAN"]

    @pytest.mark.unit
    @patch('urllib.request.urlopen')
    def test_module_download_failure(self, mock_urlopen):
        """Test that module download failure raises RuntimeError."""
        mock_urlopen.side_effect = Exception("Download failed")

        provider = FIBOMetaOntology(
            modules=["FND"],
            use_cache=False  # Force download
        )

        with pytest.raises(RuntimeError, match="Failed to load FIBO module"):
            provider.build_graph()

    @pytest.mark.unit
    @patch('urllib.request.urlopen')
    def test_corrupted_module_file(self, mock_urlopen):
        """Test that corrupted module file raises RuntimeError."""
        # Mock download returning invalid RDF
        mock_response = MagicMock()
        mock_response.read.return_value = b"Invalid RDF content <<<>>>"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = FIBOMetaOntology(
                modules=["FND"],
                cache_dir=tmpdir,
                use_cache=False
            )

            with pytest.raises(RuntimeError, match="Failed to load FIBO module"):
                provider.build_graph()

    @pytest.mark.unit
    def test_cache_directory_creation(self):
        """Test that cache directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "nested" / "cache"

            provider = FIBOMetaOntology(
                modules=["FND"],
                cache_dir=str(cache_path)
            )

            assert provider.cache_dir.exists()


class TestCompositeProviderErrors:
    """Test error handling in CompositeMetaOntology provider."""

    @pytest.mark.unit
    def test_empty_providers_list(self):
        """Test that empty providers list raises ValueError."""
        with pytest.raises(ValueError, match="At least one provider"):
            CompositeMetaOntology(providers=[])

    @pytest.mark.unit
    def test_provider_build_failure_propagates(self):
        """Test that provider build failure propagates."""
        from graph_mesh_core.meta_ontology_base import MetaOntologyProvider, MetaOntologyInfo
        from rdflib import Namespace

        class FailingProvider(MetaOntologyProvider):
            def get_info(self):
                return MetaOntologyInfo(
                    name="Failing",
                    version="1.0",
                    namespace="http://fail#",
                    description="A failing provider"
                )

            def build_graph(self):
                raise RuntimeError("Intentional failure")

            def get_alignment_targets(self):
                return []

            def get_namespace(self):
                return Namespace("http://fail#")

        failing = FailingProvider()
        composite = CompositeMetaOntology(providers=[failing])

        with pytest.raises(RuntimeError, match="Failed to build graph"):
            composite.build_graph()


class TestRegistryErrors:
    """Test error handling in MetaOntologyRegistry."""

    @pytest.mark.unit
    def test_create_with_invalid_config_type(self):
        """Test that non-dict config raises ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            MetaOntologyRegistry.create("not a dict")

        with pytest.raises(ValueError, match="must be a dictionary"):
            MetaOntologyRegistry.create(123)

        with pytest.raises(ValueError, match="must be a dictionary"):
            MetaOntologyRegistry.create(None)

    @pytest.mark.unit
    def test_create_with_missing_type(self):
        """Test that config without type raises ValueError."""
        with pytest.raises(ValueError, match="must specify 'type'"):
            MetaOntologyRegistry.create({})

        with pytest.raises(ValueError, match="must specify 'type'"):
            MetaOntologyRegistry.create({"options": {}})

    @pytest.mark.unit
    def test_create_with_invalid_type(self):
        """Test that unknown provider type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown meta-ontology provider"):
            MetaOntologyRegistry.create({"type": "nonexistent"})

    @pytest.mark.unit
    def test_create_with_invalid_options_type(self):
        """Test that non-dict options raises ValueError."""
        with pytest.raises(ValueError, match="'options' must be a dictionary"):
            MetaOntologyRegistry.create({
                "type": "generic",
                "options": "not a dict"
            })

    @pytest.mark.unit
    def test_register_invalid_provider_class(self):
        """Test that registering invalid class raises TypeError."""
        class NotAProvider:
            pass

        with pytest.raises(TypeError, match="must implement MetaOntologyProvider"):
            MetaOntologyRegistry.register("invalid", NotAProvider)

    @pytest.mark.unit
    def test_unregister_nonexistent_provider(self):
        """Test that unregistering non-existent provider raises KeyError."""
        with pytest.raises(KeyError, match="Provider not registered"):
            MetaOntologyRegistry.unregister("nonexistent")

    @pytest.mark.unit
    def test_get_provider_class_nonexistent(self):
        """Test that getting non-existent provider class raises KeyError."""
        with pytest.raises(KeyError, match="Provider .* not found"):
            MetaOntologyRegistry.get_provider_class("nonexistent")

    @pytest.mark.unit
    def test_create_with_incompatible_options(self):
        """Test that incompatible options raise TypeError."""
        # Generic provider doesn't take any constructor args
        # So passing unexpected kwargs should fail
        with pytest.raises((TypeError, RuntimeError)):
            MetaOntologyRegistry.create({
                "type": "generic",
                "options": {"unexpected_arg": "value"}
            })


class TestProviderValidation:
    """Test provider validation methods."""

    @pytest.mark.unit
    def test_validate_alignment_generic_always_true(self):
        """Test that generic provider validate_alignment returns True."""
        from graph_mesh_core.providers.generic import GenericMetaOntology
        from rdflib import URIRef

        provider = GenericMetaOntology()

        source = URIRef("http://example.org/Source")
        target = URIRef("http://example.org/Target")

        assert provider.validate_alignment(source, target) is True

    @pytest.mark.unit
    def test_fibo_validate_alignment_checks_existence(self):
        """Test that FIBO provider validates target exists in graph."""
        # We'll test with a minimal mock instead of real FIBO
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal FIBO-like graph
            fibo_graph = Graph()
            from rdflib import Namespace, Literal
            fibo_ns = Namespace("https://spec.edmcouncil.org/fibo/ontology/FND/")
            fibo_graph.add((fibo_ns.TestClass, RDF.type, OWL.Class))

            # Save to cache
            cache_dir = Path(tmpdir)
            cache_file = cache_dir / "FND.rdf"
            fibo_graph.serialize(str(cache_file), format='xml')

            with patch.object(FIBOMetaOntology, '_download_module', return_value=cache_file):
                provider = FIBOMetaOntology(
                    modules=["FND"],
                    cache_dir=str(cache_dir)
                )

                provider.build_graph()

                # Valid target (exists in graph)
                valid_target = fibo_ns.TestClass
                assert provider.validate_alignment(URIRef("http://ex.org/X"), valid_target) is True

                # Invalid target (doesn't exist)
                invalid_target = fibo_ns.NonExistent
                assert provider.validate_alignment(URIRef("http://ex.org/X"), invalid_target) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_custom_provider_with_very_large_namespace(self):
        """Test custom provider with very long namespace URI."""
        long_namespace = "http://example.org/" + "a" * 1000 + "#"

        provider = CustomMetaOntology(
            source="/fake/path.owl",
            namespace=long_namespace
        )

        assert provider.namespace_str == long_namespace

    @pytest.mark.unit
    def test_fibo_provider_case_sensitivity(self):
        """Test that FIBO module names are case-sensitive."""
        # Valid uppercase
        provider1 = FIBOMetaOntology(modules=["FND"])
        assert provider1.modules == ["FND"]

        # Invalid lowercase
        with pytest.raises(ValueError):
            FIBOMetaOntology(modules=["fnd"])

    @pytest.mark.unit
    def test_composite_with_single_provider(self):
        """Test composite with only one provider (edge case but valid)."""
        from graph_mesh_core.providers.generic import GenericMetaOntology

        provider = GenericMetaOntology()
        composite = CompositeMetaOntology(providers=[provider])

        graph = composite.build_graph()
        assert len(graph) > 0

    @pytest.mark.unit
    def test_custom_provider_with_special_characters_in_name(self):
        """Test custom provider with special characters in derived name."""
        provider = CustomMetaOntology(
            source="/path/to/my-ontology v2.0 (draft).owl",
            namespace="http://test.org#"
        )

        # Name should be derived from filename
        assert "ontology" in provider.name_str.lower()
