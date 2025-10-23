"""Graph-Mesh core meta-ontology utilities."""

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

__all__ = [
    "GM",
    "META_CLASSES",
    "META_DATA_PROPERTIES",
    "META_OBJECT_PROPERTIES",
    "MetaClass",
    "MetaProperty",
    "add_domain_classes",
    "build_meta_graph",
    "serialize_meta_graph",
]
