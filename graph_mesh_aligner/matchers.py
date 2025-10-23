"""Alignment runner abstractions for LogMap, AML, and BERTMap."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol

import docker
from docker.errors import DockerException

LOGGER = logging.getLogger(__name__)


class AlignmentMatcher(Protocol):
    """Common protocol for ontology matchers."""

    name: str

    def align(self, source_ontology: Path, target_ontology: Path, output_dir: Path) -> Path:
        """Run the matcher and return the path to the produced SSSOM mapping."""


@dataclass
class MatcherResult:
    """Result from running a matcher."""

    matcher_name: str
    mapping_path: Path
    success: bool
    execution_time: float
    error_message: str | None = None


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
    timeout: int = 300  # Default 5 minutes timeout
    health_check_enabled: bool = True

    def _check_image_health(self, client: docker.DockerClient) -> bool:
        """Check if the Docker image is available and healthy."""
        try:
            client.images.get(self.image)
            LOGGER.debug(f"Health check passed for {self.name} image: {self.image}")
            return True
        except docker.errors.ImageNotFound:
            LOGGER.warning(f"Health check failed: Image not found for {self.name}: {self.image}")
            return False
        except DockerException as exc:
            LOGGER.warning(f"Health check failed for {self.name}: {exc}")
            return False

    def align(self, source_ontology: Path, target_ontology: Path, output_dir: Path) -> Path:
        """Synchronous alignment (backward compatible)."""
        resolved_source = source_ontology.resolve()
        resolved_target = target_ontology.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = output_dir / self.output_filename

        client = docker.from_env()
        try:
            # Health check before running
            if self.health_check_enabled and not self._check_image_health(client):
                raise RuntimeError(f"Health check failed for {self.name}")

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

    async def align_async(
        self, source_ontology: Path, target_ontology: Path, output_dir: Path
    ) -> MatcherResult:
        """Asynchronous alignment with timeout and error handling."""
        start_time = time.time()
        resolved_source = source_ontology.resolve()
        resolved_target = target_ontology.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        mapping_path = output_dir / self.output_filename

        try:
            # Run the blocking Docker operation in a thread pool
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self._run_container_sync,
                    resolved_source,
                    resolved_target,
                    output_dir,
                    mapping_path,
                ),
                timeout=self.timeout,
            )

            execution_time = time.time() - start_time
            LOGGER.info(f"✓ {self.name} completed in {execution_time:.2f}s")

            return MatcherResult(
                matcher_name=self.name,
                mapping_path=mapping_path,
                success=True,
                execution_time=execution_time,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error_msg = f"Timeout after {self.timeout}s"
            LOGGER.error(f"✗ {self.name} failed: {error_msg}")
            return MatcherResult(
                matcher_name=self.name,
                mapping_path=mapping_path,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
            )

        except Exception as exc:
            execution_time = time.time() - start_time
            error_msg = str(exc)
            LOGGER.error(f"✗ {self.name} failed: {error_msg}")
            return MatcherResult(
                matcher_name=self.name,
                mapping_path=mapping_path,
                success=False,
                execution_time=execution_time,
                error_message=error_msg,
            )

    def _run_container_sync(
        self,
        resolved_source: Path,
        resolved_target: Path,
        output_dir: Path,
        mapping_path: Path,
    ) -> Path:
        """Synchronous container execution (called from async context)."""
        client = docker.from_env()
        try:
            # Health check before running
            if self.health_check_enabled and not self._check_image_health(client):
                raise RuntimeError(f"Health check failed for {self.name}")

            LOGGER.info(f"→ Starting {self.name}...")

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

            if logs:
                log_str = logs.decode("utf-8") if isinstance(logs, (bytes, bytearray)) else logs
                LOGGER.debug(f"{self.name} output:\n{log_str}")

            return mapping_path

        except DockerException as exc:
            raise RuntimeError(
                f"Failed to run matcher container '{self.image}' for {self.name}"
            ) from exc
        finally:
            try:
                client.close()
            except DockerException:
                pass


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
    """Execute all configured matchers sequentially (backward compatible).

    For parallel execution with better performance, use run_alignment_parallel().
    """
    results: list[Path] = []
    for matcher in matchers:
        mapping = matcher.align(source_ontology, target_ontology, output_dir)
        results.append(mapping)
    return results


async def run_alignment_async(
    matchers: Iterable[ContainerMatcher],
    source_ontology: Path,
    target_ontology: Path,
    output_dir: Path,
) -> list[MatcherResult]:
    """Execute all matchers in parallel using asyncio.

    This provides significant speedup (typically 3x) compared to sequential execution.
    Returns detailed results including execution times and error information.
    """
    LOGGER.info(f"Starting parallel alignment with {len(list(matchers))} matchers")
    start_time = time.time()

    # Create tasks for all matchers
    tasks = [
        matcher.align_async(source_ontology, target_ontology, output_dir)
        for matcher in matchers
    ]

    # Run all matchers in parallel
    results = await asyncio.gather(*tasks, return_exceptions=False)

    total_time = time.time() - start_time
    successful = sum(1 for r in results if r.success)

    LOGGER.info(
        f"Parallel alignment completed in {total_time:.2f}s "
        f"({successful}/{len(results)} matchers succeeded)"
    )

    return results


def run_alignment_parallel(
    matchers: Iterable[ContainerMatcher],
    source_ontology: Path,
    target_ontology: Path,
    output_dir: Path,
) -> list[MatcherResult]:
    """Synchronous wrapper for parallel alignment execution.

    This is the recommended function for running matchers in parallel.
    It provides approximately 3x speedup over sequential execution.
    """
    return asyncio.run(
        run_alignment_async(matchers, source_ontology, target_ontology, output_dir)
    )
