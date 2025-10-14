"""Alignment runner abstractions for LogMap, AML, and BERTMap."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol


class AlignmentMatcher(Protocol):
    """Common protocol for ontology matchers."""

    name: str

    def align(self, source_ontology: Path, target_ontology: Path, output_dir: Path) -> Path:
        """Run the matcher and return the path to the produced SSSOM mapping."""


@dataclass
class ContainerMatcher:
    """Containerized matcher definition.

    Each matcher is executed inside its dedicated Docker container. The class
    stores the container image name and the command that should be executed to
    perform the alignment.
    """

    name: str
    image: str
    command_template: str

    def align(self, source_ontology: Path, target_ontology: Path, output_dir: Path) -> Path:
        from subprocess import check_call

        resolved_source = source_ontology.resolve()
        resolved_target = target_ontology.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = output_dir / f"{self.name.lower()}.sssom.tsv"
        command = self.command_template.format(
            image=self.image,
            source=resolved_source,
            target=resolved_target,
            output=mapping_path,
            output_dir=output_dir,
        )
        check_call(command, shell=True)
        return mapping_path


DEFAULT_MATCHERS: tuple[ContainerMatcher, ...] = (
    ContainerMatcher(
        name="LogMap",
        image="graph-mesh/logmap:latest",
        command_template=(
            "docker run --rm "
            "-v {source}:/data/source.owl "
            "-v {target}:/data/target.owl "
            "-v {output_dir}:/data/output "
            "{image} --source /data/source.owl --target /data/target.owl --output /data/output/logmap.sssom.tsv"
        ),
    ),
    ContainerMatcher(
        name="AML",
        image="graph-mesh/aml:latest",
        command_template=(
            "docker run --rm "
            "-v {source}:/data/source.owl "
            "-v {target}:/data/target.owl "
            "-v {output_dir}:/data/output "
            "{image} --source /data/source.owl --target /data/target.owl --output /data/output/aml.sssom.tsv"
        ),
    ),
    ContainerMatcher(
        name="BERTMap",
        image="graph-mesh/bertmap:latest",
        command_template=(
            "docker run --rm "
            "-v {source}:/data/source.owl "
            "-v {target}:/data/target.owl "
            "-v {output_dir}:/data/output "
            "{image} --source /data/source.owl --target /data/target.owl --output /data/output/bertmap.sssom.tsv"
        ),
    ),
)


def run_alignment(
    matchers: Iterable[AlignmentMatcher],
    source_ontology: Path,
    target_ontology: Path,
    output_dir: Path,
) -> list[Path]:
    """Execute all configured matchers and return the produced mapping paths."""

    results: list[Path] = []
    for matcher in matchers:
        mapping = matcher.align(source_ontology, target_ontology, output_dir)
        results.append(mapping)
    return results
