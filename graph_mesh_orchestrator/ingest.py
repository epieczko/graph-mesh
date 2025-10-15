"""Ingest stage for the Graph Mesh orchestrator."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping

from graph_mesh_ingest.json_to_owl import convert_jsonschema_to_owl
from graph_mesh_ingest.xsd_to_owl import convert_xsd_list_to_owl, convert_xsd_to_owl

ConverterFunc = Callable[[str, str], str]

CONVERTER_REGISTRY: Dict[str, ConverterFunc] = {
    "xsd": convert_xsd_to_owl,
    "json": convert_jsonschema_to_owl,
}


def _get_identifier(source: Any) -> str:
    if hasattr(source, "identifier"):
        return getattr(source, "identifier")
    if isinstance(source, Mapping) and "id" in source:
        return str(source["id"])
    raise KeyError("Source configuration must define an identifier")


def _get_convert_config(source: Any) -> Mapping[str, Any]:
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

    Args:
        sources: Iterable of source configurations.
        fetched_paths: Mapping of source identifier to fetched schema path(s).
        workdir: Working directory for pipeline artifacts.

    Returns:
        Mapping of source identifier to OWL output path.
    """

    results: Dict[str, Path] = {}
    converted_root = workdir / "converted"
    converted_root.mkdir(parents=True, exist_ok=True)

    for source in sources:
        identifier = _get_identifier(source)
        convert_cfg = _get_convert_config(source)
        converter_name = convert_cfg.get("type", "xsd")
        converter = CONVERTER_REGISTRY.get(converter_name)
        if converter is None:
            raise KeyError(f"No ingest converter registered for type '{converter_name}'")

        input_path = fetched_paths.get(identifier)
        if input_path is None:
            raise KeyError(f"No fetched artifact found for source '{identifier}'")

        output_dir = converted_root / identifier
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{identifier}.owl"

        if converter_name == "xsd":
            if isinstance(input_path, Sequence) and not isinstance(input_path, (str, Path)):
                path_list = [str(Path(p)) for p in input_path]
                print(f"🔧  Ingesting {len(path_list)} XSD files → {output_path}")
                convert_xsd_list_to_owl(path_list, str(output_path))
            else:
                print(f"🔧  Ingesting single XSD → {output_path}")
                converter(str(Path(input_path)), str(output_path))
        else:
            converter(str(input_path), str(output_path))
        results[identifier] = output_path

    return results
