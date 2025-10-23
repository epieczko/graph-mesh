"""Core meta-ontology definitions and utilities for Graph-Mesh.

This module declares the abstract classes that act as the shared semantic
backbone across all ingested schemas. It also provides helpers for building
rdflib graphs and persisting them to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef

META_ONTOLOGY_IRI = "https://w3id.org/graph-mesh/meta-ontology"
GM = Namespace(f"{META_ONTOLOGY_IRI}#")


@dataclass(frozen=True)
class MetaClass:
    """Simple representation of a meta-ontology class."""

    name: str
    comment: str
    parent: str | None = None  # For subclass relationships

    def uri(self) -> URIRef:
        return GM[self.name]


@dataclass(frozen=True)
class MetaProperty:
    """Representation of an object or data property in the meta-ontology."""

    name: str
    comment: str
    property_type: str  # "ObjectProperty" or "DatatypeProperty"
    domain: str | list[str] | None = None
    range: str | list[str] | None = None

    def uri(self) -> URIRef:
        return GM[self.name]


META_CLASSES: tuple[MetaClass, ...] = (
    MetaClass("Entity", "Generic thing of interest across domains."),
    MetaClass("Agent", "Person, organization, or system capable of acting.", parent="Entity"),
    MetaClass("Contract", "Formal agreement or policy binding agents.", parent="Entity"),
    MetaClass("Event", "An occurrence situated in time.", parent="Entity"),
    MetaClass("Location", "Geospatial or jurisdictional reference.", parent="Entity"),
    MetaClass("Regulation", "Rule or regulatory instrument.", parent="Entity"),
    MetaClass("Metric", "Quantitative or qualitative measurement.", parent="Entity"),
)


# Object Properties - relationships between entities
META_OBJECT_PROPERTIES: tuple[MetaProperty, ...] = (
    MetaProperty(
        "participatesIn",
        "Relates an agent to an event they participate in.",
        "ObjectProperty",
        domain="Agent",
        range="Event"
    ),
    MetaProperty(
        "hasAgent",
        "Relates an entity to an agent involved with it.",
        "ObjectProperty",
        domain="Entity",
        range="Agent"
    ),
    MetaProperty(
        "hasLocation",
        "Relates an entity to its location.",
        "ObjectProperty",
        domain="Entity",
        range="Location"
    ),
    MetaProperty(
        "occursAt",
        "Relates an event to the location where it occurs.",
        "ObjectProperty",
        domain="Event",
        range="Location"
    ),
    MetaProperty(
        "governedBy",
        "Relates an entity to a regulation that governs it.",
        "ObjectProperty",
        domain="Entity",
        range="Regulation"
    ),
    MetaProperty(
        "subjectTo",
        "Relates an agent to a contract they are subject to.",
        "ObjectProperty",
        domain="Agent",
        range="Contract"
    ),
    MetaProperty(
        "hasMeasurement",
        "Relates an entity to a metric that measures it.",
        "ObjectProperty",
        domain="Entity",
        range="Metric"
    ),
    MetaProperty(
        "relatedTo",
        "Generic relationship between entities.",
        "ObjectProperty",
        domain="Entity",
        range="Entity"
    ),
)


# Data Properties - literal values
META_DATA_PROPERTIES: tuple[MetaProperty, ...] = (
    MetaProperty(
        "hasName",
        "The name of an entity.",
        "DatatypeProperty",
        domain="Entity",
        range=str(RDFS.Literal)
    ),
    MetaProperty(
        "hasDescription",
        "A textual description of an entity.",
        "DatatypeProperty",
        domain="Entity",
        range=str(RDFS.Literal)
    ),
    MetaProperty(
        "hasIdentifier",
        "A unique identifier for an entity.",
        "DatatypeProperty",
        domain="Entity",
        range=str(RDFS.Literal)
    ),
    MetaProperty(
        "hasTimestamp",
        "Temporal information associated with an event.",
        "DatatypeProperty",
        domain="Event",
        range=str(RDFS.Literal)
    ),
    MetaProperty(
        "hasValue",
        "The value of a metric.",
        "DatatypeProperty",
        domain="Metric",
        range=str(RDFS.Literal)
    ),
    MetaProperty(
        "hasUnit",
        "The unit of measurement for a metric.",
        "DatatypeProperty",
        domain="Metric",
        range=str(RDFS.Literal)
    ),
)


def build_meta_graph() -> Graph:
    """Create an rdflib Graph populated with the core meta-ontology classes and properties."""

    graph = Graph()
    graph.bind("gm", GM)
    graph.bind("owl", OWL)

    # Declare as OWL Ontology
    graph.add((URIRef(META_ONTOLOGY_IRI), RDF.type, OWL.Ontology))
    graph.add((URIRef(META_ONTOLOGY_IRI), RDFS.label, Literal("Graph-Mesh Meta-Ontology")))
    graph.add((URIRef(META_ONTOLOGY_IRI), RDFS.comment,
               Literal("Core meta-ontology for federated semantic integration in Graph-Mesh")))

    # Add classes with subclass relationships
    for meta_class in META_CLASSES:
        graph.add((meta_class.uri(), RDF.type, OWL.Class))
        graph.add((meta_class.uri(), RDFS.label, Literal(meta_class.name)))
        graph.add((meta_class.uri(), RDFS.comment, Literal(meta_class.comment)))

        # Add subclass relationship if parent is specified
        if meta_class.parent:
            parent_uri = GM[meta_class.parent]
            graph.add((meta_class.uri(), RDFS.subClassOf, parent_uri))

    # Add object properties
    for prop in META_OBJECT_PROPERTIES:
        graph.add((prop.uri(), RDF.type, OWL.ObjectProperty))
        graph.add((prop.uri(), RDFS.label, Literal(prop.name)))
        graph.add((prop.uri(), RDFS.comment, Literal(prop.comment)))

        # Add domain
        if prop.domain:
            domains = [prop.domain] if isinstance(prop.domain, str) else prop.domain
            for domain in domains:
                graph.add((prop.uri(), RDFS.domain, GM[domain]))

        # Add range
        if prop.range:
            ranges = [prop.range] if isinstance(prop.range, str) else prop.range
            for rng in ranges:
                graph.add((prop.uri(), RDFS.range, GM[rng]))

    # Add data properties
    for prop in META_DATA_PROPERTIES:
        graph.add((prop.uri(), RDF.type, OWL.DatatypeProperty))
        graph.add((prop.uri(), RDFS.label, Literal(prop.name)))
        graph.add((prop.uri(), RDFS.comment, Literal(prop.comment)))

        # Add domain
        if prop.domain:
            domains = [prop.domain] if isinstance(prop.domain, str) else prop.domain
            for domain in domains:
                graph.add((prop.uri(), RDFS.domain, GM[domain]))

        # Add range (for data properties, range is typically XSD datatype)
        if prop.range:
            graph.add((prop.uri(), RDFS.range, URIRef(prop.range)))

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
