"""
Unit tests for alignment matchers.

Tests cover:
- AlignmentMatcher protocol
- ContainerMatcher dataclass
- Docker container execution (mocked)
- Volume mounting configuration
- Error handling for Docker failures
- DEFAULT_MATCHERS configuration
- run_alignment orchestration
"""

from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest
from docker.errors import DockerException

from graph_mesh_aligner.matchers import (
    AlignmentMatcher,
    ContainerMatcher,
    DEFAULT_MATCHERS,
    run_alignment,
)


class TestAlignmentMatcherProtocol:
    """Test AlignmentMatcher protocol definition."""

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_protocol_has_name_attribute(self):
        """Test that protocol requires 'name' attribute."""
        # Create a mock matcher that satisfies the protocol
        matcher = Mock(spec=AlignmentMatcher)
        matcher.name = "TestMatcher"

        assert hasattr(matcher, "name")
        assert matcher.name == "TestMatcher"

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_protocol_has_align_method(self):
        """Test that protocol requires 'align' method."""
        matcher = Mock(spec=AlignmentMatcher)

        assert hasattr(matcher, "align")
        assert callable(matcher.align)


class TestContainerMatcher:
    """Test ContainerMatcher dataclass."""

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_container_matcher_creation(self):
        """Test creating a ContainerMatcher instance."""
        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        assert matcher.name == "TestMatcher"
        assert matcher.image == "test/matcher:latest"
        assert matcher.output_filename == "test.sssom.tsv"

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_container_matcher_has_align_method(self):
        """Test that ContainerMatcher has align method."""
        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        assert hasattr(matcher, "align")
        assert callable(matcher.align)

    @pytest.mark.unit
    @pytest.mark.matcher
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_creates_output_directory(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that align creates output directory if it doesn't exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "nested" / "output"

        result = matcher.align(source, target, output_dir)

        assert output_dir.exists()
        assert output_dir.is_dir()

    @pytest.mark.unit
    @pytest.mark.matcher
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_returns_mapping_path(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that align returns the expected mapping file path."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        result = matcher.align(source, target, output_dir)

        assert result == output_dir / "test.sssom.tsv"

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.docker
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_calls_docker_with_correct_params(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that Docker is called with correct parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        matcher.align(source, target, output_dir)

        # Verify Docker was called
        mock_docker.from_env.assert_called_once()
        mock_client.containers.run.assert_called_once()

        # Verify call parameters
        call_kwargs = mock_client.containers.run.call_args[1]
        assert call_kwargs["image"] == "test/matcher:latest"
        assert call_kwargs["remove"] is True
        assert call_kwargs["detach"] is False

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.docker
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_mounts_correct_volumes(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that volumes are mounted correctly."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        matcher.align(source, target, output_dir)

        # Verify volumes
        call_kwargs = mock_client.containers.run.call_args[1]
        volumes = call_kwargs["volumes"]

        assert str(source.resolve()) in volumes
        assert str(target.resolve()) in volumes
        assert str(output_dir.resolve()) in volumes

        # Verify volume bindings
        assert volumes[str(source.resolve())]["bind"] == "/data/source.owl"
        assert volumes[str(target.resolve())]["bind"] == "/data/target.owl"
        assert volumes[str(output_dir.resolve())]["bind"] == "/data/output"

        # Verify volume modes
        assert volumes[str(source.resolve())]["mode"] == "ro"
        assert volumes[str(target.resolve())]["mode"] == "ro"
        assert volumes[str(output_dir.resolve())]["mode"] == "rw"

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.docker
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_passes_correct_command(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that correct command is passed to container."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        matcher.align(source, target, output_dir)

        # Verify command
        call_kwargs = mock_client.containers.run.call_args[1]
        command = call_kwargs["command"]

        assert "--source" in command
        assert "/data/source.owl" in command
        assert "--target" in command
        assert "/data/target.owl" in command
        assert "--output" in command
        assert "/data/output/test.sssom.tsv" in command

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.docker
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_handles_docker_exception(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that Docker exceptions are handled and re-raised as RuntimeError."""
        # Setup mock to raise DockerException
        mock_client = MagicMock()
        mock_client.containers.run.side_effect = DockerException("Docker error")
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        with pytest.raises(RuntimeError, match="Failed to run matcher container"):
            matcher.align(source, target, output_dir)

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.docker
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_closes_docker_client(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that Docker client is closed after execution."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        matcher.align(source, target, output_dir)

        # Verify client was closed
        mock_client.close.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.docker
    @patch('graph_mesh_aligner.matchers.docker')
    def test_align_handles_client_close_exception(self, mock_docker, sample_ontology_file, temp_dir):
        """Test that exceptions during client.close() are silently ignored."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_client.close.side_effect = DockerException("Close error")
        mock_docker.from_env.return_value = mock_client

        matcher = ContainerMatcher(
            name="TestMatcher",
            image="test/matcher:latest",
            output_filename="test.sssom.tsv"
        )

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        # Should not raise even though close() fails
        result = matcher.align(source, target, output_dir)
        assert result is not None


class TestDefaultMatchers:
    """Test DEFAULT_MATCHERS configuration."""

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_default_matchers_is_tuple(self):
        """Test that DEFAULT_MATCHERS is a tuple."""
        assert isinstance(DEFAULT_MATCHERS, tuple)

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_default_matchers_count(self):
        """Test that DEFAULT_MATCHERS contains expected matchers."""
        assert len(DEFAULT_MATCHERS) == 3

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_default_matchers_names(self):
        """Test that all expected matchers are configured."""
        expected_names = {"LogMap", "AML", "BERTMap"}
        actual_names = {m.name for m in DEFAULT_MATCHERS}

        assert actual_names == expected_names

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_logmap_matcher_config(self):
        """Test LogMap matcher configuration."""
        logmap = [m for m in DEFAULT_MATCHERS if m.name == "LogMap"][0]

        assert logmap.image == "graph-mesh/logmap:latest"
        assert logmap.output_filename == "logmap.sssom.tsv"

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_aml_matcher_config(self):
        """Test AML matcher configuration."""
        aml = [m for m in DEFAULT_MATCHERS if m.name == "AML"][0]

        assert aml.image == "graph-mesh/aml:latest"
        assert aml.output_filename == "aml.sssom.tsv"

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_bertmap_matcher_config(self):
        """Test BERTMap matcher configuration."""
        bertmap = [m for m in DEFAULT_MATCHERS if m.name == "BERTMap"][0]

        assert bertmap.image == "graph-mesh/bertmap:latest"
        assert bertmap.output_filename == "bertmap.sssom.tsv"

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_all_matchers_have_unique_output_files(self):
        """Test that all matchers have unique output filenames."""
        filenames = [m.output_filename for m in DEFAULT_MATCHERS]
        assert len(filenames) == len(set(filenames))


class TestRunAlignment:
    """Test run_alignment orchestration function."""

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_run_alignment_with_single_matcher(self, sample_ontology_file, temp_dir):
        """Test running alignment with a single matcher."""
        # Create a mock matcher
        mock_matcher = Mock()
        mock_matcher.name = "TestMatcher"
        mapping_path = temp_dir / "test.sssom.tsv"
        mock_matcher.align.return_value = mapping_path

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        results = run_alignment([mock_matcher], source, target, output_dir)

        assert len(results) == 1
        assert results[0] == mapping_path
        mock_matcher.align.assert_called_once_with(source, target, output_dir)

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_run_alignment_with_multiple_matchers(self, sample_ontology_file, temp_dir):
        """Test running alignment with multiple matchers."""
        # Create mock matchers
        mock_matcher1 = Mock()
        mock_matcher1.name = "Matcher1"
        mapping_path1 = temp_dir / "matcher1.sssom.tsv"
        mock_matcher1.align.return_value = mapping_path1

        mock_matcher2 = Mock()
        mock_matcher2.name = "Matcher2"
        mapping_path2 = temp_dir / "matcher2.sssom.tsv"
        mock_matcher2.align.return_value = mapping_path2

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        results = run_alignment([mock_matcher1, mock_matcher2], source, target, output_dir)

        assert len(results) == 2
        assert results[0] == mapping_path1
        assert results[1] == mapping_path2

        mock_matcher1.align.assert_called_once()
        mock_matcher2.align.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_run_alignment_with_no_matchers(self, sample_ontology_file, temp_dir):
        """Test running alignment with empty matcher list."""
        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        results = run_alignment([], source, target, output_dir)

        assert results == []

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_run_alignment_passes_correct_params(self, sample_ontology_file, temp_dir):
        """Test that run_alignment passes correct parameters to matchers."""
        mock_matcher = Mock()
        mock_matcher.name = "TestMatcher"
        mapping_path = temp_dir / "test.sssom.tsv"
        mock_matcher.align.return_value = mapping_path

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        run_alignment([mock_matcher], source, target, output_dir)

        # Verify the matcher was called with exact parameters
        mock_matcher.align.assert_called_once_with(source, target, output_dir)

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_run_alignment_preserves_order(self, sample_ontology_file, temp_dir):
        """Test that run_alignment preserves matcher execution order."""
        matchers = []
        expected_paths = []

        for i in range(5):
            mock_matcher = Mock()
            mock_matcher.name = f"Matcher{i}"
            mapping_path = temp_dir / f"matcher{i}.sssom.tsv"
            mock_matcher.align.return_value = mapping_path
            matchers.append(mock_matcher)
            expected_paths.append(mapping_path)

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        results = run_alignment(matchers, source, target, output_dir)

        assert results == expected_paths

    @pytest.mark.unit
    @pytest.mark.matcher
    def test_run_alignment_propagates_exceptions(self, sample_ontology_file, temp_dir):
        """Test that exceptions from matchers are propagated."""
        mock_matcher = Mock()
        mock_matcher.name = "FailingMatcher"
        mock_matcher.align.side_effect = RuntimeError("Matcher failed")

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        with pytest.raises(RuntimeError, match="Matcher failed"):
            run_alignment([mock_matcher], source, target, output_dir)

    @pytest.mark.unit
    @pytest.mark.matcher
    @pytest.mark.slow
    @patch('graph_mesh_aligner.matchers.docker')
    def test_run_alignment_with_default_matchers(self, mock_docker, sample_ontology_file, temp_dir):
        """Test running alignment with DEFAULT_MATCHERS."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.run.return_value = b"Success"
        mock_docker.from_env.return_value = mock_client

        source = sample_ontology_file
        target = sample_ontology_file
        output_dir = temp_dir / "output"

        results = run_alignment(DEFAULT_MATCHERS, source, target, output_dir)

        # Should have 3 results (LogMap, AML, BERTMap)
        assert len(results) == 3

        # Verify all expected files
        expected_files = {"logmap.sssom.tsv", "aml.sssom.tsv", "bertmap.sssom.tsv"}
        actual_files = {r.name for r in results}
        assert actual_files == expected_files
