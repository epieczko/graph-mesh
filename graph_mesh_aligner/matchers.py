"""Alignment runner abstractions for LogMap, AML, and BERTMap."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

import docker
from docker.errors import DockerException


class AlignmentMatcher(Protocol):
    """Common protocol for ontology matchers."""

    name: str

    def align(self, source_ontology: Path, target_ontology: Path, output_dir: Path) -> Path:
        """Run the matcher and return the path to the produced SSSOM mapping."""


@dataclass
class ContainerMatcher:
    """Containerized matcher definition.

    Each matcher is executed inside its dedicated Docker container. The class
    stores the container image name and the expected output file name used when
    invoking the matcher CLI inside the container.
    """

    name: str
    image: str
    output_filename: str

    def align(self, source_ontology: Path, target_ontology: Path, output_dir: Path) -> Path:
        resolved_source = source_ontology.resolve()
        resolved_target = target_ontology.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = output_dir / self.output_filename

        client = docker.from_env()
        try:
            logs = client.containers.run(
                image=self.image,
                command=[
                    "--source",
                    "/data/source.owl",
                    "--target",
                    "/data/target.owl",
                    "--output",
                    f"/data/output/{self.output_filename}",
                ],
                volumes={
                    str(resolved_source): {"bind": "/data/source.owl", "mode": "ro"},
                    str(resolved_target): {"bind": "/data/target.owl", "mode": "ro"},
                    str(output_dir): {"bind": "/data/output", "mode": "rw"},
                },
                remove=True,
                detach=False,
            )
        except DockerException as exc:
            raise RuntimeError(
                f"Failed to run matcher container '{self.image}' for {self.name}"
            ) from exc
        finally:
            try:
                client.close()
            except DockerException:
                pass

        if logs:
            # The Docker SDK returns container logs as bytes when detach=False.
            print(logs.decode("utf-8") if isinstance(logs, (bytes, bytearray)) else logs)

        return mapping_path


DEFAULT_MATCHERS: tuple[ContainerMatcher, ...] = (
    ContainerMatcher(
        name="LogMap",
        image="graph-mesh/logmap:latest",
        output_filename="logmap.sssom.tsv",
    ),
    ContainerMatcher(
        name="AML",
        image="graph-mesh/aml:latest",
        output_filename="aml.sssom.tsv",
    ),
    ContainerMatcher(
        name="BERTMap",
        image="graph-mesh/bertmap:latest",
        output_filename="bertmap.sssom.tsv",
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
