"""Ingest stage for the Graph Mesh orchestrator."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping

import structlog

from graph_mesh_ingest.json_to_owl import convert_jsonschema_to_owl
from graph_mesh_ingest.xsd_to_owl import convert_xsd_list_to_owl, convert_xsd_to_owl
from graph_mesh_orchestrator.errors import ConverterNotAvailableError, IngestError

logger = structlog.get_logger(__name__)

ConverterFunc = Callable[[str, str], str]

CONVERTER_REGISTRY: Dict[str, ConverterFunc] = {
    "xsd": convert_xsd_to_owl,
    "json": convert_jsonschema_to_owl,
}


def _get_identifier(source: Any) -> str:
    """Extract identifier from source configuration.

    Args:
        source: Source configuration object

    Returns:
        Source identifier

    Raises:
        IngestError: If identifier cannot be extracted
    """
    if hasattr(source, "id"):
        return getattr(source, "id")
    if hasattr(source, "identifier"):
        return getattr(source, "identifier")
    if isinstance(source, Mapping) and "id" in source:
        return str(source["id"])
    raise IngestError(
        "Source configuration must define an identifier",
        source_id="unknown"
    )


def _get_convert_config(source: Any) -> Mapping[str, Any]:
    """Extract convert configuration from source.

    Args:
        source: Source configuration object

    Returns:
        Convert configuration dictionary
    """
    if hasattr(source, "convert"):
        convert_obj = getattr(source, "convert")
        # Handle pydantic models
        if hasattr(convert_obj, "model_dump"):
            return convert_obj.model_dump()
        elif hasattr(convert_obj, "dict"):
            return convert_obj.dict()
        return convert_obj or {}
    if isinstance(source, Mapping):
        return source.get("convert", {})
    return {}


def run_ingest(
    sources: Iterable[Any],
    fetched_paths: Mapping[str, Any],
    workdir: Path,
) -> Dict[str, Path]:
    """Run the ingest stage for each fetched source.

    Args:
        sources: Iterable of source configurations.
        fetched_paths: Mapping of source identifier to fetched schema path(s).
        workdir: Working directory for pipeline artifacts.

    Returns:
        Mapping of source identifier to OWL output path.

    Raises:
        IngestError: If ingestion fails for any source
        ConverterNotAvailableError: If converter is not registered
    """
    results: Dict[str, Path] = {}
    converted_root = workdir / "converted"
    converted_root.mkdir(parents=True, exist_ok=True)

    logger.info("ingest_starting", source_count=len(list(sources)))

    for source in sources:
        identifier = None
        try:
            identifier = _get_identifier(source)
            log = logger.bind(source_id=identifier)

            convert_cfg = _get_convert_config(source)
            converter_name = convert_cfg.get("type", "xsd")

            log.debug("ingest_config", converter_type=converter_name, config=convert_cfg)

            converter = CONVERTER_REGISTRY.get(converter_name)
            if converter is None:
                raise ConverterNotAvailableError(converter_name)

            input_path = fetched_paths.get(identifier)
            if input_path is None:
                raise IngestError(
                    f"No fetched artifact found for source",
                    source_id=identifier,
                    converter_type=converter_name
                )

            output_dir = converted_root / identifier
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{identifier}.owl"

            # Handle different converter types
            if converter_name == "xsd":
                if isinstance(input_path, Sequence) and not isinstance(input_path, (str, Path)):
                    # Multiple XSD files
                    path_list = [str(Path(p)) for p in input_path]
                    log.info("ingesting_multiple_xsd", count=len(path_list), output=str(output_path))
                    try:
                        convert_xsd_list_to_owl(path_list, str(output_path))
                    except Exception as e:
                        raise IngestError(
                            f"Failed to convert multiple XSD files: {str(e)}",
                            source_id=identifier,
                            converter_type=converter_name,
                            input_path=str(path_list)
                        ) from e
                else:
                    # Single XSD file
                    log.info("ingesting_single_xsd", input=str(input_path), output=str(output_path))
                    try:
                        converter(str(Path(input_path)), str(output_path))
                    except Exception as e:
                        raise IngestError(
                            f"Failed to convert XSD file: {str(e)}",
                            source_id=identifier,
                            converter_type=converter_name,
                            input_path=str(input_path)
                        ) from e
            else:
                # Generic converter
                log.info("ingesting_schema", converter=converter_name, input=str(input_path), output=str(output_path))
                try:
                    converter(str(input_path), str(output_path))
                except Exception as e:
                    raise IngestError(
                        f"Conversion failed: {str(e)}",
                        source_id=identifier,
                        converter_type=converter_name,
                        input_path=str(input_path)
                    ) from e

            # Verify output was created
            if not output_path.exists():
                raise IngestError(
                    "Converter succeeded but output file not found",
                    source_id=identifier,
                    converter_type=converter_name,
                    input_path=str(input_path)
                )

            results[identifier] = output_path
            log.info("ingest_complete", output=str(output_path))

        except (IngestError, ConverterNotAvailableError):
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            raise IngestError(
                f"Unexpected error during ingestion: {str(e)}",
                source_id=identifier or "unknown",
                converter_type=convert_cfg.get("type", "unknown") if 'convert_cfg' in locals() else "unknown"
            ) from e

    logger.info("ingest_complete", converted_count=len(results))
    return results
