"""JSON Schema to OWL converter."""

from __future__ import annotations

import json
import os
from typing import Optional

from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal


def convert_jsonschema_to_owl(json_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert a JSON Schema document into an OWL ontology."""

    with open(json_path, "r", encoding="utf-8") as handle:
        schema = json.load(handle)

    graph = Graph()
    base = Namespace(base_uri or "https://graph-mesh.org/schema/")

    graph.bind("gm", base)
    graph.bind("rdfs", RDFS)
    graph.bind("owl", OWL)

    for name in schema.get("properties", {}):
        node = base[name]
        graph.add((node, RDF.type, OWL.ObjectProperty))
        graph.add((node, RDFS.label, Literal(name)))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    graph.serialize(destination=output_path, format="xml")
    return output_path
