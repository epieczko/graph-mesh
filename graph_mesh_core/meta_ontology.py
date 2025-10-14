"""Core meta-ontology definitions and utilities for Graph-Mesh.

This module declares the abstract classes that act as the shared semantic
backbone across all ingested schemas. It also provides helpers for building
rdflib graphs and persisting them to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

META_ONTOLOGY_IRI = "https://w3id.org/graph-mesh/meta-ontology"
GM = Namespace(f"{META_ONTOLOGY_IRI}#")


@dataclass(frozen=True)
class MetaClass:
    """Simple representation of a meta-ontology class."""

    name: str
    comment: str

    def uri(self) -> URIRef:
        return GM[self.name]


META_CLASSES: tuple[MetaClass, ...] = (
    MetaClass("Entity", "Generic thing of interest across domains."),
    MetaClass("Agent", "Person, organization, or system capable of acting."),
    MetaClass("Contract", "Formal agreement or policy binding agents."),
    MetaClass("Event", "An occurrence situated in time."),
    MetaClass("Location", "Geospatial or jurisdictional reference."),
    MetaClass("Regulation", "Rule or regulatory instrument."),
    MetaClass("Metric", "Quantitative or qualitative measurement."),
)


def build_meta_graph() -> Graph:
    """Create an rdflib Graph populated with the core meta-ontology classes."""

    graph = Graph()
    graph.bind("gm", GM)

    for meta_class in META_CLASSES:
        graph.add((meta_class.uri(), RDF.type, RDFS.Class))
        graph.add((meta_class.uri(), RDFS.label, Literal(meta_class.name)))
        graph.add((meta_class.uri(), RDFS.comment, Literal(meta_class.comment)))

    return graph


def serialize_meta_graph(output_path: Path, format: str = "turtle") -> Path:
    """Serialize the core meta-ontology to ``output_path``."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph = build_meta_graph()
    graph.serialize(destination=str(output_path), format=format)
    return output_path


def add_domain_classes(graph: Graph, class_iris: Iterable[str]) -> Graph:
    """Attach domain-specific classes as subclasses of ``gm:Entity``."""

    entity = GM["Entity"]
    for class_iri in class_iris:
        uri = URIRef(class_iri)
        graph.add((uri, RDF.type, RDFS.Class))
        graph.add((uri, RDFS.subClassOf, entity))

    return graph
