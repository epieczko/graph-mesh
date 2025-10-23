"""
Tests for orchestrator pipeline.
"""
import pytest
from pathlib import Path
import yaml
from graph_mesh_orchestrator.pipeline import load_manifest, PipelineManifest


class TestOrchestrator:
    """Test suite for orchestrator functionality."""

    @pytest.fixture
    def sample_manifest(self):
        """Sample manifest for testing."""
        return {
            "name": "test-pipeline",
            "matchers": ["logmap"],
            "sources": [
                {
                    "id": "source1",
                    "fetch": {
                        "type": "file",
                        "path": "test.xsd"
                    },
                    "convert": {
                        "type": "xsd"
                    }
                }
            ]
        }

    def test_load_manifest(self, sample_manifest, temp_dir):
        """Test loading pipeline manifest from YAML."""
        manifest_path = temp_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(sample_manifest))

        result = load_manifest(manifest_path)

        assert isinstance(result, PipelineManifest), \
            "Should return PipelineManifest instance"
        assert result.name == "test-pipeline", \
            "Manifest name should match"
        assert "logmap" in result.matchers, \
            "Matchers should be loaded"
        assert len(result.sources) == 1, \
            "Should have one source"

    def test_manifest_validation(self, temp_dir):
        """Test manifest validation for required fields."""
        invalid_manifest = {"name": "test"}  # Missing required fields
        manifest_path = temp_dir / "invalid_manifest.yaml"
        manifest_path.write_text(yaml.dump(invalid_manifest))

        # Should raise error for invalid manifest
        with pytest.raises((KeyError, ValueError, AttributeError)):
            load_manifest(manifest_path)

    def test_pipeline_artifacts_structure(self):
        """Test PipelineArtifacts dataclass structure."""
        from graph_mesh_orchestrator.pipeline import PipelineArtifacts
        from pathlib import Path

        artifacts = PipelineArtifacts(
            base_dir=Path("/tmp/artifacts"),
            meta_ontology=Path("/tmp/artifacts/meta.ttl"),
            converted_graphs={},
            mappings={},
            merged_graph=Path("/tmp/artifacts/merged.ttl")
        )

        assert artifacts.base_dir == Path("/tmp/artifacts"), \
            "Base directory should be set correctly"
        assert isinstance(artifacts.converted_graphs, dict), \
            "Converted graphs should be a dictionary"
