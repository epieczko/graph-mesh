"""Graph-Mesh core meta-ontology utilities."""

# Backward compatibility exports
from .meta_ontology import (
    GM,
    META_CLASSES,
    META_DATA_PROPERTIES,
    META_OBJECT_PROPERTIES,
    MetaClass,
    MetaProperty,
    add_domain_classes,
    build_meta_graph,
    serialize_meta_graph,
)

# New pluggable architecture exports
from .meta_ontology_base import MetaOntologyInfo, MetaOntologyProvider
from .meta_ontology_registry import MetaOntologyRegistry

__all__ = [
    # Backward compatibility (generic ontology)
    "GM",
    "META_CLASSES",
    "META_DATA_PROPERTIES",
    "META_OBJECT_PROPERTIES",
    "MetaClass",
    "MetaProperty",
    "add_domain_classes",
    "build_meta_graph",
    "serialize_meta_graph",
    # Pluggable architecture
    "MetaOntologyProvider",
    "MetaOntologyInfo",
    "MetaOntologyRegistry",
]
