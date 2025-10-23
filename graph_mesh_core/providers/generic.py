"""Generic domain-agnostic meta-ontology provider.

This provider implements a simple 7-class ontology suitable for exploratory
integration of schemas where no specific domain ontology is appropriate.
"""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef

from graph_mesh_core.meta_ontology_base import (
    MetaOntologyInfo,
    MetaOntologyProvider,
)

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


# Core classes
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


class GenericMetaOntology(MetaOntologyProvider):
    """Generic 7-class meta-ontology for domain-agnostic integration.

    This provider implements a simple, broadly-applicable ontology with:
    - 7 core classes: Entity, Agent, Contract, Event, Location, Regulation, Metric
    - 8 object properties: participatesIn, hasAgent, hasLocation, etc.
    - 6 datatype properties: hasName, hasDescription, hasIdentifier, etc.

    Suitable for:
    - Exploratory data integration
    - Prototyping before selecting domain ontology
    - Cross-domain projects without specific ontology

    Example:
        >>> provider = GenericMetaOntology()
        >>> graph = provider.build_graph()
        >>> info = provider.get_info()
        >>> print(f"{info.name}: {info.description}")
    """

    def __init__(self):
        """Initialize the generic meta-ontology provider."""
        pass  # No configuration needed for generic ontology

    def get_info(self) -> MetaOntologyInfo:
        """Return metadata about the generic meta-ontology.

        Returns:
            MetaOntologyInfo with name, version, namespace, and description.
        """
        return MetaOntologyInfo(
            name="Generic",
            version="1.0",
            namespace=META_ONTOLOGY_IRI,
            description="Domain-agnostic 7-class ontology for general-purpose schema integration",
            source_url="https://github.com/epieczko/graph-mesh"
        )

    def build_graph(self) -> Graph:
        """Build the RDF graph for the generic meta-ontology.

        Returns:
            rdflib.Graph containing classes, properties, and annotations.
        """
        graph = Graph()
        graph.bind("gm", GM)
        graph.bind("owl", OWL)
        graph.bind("rdfs", RDFS)

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

    def get_alignment_targets(self) -> list[URIRef]:
        """Return list of alignable classes.

        Returns all 7 core classes as alignment targets.

        Returns:
            List of URIRefs for Entity, Agent, Contract, Event, Location, Regulation, Metric.
        """
        return [meta_class.uri() for meta_class in META_CLASSES]

    def get_namespace(self) -> Namespace:
        """Return the Graph-Mesh namespace.

        Returns:
            rdflib.Namespace for https://w3id.org/graph-mesh/meta-ontology#
        """
        return GM

    def get_top_level_classes(self) -> list[URIRef]:
        """Return top-level classes (only Entity has no parent).

        Returns:
            List containing only the Entity class URI.
        """
        return [GM["Entity"]]

    def get_properties(self) -> list[URIRef]:
        """Return all properties defined in the ontology.

        Returns:
            List of URIRefs for both object and datatype properties.
        """
        obj_props = [prop.uri() for prop in META_OBJECT_PROPERTIES]
        data_props = [prop.uri() for prop in META_DATA_PROPERTIES]
        return obj_props + data_props

    def get_description(self, concept_uri: URIRef) -> str | None:
        """Get description for a concept.

        Args:
            concept_uri: URI of the concept

        Returns:
            Description string if concept exists, None otherwise.
        """
        # Check classes
        for meta_class in META_CLASSES:
            if meta_class.uri() == concept_uri:
                return meta_class.comment

        # Check object properties
        for prop in META_OBJECT_PROPERTIES:
            if prop.uri() == concept_uri:
                return prop.comment

        # Check data properties
        for prop in META_DATA_PROPERTIES:
            if prop.uri() == concept_uri:
                return prop.comment

        return None
