"""Unified pipeline orchestrating fetch → ingest → align → fuse → validate."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

import structlog
import yaml
from rdflib import Graph

from graph_mesh_aligner.matchers import DEFAULT_MATCHERS, ContainerMatcher, run_alignment
from graph_mesh_core.meta_ontology import build_meta_graph, serialize_meta_graph
from graph_mesh_orchestrator.errors import (
    CheckpointError,
    FetchError,
    FusionError,
    PipelineError,
    PipelineStateError,
    RecoverableError,
)
from graph_mesh_orchestrator.ingest import run_ingest
from graph_mesh_orchestrator.models import (
    PipelineCheckpoint,
    PipelineManifest,
    PipelineState,
    SourceState,
)
from graph_mesh_orchestrator.validation import run_preflight_checks

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if sys.stderr.isatty() else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger(__name__)

MATCHER_REGISTRY: Dict[str, ContainerMatcher] = {matcher.name: matcher for matcher in DEFAULT_MATCHERS}


@dataclass
class PipelineArtifacts:
    workdir: Path
    meta_ontology: Path
    converted: dict[str, Path]
    mappings: dict[str, list[Path]]
    merged_graph: Path


def load_manifest(path: Path) -> PipelineManifest:
    """Load and validate pipeline manifest.

    Args:
        path: Path to manifest file

    Returns:
        Validated PipelineManifest

    Raises:
        ManifestValidationError: If manifest validation fails
    """
    logger.info("loading_manifest", path=str(path))
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return PipelineManifest.model_validate(data)


def fetch_source(source, workdir):
    """Fetch source data based on configuration.

    Args:
        source: SourceConfig instance
        workdir: Working directory for artifacts

    Returns:
        Path or list of paths to fetched data

    Raises:
        FetchError: If fetch operation fails
    """
    try:
        fetch_info = source.fetch
        fetch_type = fetch_info.type.value if hasattr(fetch_info.type, 'value') else str(fetch_info.type)

        # Handle multiple paths (list) or single path (string)
        paths = fetch_info.paths or ([fetch_info.path] if fetch_info.path else [])
        resolved_paths = [str(Path(p).resolve()) for p in paths if p]

        if not resolved_paths:
            raise FetchError(
                f"No paths configured for source",
                source_id=source.id,
                fetch_type=fetch_type
            )

        if fetch_type == "local":
            # Validate paths exist
            for path in resolved_paths:
                if not Path(path).exists():
                    raise FetchError(
                        f"Local file not found: {path}",
                        source_id=source.id,
                        fetch_type=fetch_type,
                        path=path
                    )

            if len(resolved_paths) == 1:
                resolved = resolved_paths[0]
                logger.info("fetched_local_file", source_id=source.id, path=resolved)
            else:
                resolved = resolved_paths
                logger.info("fetched_multiple_files", source_id=source.id, count=len(resolved))

            return resolved

        raise FetchError(
            f"Unsupported fetch type: {fetch_type}",
            source_id=source.id,
            fetch_type=fetch_type
        )

    except FetchError:
        raise
    except Exception as e:
        raise FetchError(
            f"Fetch failed: {str(e)}",
            source_id=source.id if hasattr(source, 'id') else 'unknown'
        ) from e



def fuse_graphs(graphs: Iterable[Path], meta_graph: Graph, output_path: Path) -> Path:
    """Fuse multiple OWL graphs with meta-ontology.

    Args:
        graphs: Iterable of graph file paths
        meta_graph: Meta-ontology graph
        output_path: Output path for merged graph

    Returns:
        Path to merged graph

    Raises:
        FusionError: If graph fusion fails
    """
    try:
        logger.info("fusing_graphs", graph_count=len(list(graphs)), output=str(output_path))
        combined = Graph()
        combined += meta_graph

        graph_list = list(graphs)
        for i, graph_path in enumerate(graph_list):
            logger.debug("parsing_graph", index=i + 1, total=len(graph_list), path=str(graph_path))
            combined.parse(graph_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.serialize(destination=output_path, format="turtle")
        logger.info("fusion_complete", output=str(output_path), triple_count=len(combined))
        return output_path

    except Exception as e:
        raise FusionError(
            f"Graph fusion failed: {str(e)}",
            graph_count=len(list(graphs))
        ) from e


def save_checkpoint(
    checkpoint: PipelineCheckpoint,
    workdir: Path
) -> None:
    """Save pipeline checkpoint.

    Args:
        checkpoint: Checkpoint data
        workdir: Working directory

    Raises:
        CheckpointError: If checkpoint save fails
    """
    try:
        checkpoint_path = workdir / "checkpoint.json"
        checkpoint.to_file(checkpoint_path)
        logger.debug("checkpoint_saved", path=str(checkpoint_path))
    except Exception as e:
        raise CheckpointError(
            f"Failed to save checkpoint: {str(e)}",
            checkpoint_path=str(checkpoint_path),
            operation="save"
        ) from e


def load_checkpoint(workdir: Path) -> Optional[PipelineCheckpoint]:
    """Load pipeline checkpoint if it exists.

    Args:
        workdir: Working directory

    Returns:
        Checkpoint data or None if not found

    Raises:
        CheckpointError: If checkpoint load fails
    """
    checkpoint_path = workdir / "checkpoint.json"
    if not checkpoint_path.exists():
        return None

    try:
        checkpoint = PipelineCheckpoint.from_file(checkpoint_path)
        logger.info("checkpoint_loaded", state=checkpoint.state.value)
        return checkpoint
    except Exception as e:
        raise CheckpointError(
            f"Failed to load checkpoint: {str(e)}",
            checkpoint_path=str(checkpoint_path),
            operation="load"
        ) from e


def orchestrate(
    manifest_path: Path,
    workdir: Path | None = None,
    resume: bool = False,
    skip_preflight: bool = False,
    max_retries: int = 3
) -> PipelineArtifacts:
    """Orchestrate the complete pipeline with state management and resume capability.

    Args:
        manifest_path: Path to pipeline manifest
        workdir: Working directory for artifacts
        resume: Whether to resume from checkpoint
        skip_preflight: Skip pre-flight validation checks
        max_retries: Maximum retry attempts for recoverable errors

    Returns:
        PipelineArtifacts with paths to all outputs

    Raises:
        PipelineError: If pipeline execution fails
    """
    workdir = (workdir or Path("artifacts")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    log = logger.bind(manifest=str(manifest_path), workdir=str(workdir))

    # Initialize or load checkpoint
    checkpoint = None
    if resume:
        checkpoint = load_checkpoint(workdir)
        if checkpoint and checkpoint.can_resume():
            log.info("resuming_pipeline", state=checkpoint.state.value)
        else:
            log.warning("no_valid_checkpoint", resuming_from_start=True)
            checkpoint = None

    # Pre-flight checks (unless skipped or resuming)
    if not skip_preflight and not checkpoint:
        log.info("running_preflight_checks")
        try:
            run_preflight_checks(manifest_path, workdir, check_docker=True, strict=False)
        except Exception as e:
            log.warning("preflight_check_failed", error=str(e))

    # Load and validate manifest
    log.info("loading_manifest")
    manifest = load_manifest(manifest_path)

    # Initialize checkpoint if not resuming
    if not checkpoint:
        checkpoint = PipelineCheckpoint(
            manifest_path=str(manifest_path),
            workdir=str(workdir),
            state=PipelineState.PENDING,
            current_stage="initialization",
            sources={src.id: SourceState(source_id=src.id) for src in manifest.sources},
            timestamp=datetime.utcnow().isoformat()
        )

    # Track artifacts
    fetched: dict[str, Path] = {}
    converted: dict[str, Path] = {}
    mappings: dict[str, list[Path]] = {}

    try:
        # Stage 1: Meta-ontology preparation
        if not checkpoint.meta_ontology_path:
            log.info("stage_meta_ontology", stage="preparation")
            checkpoint.state = PipelineState.VALIDATING
            checkpoint.current_stage = "meta_ontology"
            save_checkpoint(checkpoint, workdir)

            meta_path = serialize_meta_graph(workdir / "meta" / "meta-ontology.ttl")
            checkpoint.meta_ontology_path = str(meta_path)
            save_checkpoint(checkpoint, workdir)
        else:
            meta_path = Path(checkpoint.meta_ontology_path)
            log.info("meta_ontology_exists", path=str(meta_path))

        meta_graph = build_meta_graph()

        # Stage 2: Fetch sources
        log.info("stage_fetch", stage="fetch", source_count=len(manifest.sources))
        checkpoint.state = PipelineState.FETCHING
        checkpoint.current_stage = "fetch"
        save_checkpoint(checkpoint, workdir)

        for source in manifest.sources:
            if not source.enabled:
                log.info("source_disabled", source_id=source.id)
                continue

            source_state = checkpoint.sources.get(source.id)
            if source_state and source_state.fetched and source_state.fetch_path:
                log.info("source_already_fetched", source_id=source.id)
                fetched[source.id] = Path(source_state.fetch_path)
                continue

            log.info("fetching_source", source_id=source.id)
            try:
                raw_path = fetch_source(source, workdir)
                fetched[source.id] = raw_path if isinstance(raw_path, Path) else Path(str(raw_path))

                # Update checkpoint
                source_state.fetched = True
                source_state.fetch_path = str(raw_path)
                save_checkpoint(checkpoint, workdir)

            except RecoverableError as e:
                if e.can_retry():
                    log.warning("fetch_failed_retrying", source_id=source.id, error=str(e))
                    time.sleep(2)
                    # Retry logic could be more sophisticated
                    continue
                raise

        # Stage 3: Ingest (convert to OWL)
        log.info("stage_ingest", stage="ingest", source_count=len(fetched))
        checkpoint.state = PipelineState.INGESTING
        checkpoint.current_stage = "ingest"
        save_checkpoint(checkpoint, workdir)

        # Check for already converted sources
        sources_to_convert = []
        for source in manifest.sources:
            if not source.enabled or source.id not in fetched:
                continue

            source_state = checkpoint.sources.get(source.id)
            if source_state and source_state.ingested and source_state.converted_path:
                log.info("source_already_converted", source_id=source.id)
                converted[source.id] = Path(source_state.converted_path)
            else:
                sources_to_convert.append(source)

        # Convert remaining sources
        if sources_to_convert:
            fetched_for_ingest = {src.id: fetched[src.id] for src in sources_to_convert if src.id in fetched}
            newly_converted = run_ingest(sources_to_convert, fetched_for_ingest, workdir)
            converted.update(newly_converted)

            # Update checkpoint for newly converted sources
            for source_id, converted_path in newly_converted.items():
                source_state = checkpoint.sources.get(source_id)
                if source_state:
                    source_state.ingested = True
                    source_state.converted_path = str(converted_path)
            save_checkpoint(checkpoint, workdir)

        # Stage 4: Alignment
        log.info("stage_alignment", stage="alignment")
        checkpoint.state = PipelineState.ALIGNING
        checkpoint.current_stage = "alignment"
        save_checkpoint(checkpoint, workdir)

        for source in manifest.sources:
            if not source.enabled or source.id not in converted:
                continue

            source_state = checkpoint.sources.get(source.id)
            if source_state and source_state.aligned and source_state.mapping_paths:
                log.info("source_already_aligned", source_id=source.id)
                mappings[source.id] = [Path(p) for p in source_state.mapping_paths]
                continue

            log.info("aligning_source", source_id=source.id)
            converted_path = converted[source.id]

            matcher_names = manifest.matchers
            selected_matchers = [MATCHER_REGISTRY[name] for name in matcher_names if name in MATCHER_REGISTRY]

            if not selected_matchers:
                log.warning("no_matchers_available", source_id=source.id)
                continue

            mapping_dir = workdir / "mappings" / source.id
            try:
                mapping_paths = run_alignment(
                    selected_matchers,
                    converted_path,
                    meta_path,
                    mapping_dir,
                )
                mappings[source.id] = mapping_paths

                # Update checkpoint
                source_state.aligned = True
                source_state.mapping_paths = [str(p) for p in mapping_paths]
                save_checkpoint(checkpoint, workdir)

            except Exception as e:
                log.error("alignment_failed", source_id=source.id, error=str(e))
                # Continue with other sources even if one fails
                source_state.error = str(e)
                save_checkpoint(checkpoint, workdir)

        # Stage 5: Fusion
        log.info("stage_fusion", stage="fusion")
        checkpoint.state = PipelineState.FUSING
        checkpoint.current_stage = "fusion"
        save_checkpoint(checkpoint, workdir)

        merged_path = fuse_graphs(converted.values(), meta_graph, workdir / "graph-mesh-merged.ttl")
        checkpoint.merged_graph_path = str(merged_path)

        # Mark as complete
        checkpoint.state = PipelineState.COMPLETED
        checkpoint.current_stage = "completed"
        save_checkpoint(checkpoint, workdir)

        log.info("pipeline_complete", merged_graph=str(merged_path))

        return PipelineArtifacts(
            workdir=workdir,
            meta_ontology=meta_path,
            converted=converted,
            mappings=mappings,
            merged_graph=merged_path,
        )

    except Exception as e:
        log.error("pipeline_failed", error=str(e), stage=checkpoint.current_stage)
        checkpoint.state = PipelineState.FAILED
        checkpoint.error_message = str(e)
        save_checkpoint(checkpoint, workdir)
        raise PipelineError(f"Pipeline execution failed: {str(e)}") from e


def main(manifest_path: str, workdir: Optional[str] = None, resume: bool = False) -> None:
    """Main entry point for pipeline orchestration.

    Args:
        manifest_path: Path to pipeline manifest
        workdir: Working directory for artifacts
        resume: Whether to resume from checkpoint
    """
    logging.basicConfig(level=logging.INFO)

    try:
        workdir_path = Path(workdir) if workdir else None
        artifacts = orchestrate(
            manifest_path=Path(manifest_path),
            workdir=workdir_path,
            resume=resume,
            skip_preflight=False
        )
        logger.info("pipeline_success", artifacts={
            "workdir": str(artifacts.workdir),
            "meta_ontology": str(artifacts.meta_ontology),
            "merged_graph": str(artifacts.merged_graph),
            "converted_count": len(artifacts.converted),
        })
    except Exception as e:
        logger.error("pipeline_failed", error=str(e), error_type=type(e).__name__)
        raise


if __name__ == "__main__":  # pragma: no cover - CLI entry
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the Graph-Mesh pipeline with validation and state management"
    )
    parser.add_argument("manifest", type=str, help="Path to pipeline manifest YAML")
    parser.add_argument(
        "--workdir",
        type=str,
        default=None,
        help="Working directory for artifacts (default: ./artifacts)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available"
    )
    args = parser.parse_args()
    main(args.manifest, workdir=args.workdir, resume=args.resume)
