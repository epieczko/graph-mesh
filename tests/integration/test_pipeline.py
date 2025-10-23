"""
Integration tests for full Graph-Mesh pipeline.

Tests cover:
- End-to-end pipeline execution
- Manifest loading and parsing
- Source fetching
- Ingest stage integration
- Graph fusion
- Artifact creation and structure
- Multi-source scenarios
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml

import pytest
from rdflib import Graph, RDF, RDFS, OWL

from graph_mesh_orchestrator.pipeline import (
    SourceConfig,
    PipelineManifest,
    PipelineArtifacts,
    load_manifest,
    fetch_source,
    fuse_graphs,
    orchestrate,
)
from graph_mesh_core.meta_ontology import build_meta_graph


class TestSourceConfig:
    """Test SourceConfig dataclass."""

    @pytest.mark.integration
    def test_from_dict_basic(self):
        """Test creating SourceConfig from dict."""
        data = {
            "id": "test-source",
            "fetch": {"type": "local", "path": "/path/to/file.xsd"},
            "convert": {"type": "xsd"}
        }

        config = SourceConfig.from_dict(data)

        assert config.identifier == "test-source"
        assert config.fetch == {"type": "local", "path": "/path/to/file.xsd"}
        assert config.convert == {"type": "xsd"}

    @pytest.mark.integration
    def test_from_dict_minimal(self):
        """Test creating SourceConfig with minimal data."""
        data = {"id": "minimal"}

        config = SourceConfig.from_dict(data)

        assert config.identifier == "minimal"
        assert config.fetch == {}
        assert config.convert == {}


class TestPipelineManifest:
    """Test PipelineManifest dataclass."""

    @pytest.mark.integration
    def test_from_dict_basic(self):
        """Test creating PipelineManifest from dict."""
        data = {
            "name": "test-pipeline",
            "sources": [
                {"id": "source1", "fetch": {"type": "local"}, "convert": {"type": "xsd"}}
            ],
            "matchers": ["LogMap", "AML"]
        }

        manifest = PipelineManifest.from_dict(data)

        assert manifest.name == "test-pipeline"
        assert len(manifest.sources) == 1
        assert manifest.sources[0].identifier == "source1"
        assert manifest.matchers == ["LogMap", "AML"]

    @pytest.mark.integration
    def test_from_dict_default_matchers(self):
        """Test that default matchers are used when not specified."""
        data = {
            "name": "test-pipeline",
            "sources": [{"id": "source1"}]
        }

        manifest = PipelineManifest.from_dict(data)

        # Should have default matchers
        assert len(manifest.matchers) > 0
        assert "LogMap" in manifest.matchers

    @pytest.mark.integration
    def test_from_dict_multiple_sources(self):
        """Test manifest with multiple sources."""
        data = {
            "name": "multi-source",
            "sources": [
                {"id": "source1", "convert": {"type": "xsd"}},
                {"id": "source2", "convert": {"type": "json"}},
                {"id": "source3", "convert": {"type": "xsd"}}
            ],
            "matchers": ["LogMap"]
        }

        manifest = PipelineManifest.from_dict(data)

        assert len(manifest.sources) == 3
        assert manifest.sources[0].identifier == "source1"
        assert manifest.sources[1].identifier == "source2"
        assert manifest.sources[2].identifier == "source3"


class TestLoadManifest:
    """Test manifest loading from file."""

    @pytest.mark.integration
    def test_load_simple_manifest(self, simple_manifest_file):
        """Test loading a simple manifest file."""
        manifest = load_manifest(simple_manifest_file)

        assert isinstance(manifest, PipelineManifest)
        assert manifest.name == "test-pipeline"
        assert len(manifest.sources) > 0

    @pytest.mark.integration
    def test_load_manifest_with_multiple_sources(self, multi_source_manifest_dict, temp_dir):
        """Test loading manifest with multiple sources."""
        manifest_file = temp_dir / "multi_manifest.yaml"
        manifest_file.write_text(yaml.dump(multi_source_manifest_dict))

        manifest = load_manifest(manifest_file)

        assert len(manifest.sources) == 2
        assert manifest.matchers == ["LogMap", "AML"]


class TestFetchSource:
    """Test source fetching functionality."""

    @pytest.mark.integration
    def test_fetch_single_local_file(self, simple_xsd_file, temp_dir):
        """Test fetching a single local file."""
        source = SourceConfig(
            identifier="test",
            fetch={"type": "local", "path": str(simple_xsd_file)},
            convert={"type": "xsd"}
        )

        result = fetch_source(source, temp_dir)

        assert str(simple_xsd_file.resolve()) in result

    @pytest.mark.integration
    def test_fetch_multiple_local_files(self, multiple_xsd_files, temp_dir):
        """Test fetching multiple local files."""
        source = SourceConfig(
            identifier="multi",
            fetch={"type": "local", "paths": [str(f) for f in multiple_xsd_files]},
            convert={"type": "xsd"}
        )

        result = fetch_source(source, temp_dir)

        assert isinstance(result, list)
        assert len(result) == len(multiple_xsd_files)

    @pytest.mark.integration
    def test_fetch_unsupported_type_raises_error(self, temp_dir):
        """Test that unsupported fetch type raises NotImplementedError."""
        source = SourceConfig(
            identifier="remote",
            fetch={"type": "http", "url": "http://example.com/schema.xsd"},
            convert={"type": "xsd"}
        )

        with pytest.raises(NotImplementedError, match="Unsupported fetch type"):
            fetch_source(source, temp_dir)


class TestFuseGraphs:
    """Test graph fusion functionality."""

    @pytest.mark.integration
    def test_fuse_single_graph(self, sample_ontology_file, temp_dir):
        """Test fusing a single graph with meta-ontology."""
        meta_graph = build_meta_graph()
        output_path = temp_dir / "fused.ttl"

        result = fuse_graphs([sample_ontology_file], meta_graph, output_path)

        assert result == output_path
        assert output_path.exists()

        # Verify fusion
        g = Graph()
        g.parse(str(output_path))

        # Should contain meta-ontology classes
        meta_classes = list(g.triples((None, RDF.type, RDFS.Class)))
        assert len(meta_classes) > 0

    @pytest.mark.integration
    def test_fuse_multiple_graphs(self, temp_dir):
        """Test fusing multiple graphs."""
        # Create sample graphs
        g1 = Graph()
        g1.parse(data="""
            @prefix ex: <http://example.org/> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            ex:Class1 a owl:Class .
        """, format="turtle")

        g2 = Graph()
        g2.parse(data="""
            @prefix ex: <http://example.org/> .
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            ex:Class2 a owl:Class .
        """, format="turtle")

        path1 = temp_dir / "graph1.ttl"
        path2 = temp_dir / "graph2.ttl"
        g1.serialize(destination=str(path1), format="turtle")
        g2.serialize(destination=str(path2), format="turtle")

        meta_graph = build_meta_graph()
        output_path = temp_dir / "fused.ttl"

        result = fuse_graphs([path1, path2], meta_graph, output_path)

        # Verify all content is included
        fused = Graph()
        fused.parse(str(result))

        # Should have classes from both graphs plus meta-ontology
        assert len(fused) > len(meta_graph)

    @pytest.mark.integration
    def test_fuse_preserves_meta_ontology(self, sample_ontology_file, temp_dir):
        """Test that fusion preserves meta-ontology content."""
        meta_graph = build_meta_graph()
        original_meta_size = len(meta_graph)
        output_path = temp_dir / "fused.ttl"

        fuse_graphs([sample_ontology_file], meta_graph, output_path)

        # Parse and check
        fused = Graph()
        fused.parse(str(output_path))

        # Meta-ontology content should be preserved
        assert len(fused) >= original_meta_size


class TestOrchestrate:
    """Test full pipeline orchestration."""

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_single_source(self, mock_run_alignment, simple_manifest_file, temp_dir):
        """Test orchestrating pipeline with single source."""
        # Mock alignment to avoid Docker
        mock_run_alignment.return_value = [temp_dir / "mapping.sssom.tsv"]

        artifacts = orchestrate(simple_manifest_file, workdir=temp_dir)

        assert isinstance(artifacts, PipelineArtifacts)
        assert artifacts.workdir == temp_dir
        assert artifacts.meta_ontology.exists()
        assert artifacts.merged_graph.exists()
        assert len(artifacts.converted) > 0

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_creates_directory_structure(self, mock_run_alignment, simple_manifest_file, temp_dir):
        """Test that orchestrate creates expected directory structure."""
        mock_run_alignment.return_value = []

        artifacts = orchestrate(simple_manifest_file, workdir=temp_dir)

        # Check directory structure
        assert (temp_dir / "meta").exists()
        assert (temp_dir / "converted").exists()
        assert artifacts.meta_ontology.exists()

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_meta_ontology_valid(self, mock_run_alignment, simple_manifest_file, temp_dir):
        """Test that meta-ontology artifact is valid."""
        mock_run_alignment.return_value = []

        artifacts = orchestrate(simple_manifest_file, workdir=temp_dir)

        # Verify meta-ontology is valid RDF
        g = Graph()
        g.parse(str(artifacts.meta_ontology))
        assert len(g) > 0

        # Should have meta-ontology classes
        classes = list(g.triples((None, RDF.type, RDFS.Class)))
        assert len(classes) >= 7  # 7 meta-classes

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_converted_graphs_valid(self, mock_run_alignment, simple_manifest_file, temp_dir):
        """Test that converted graphs are valid OWL."""
        mock_run_alignment.return_value = []

        artifacts = orchestrate(simple_manifest_file, workdir=temp_dir)

        # Check each converted graph
        for source_id, owl_path in artifacts.converted.items():
            assert owl_path.exists()

            # Verify it's valid OWL/RDF
            g = Graph()
            g.parse(str(owl_path))
            assert len(g) > 0

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_merged_graph_valid(self, mock_run_alignment, simple_manifest_file, temp_dir):
        """Test that merged graph is valid and contains all content."""
        mock_run_alignment.return_value = []

        artifacts = orchestrate(simple_manifest_file, workdir=temp_dir)

        # Verify merged graph
        merged = Graph()
        merged.parse(str(artifacts.merged_graph))

        # Should have content from meta-ontology
        meta_classes = list(merged.triples((None, RDF.type, RDFS.Class)))
        assert len(meta_classes) >= 7

        # Should have content from converted graphs
        assert len(merged) > 7 * 3  # More than just meta-ontology

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_multiple_sources(self, mock_run_alignment, multi_source_manifest_dict, temp_dir):
        """Test orchestrating pipeline with multiple sources."""
        # Create manifest file
        manifest_file = temp_dir / "multi_manifest.yaml"
        manifest_file.write_text(yaml.dump(multi_source_manifest_dict))

        mock_run_alignment.return_value = []

        artifacts = orchestrate(manifest_file, workdir=temp_dir)

        # Should have converted graphs for both sources
        assert len(artifacts.converted) == 2
        assert "xsd-source" in artifacts.converted
        assert "json-source" in artifacts.converted

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_without_workdir(self, mock_run_alignment, simple_manifest_file):
        """Test that orchestrate creates default workdir if not specified."""
        mock_run_alignment.return_value = []

        artifacts = orchestrate(simple_manifest_file, workdir=None)

        # Should create artifacts directory by default
        assert artifacts.workdir.exists()
        assert artifacts.workdir.name == "artifacts"

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_alignment_called_for_each_source(self, mock_run_alignment, multi_source_manifest_dict, temp_dir):
        """Test that alignment is run for each source."""
        manifest_file = temp_dir / "multi_manifest.yaml"
        manifest_file.write_text(yaml.dump(multi_source_manifest_dict))

        mock_run_alignment.return_value = []

        orchestrate(manifest_file, workdir=temp_dir)

        # run_alignment should be called once per source
        assert mock_run_alignment.call_count == 2

    @pytest.mark.integration
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_orchestrate_mappings_populated(self, mock_run_alignment, simple_manifest_file, temp_dir):
        """Test that mappings are populated in artifacts."""
        # Mock alignment to return mapping paths
        mapping_path = temp_dir / "test_mapping.sssom.tsv"
        mock_run_alignment.return_value = [mapping_path]

        artifacts = orchestrate(simple_manifest_file, workdir=temp_dir)

        # Check that mappings are recorded
        assert len(artifacts.mappings) > 0
        for source_id, mapping_list in artifacts.mappings.items():
            assert isinstance(mapping_list, list)


class TestPipelineArtifacts:
    """Test PipelineArtifacts dataclass."""

    @pytest.mark.integration
    def test_pipeline_artifacts_creation(self, temp_dir):
        """Test creating PipelineArtifacts instance."""
        artifacts = PipelineArtifacts(
            workdir=temp_dir,
            meta_ontology=temp_dir / "meta.ttl",
            converted={"source1": temp_dir / "source1.owl"},
            mappings={"source1": [temp_dir / "mapping.tsv"]},
            merged_graph=temp_dir / "merged.ttl"
        )

        assert artifacts.workdir == temp_dir
        assert artifacts.meta_ontology == temp_dir / "meta.ttl"
        assert len(artifacts.converted) == 1
        assert len(artifacts.mappings) == 1
        assert artifacts.merged_graph == temp_dir / "merged.ttl"


class TestEndToEndScenarios:
    """Test complete end-to-end scenarios."""

    @pytest.mark.integration
    @pytest.mark.slow
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_xsd_to_owl_pipeline(self, mock_run_alignment, simple_xsd_file, temp_dir):
        """Test complete pipeline with XSD input."""
        # Create manifest
        manifest_data = {
            "name": "xsd-pipeline",
            "sources": [
                {
                    "id": "test-xsd",
                    "fetch": {"type": "local", "path": str(simple_xsd_file)},
                    "convert": {"type": "xsd"}
                }
            ],
            "matchers": ["LogMap"]
        }
        manifest_file = temp_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))

        mock_run_alignment.return_value = []

        artifacts = orchestrate(manifest_file, workdir=temp_dir)

        # Verify complete pipeline execution
        assert artifacts.meta_ontology.exists()
        assert "test-xsd" in artifacts.converted
        assert artifacts.converted["test-xsd"].exists()
        assert artifacts.merged_graph.exists()

        # Verify content quality
        converted_graph = Graph()
        converted_graph.parse(str(artifacts.converted["test-xsd"]))
        assert len(converted_graph) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_json_to_owl_pipeline(self, mock_run_alignment, simple_json_schema_file, temp_dir):
        """Test complete pipeline with JSON Schema input."""
        # Create manifest
        manifest_data = {
            "name": "json-pipeline",
            "sources": [
                {
                    "id": "test-json",
                    "fetch": {"type": "local", "path": str(simple_json_schema_file)},
                    "convert": {"type": "json"}
                }
            ],
            "matchers": ["LogMap"]
        }
        manifest_file = temp_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))

        mock_run_alignment.return_value = []

        artifacts = orchestrate(manifest_file, workdir=temp_dir)

        # Verify pipeline execution
        assert "test-json" in artifacts.converted
        assert artifacts.converted["test-json"].exists()
        assert artifacts.merged_graph.exists()

    @pytest.mark.integration
    @pytest.mark.slow
    @patch('graph_mesh_orchestrator.pipeline.run_alignment')
    def test_mixed_sources_pipeline(self, mock_run_alignment, simple_xsd_file, simple_json_schema_file, temp_dir):
        """Test pipeline with mixed XSD and JSON sources."""
        manifest_data = {
            "name": "mixed-pipeline",
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
            "matchers": ["LogMap"]
        }
        manifest_file = temp_dir / "manifest.yaml"
        manifest_file.write_text(yaml.dump(manifest_data))

        mock_run_alignment.return_value = []

        artifacts = orchestrate(manifest_file, workdir=temp_dir)

        # Both sources should be processed
        assert len(artifacts.converted) == 2
        assert "xsd-source" in artifacts.converted
        assert "json-source" in artifacts.converted

        # Merged graph should contain both
        merged = Graph()
        merged.parse(str(artifacts.merged_graph))
        assert len(merged) > 0
