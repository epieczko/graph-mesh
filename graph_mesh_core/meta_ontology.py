"""Core meta-ontology definitions and utilities for Graph-Mesh.

This module declares the abstract classes that act as the shared semantic
backbone across all ingested schemas. It also provides helpers for building
rdflib graphs and persisting them to disk.

BACKWARD COMPATIBILITY:
This module maintains the original API for backward compatibility. New code
should use the pluggable provider system via meta_ontology_registry.

Example (old API - still works):
    >>> from graph_mesh_core.meta_ontology import build_meta_graph
    >>> graph = build_meta_graph()

Example (new API - recommended):
    >>> from graph_mesh_core.meta_ontology_registry import MetaOntologyRegistry
    >>> provider = MetaOntologyRegistry.create({"type": "generic"})
    >>> graph = provider.build_graph()
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef

# Re-export from generic provider for backward compatibility
from graph_mesh_core.providers.generic import (
    META_ONTOLOGY_IRI,
    GM,
    MetaClass,
    MetaProperty,
    META_CLASSES,
    META_OBJECT_PROPERTIES,
    META_DATA_PROPERTIES,
)


def build_meta_graph() -> Graph:
    """Create an rdflib Graph populated with the core meta-ontology classes and properties.

    DEPRECATED: Use MetaOntologyRegistry for new code.

    Returns:
        rdflib.Graph containing the generic 7-class ontology.

    Example:
        >>> graph = build_meta_graph()  # Still works for backward compatibility
    """
    from graph_mesh_core.providers.generic import GenericMetaOntology
    provider = GenericMetaOntology()
    return provider.build_graph()


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
