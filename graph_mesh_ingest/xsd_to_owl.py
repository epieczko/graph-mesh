"""XSD to OWL converter."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional, Sequence

import xmlschema
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal


def convert_xsd_to_owl(xsd_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert an XSD file into an OWL ontology.

    Args:
        xsd_path: Path to the input XSD document.
        output_path: Destination for the serialized OWL document.
        base_uri: Optional base namespace for the generated entities.

    Returns:
        The path to the generated OWL file.
    """

    schema = xmlschema.XMLSchema(xsd_path)
    graph = Graph()
    base = Namespace(base_uri or "https://graph-mesh.org/schema/")

    graph.bind("gm", base)
    graph.bind("rdfs", RDFS)
    graph.bind("owl", OWL)

    for name in schema.types:
        cls = base[name]
        graph.add((cls, RDF.type, OWL.Class))
        graph.add((cls, RDFS.label, Literal(name)))

    for name in schema.elements:
        prop = base[name]
        graph.add((prop, RDF.type, OWL.ObjectProperty))
        graph.add((prop, RDFS.label, Literal(name)))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    graph.serialize(destination=output_path, format="xml")
    return output_path


def convert_xsd_list_to_owl(
    xsd_paths: Sequence[str],
    output_path: str,
    base_uri: Optional[str] = None,
) -> str:
    """Convert and merge multiple XSDs into one OWL ontology.

    Args:
        xsd_paths: Collection of XSD document paths to merge.
        output_path: Destination for the merged OWL ontology.
        base_uri: Optional base namespace for the generated entities.

    Returns:
        The path to the merged OWL file.
    """

    if not xsd_paths:
        raise ValueError("xsd_paths must contain at least one file path")

    # Fast-path for single item to avoid unnecessary work
    if len(xsd_paths) == 1:
        return convert_xsd_to_owl(xsd_paths[0], output_path, base_uri)

    merged_graph = Graph()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        for index, path in enumerate(xsd_paths):
            # Reuse the single-file converter to maintain consistent transformation logic.
            tmp_output = tmpdir_path / f"converted-{index}.owl"
            convert_xsd_to_owl(path, str(tmp_output), base_uri)
            merged_graph.parse(str(tmp_output))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged_graph.serialize(destination=output_path, format="xml")
    return output_path
