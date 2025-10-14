"""XSD to OWL converter."""

from __future__ import annotations

import os
from typing import Optional

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
