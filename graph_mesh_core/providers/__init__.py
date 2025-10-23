"""Meta-ontology provider implementations.

This package contains concrete implementations of the MetaOntologyProvider interface
for various domain ontologies.

Available providers:
- GenericMetaOntology: Simple 7-class domain-agnostic ontology
- FIBOMetaOntology: Financial Industry Business Ontology
- CustomMetaOntology: Load ontology from file or URL
- CompositeMetaOntology: Combine multiple ontologies
"""

from graph_mesh_core.providers.generic import GenericMetaOntology
from graph_mesh_core.providers.custom import CustomMetaOntology
from graph_mesh_core.providers.fibo import FIBOMetaOntology
from graph_mesh_core.providers.composite import CompositeMetaOntology

__all__ = [
    "GenericMetaOntology",
    "CustomMetaOntology",
    "FIBOMetaOntology",
    "CompositeMetaOntology",
]
