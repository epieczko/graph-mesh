"""Unified pipeline orchestrating fetch → ingest → align → fuse → validate."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

import yaml
from rdflib import Graph

from graph_mesh_aligner.matchers import DEFAULT_MATCHERS, ContainerMatcher, run_alignment
from graph_mesh_core.meta_ontology import build_meta_graph, serialize_meta_graph
from graph_mesh_orchestrator.ingest import run_ingest

LOGGER = logging.getLogger(__name__)

MATCHER_REGISTRY: Dict[str, ContainerMatcher] = {matcher.name: matcher for matcher in DEFAULT_MATCHERS}


@dataclass
class SourceConfig:
    identifier: str
    fetch: dict
    convert: dict

    @classmethod
    def from_dict(cls, data: dict) -> "SourceConfig":
        return cls(
            identifier=data["id"],
            fetch=data.get("fetch", {}),
            convert=data.get("convert", {}),
        )


@dataclass
class PipelineManifest:
    name: str
    sources: list[SourceConfig]
    matchers: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "PipelineManifest":
        sources = [SourceConfig.from_dict(item) for item in data.get("sources", [])]
        return cls(
            name=data["name"],
            sources=sources,
            matchers=data.get("matchers", [matcher.name for matcher in DEFAULT_MATCHERS]),
        )


@dataclass
class PipelineArtifacts:
    workdir: Path
    meta_ontology: Path
    converted: dict[str, Path]
    mappings: dict[str, list[Path]]
    merged_graph: Path


def load_manifest(path: Path) -> PipelineManifest:
    return PipelineManifest.from_dict(yaml.safe_load(path.read_text()))


def fetch_source(source, workdir):
    # source is a SourceConfig instance
    fetch_info = source.fetch or {}
    fetch_type = fetch_info.get("type", "local")

    # Handle multiple paths (list) or single path (string)
    paths = fetch_info.get("paths") or [fetch_info.get("path")]
    resolved_paths = [str(Path(p).resolve()) for p in paths if p]

    if fetch_type == "local":
        if len(resolved_paths) == 1:
            resolved = resolved_paths[0]
            print(f"📂  Using local file: {resolved}")
        else:
            resolved = resolved_paths
            print(f"📂  Using multiple local files:\n    - " + "\n    - ".join(resolved))
        return resolved

    raise NotImplementedError(f"Unsupported fetch type: {fetch_type}")



def fuse_graphs(graphs: Iterable[Path], meta_graph: Graph, output_path: Path) -> Path:
    combined = Graph()
    combined += meta_graph
    for graph_path in graphs:
        combined.parse(graph_path)
    combined.serialize(destination=output_path, format="turtle")
    return output_path


def orchestrate(manifest_path: Path, workdir: Path | None = None) -> PipelineArtifacts:
    workdir = (workdir or Path("artifacts")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading manifest from %s", manifest_path)
    manifest = load_manifest(manifest_path)

    LOGGER.info("Preparing meta-ontology scaffold")
    meta_path = serialize_meta_graph(workdir / "meta" / "meta-ontology.ttl")
    meta_graph = build_meta_graph()

    fetched: dict[str, Path] = {}
    converted: dict[str, Path] = {}
    mappings: dict[str, list[Path]] = {}

    for source in manifest.sources:
        LOGGER.info("Processing source %s", source.identifier)
        raw_path = fetch_source(source, workdir)
        fetched[source.identifier] = raw_path

    LOGGER.info("Running ingest stage for %d sources", len(fetched))
    converted.update(run_ingest(manifest.sources, fetched, workdir))

    for source in manifest.sources:
        converted_path = converted[source.identifier]

        matcher_names = manifest.matchers
        selected_matchers = [MATCHER_REGISTRY[name] for name in matcher_names]
        mapping_dir = workdir / "mappings" / source.identifier
        mappings[source.identifier] = run_alignment(
            selected_matchers,
            converted_path,
            meta_path,
            mapping_dir,
        )

    merged_path = fuse_graphs(converted.values(), meta_graph, workdir / "graph-mesh-merged.ttl")

    return PipelineArtifacts(
        workdir=workdir,
        meta_ontology=meta_path,
        converted=converted,
        mappings=mappings,
        merged_graph=merged_path,
    )


def main(manifest_path: str) -> None:
    logging.basicConfig(level=logging.INFO)
    orchestrate(Path(manifest_path))


if __name__ == "__main__":  # pragma: no cover - CLI entry
    import argparse

    parser = argparse.ArgumentParser(description="Run the Graph-Mesh pipeline")
    parser.add_argument("manifest", type=str, help="Path to pipeline manifest YAML")
    args = parser.parse_args()
    main(args.manifest)
