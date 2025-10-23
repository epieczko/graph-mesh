"""Ingest stage for the Graph Mesh orchestrator.

This module uses the graph_mesh_ingest plugin system to convert various
schema formats (XSD, JSON Schema, CSV/TSV) to OWL ontologies.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping
import logging

from graph_mesh_ingest import get_converter, ConverterRegistry
from graph_mesh_ingest.xsd_to_owl import convert_xsd_list_to_owl

logger = logging.getLogger(__name__)


def _get_identifier(source: Any) -> str:
    """Extract identifier from source configuration.

    Args:
        source: Source configuration object or mapping

    Returns:
        Source identifier

    Raises:
        KeyError: If identifier not found
    """
    if hasattr(source, "identifier"):
        return getattr(source, "identifier")
    if isinstance(source, Mapping) and "id" in source:
        return str(source["id"])
    raise KeyError("Source configuration must define an identifier")


def _get_convert_config(source: Any) -> Mapping[str, Any]:
    """Extract conversion configuration from source.

    Args:
        source: Source configuration object or mapping

    Returns:
        Conversion configuration dictionary
    """
    if hasattr(source, "convert"):
        return getattr(source, "convert") or {}
    if isinstance(source, Mapping):
        return source.get("convert", {})
    return {}


def run_ingest(
    sources: Iterable[Any],
    fetched_paths: Mapping[str, Any],
    workdir: Path,
) -> Dict[str, Path]:
    """Run the ingest stage for each fetched source.

    Converts schemas to OWL using the appropriate converter based on the
    schema type specified in the source configuration.

    Args:
        sources: Iterable of source configurations.
        fetched_paths: Mapping of source identifier to fetched schema path(s).
        workdir: Working directory for pipeline artifacts.

    Returns:
        Mapping of source identifier to OWL output path.

    Raises:
        KeyError: If converter type not registered or source not found
        ValueError: If conversion fails
    """
    results: Dict[str, Path] = {}
    converted_root = workdir / "converted"
    converted_root.mkdir(parents=True, exist_ok=True)

    # Log available converters
    available_converters = ConverterRegistry.list_converters()
    logger.info(f"Available converters: {', '.join(available_converters)}")

    for source in sources:
        identifier = _get_identifier(source)
        convert_cfg = _get_convert_config(source)

        # Get converter type (default to 'xsd' for backward compatibility)
        converter_type = convert_cfg.get("type", "xsd")

        # Get converter configuration
        converter_config = convert_cfg.get("config", {})

        # Get input path
        input_path = fetched_paths.get(identifier)
        if input_path is None:
            raise KeyError(f"No fetched artifact found for source '{identifier}'")

        # Setup output paths
        output_dir = converted_root / identifier
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{identifier}.owl"

        # Handle XSD with multiple files (special case for backward compatibility)
        if converter_type == "xsd" and isinstance(input_path, Sequence) and not isinstance(input_path, (str, Path)):
            path_list = [str(Path(p)) for p in input_path]
            print(f"🔧  Ingesting {len(path_list)} XSD files → {output_path}")
            convert_xsd_list_to_owl(path_list, str(output_path))
            results[identifier] = output_path
            continue

        # Get converter instance
        converter = get_converter(converter_type, converter_config)
        if converter is None:
            raise KeyError(
                f"No converter registered for type '{converter_type}'. "
                f"Available types: {', '.join(available_converters)}"
            )

        # Convert schema
        try:
            print(f"🔧  Converting {converter_type.upper()} → {output_path}")
            logger.info(f"Converting {identifier} using {converter.__class__.__name__}")

            converter.convert(str(input_path), str(output_path))
            results[identifier] = output_path

            logger.info(f"Successfully converted {identifier} to {output_path}")

        except Exception as e:
            logger.error(f"Failed to convert {identifier}: {e}")
            raise ValueError(f"Conversion failed for {identifier}: {e}")

    return results
