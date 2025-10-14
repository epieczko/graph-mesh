"""Converter interfaces and helper functions for schema ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class SchemaConverter(Protocol):
    """Protocol implemented by converters that yield OWL/RDF artifacts."""

    name: str

    def convert(self, source: Path, output_dir: Path) -> Path:
        """Convert ``source`` into an ontology stored under ``output_dir``."""


@dataclass
class TemplateConverter:
    """Declarative converter driven by manifest configuration."""

    name: str
    command_template: str

    def convert(self, source: Path, output_dir: Path) -> Path:
        from subprocess import check_call

        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{self.name.lower()}.owl"
        command = self.command_template.format(
            source=source.resolve(),
            output=output_path,
            output_dir=output_dir,
        )
        check_call(command, shell=True)
        return output_path
