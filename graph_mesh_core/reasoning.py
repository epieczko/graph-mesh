"""Reasoning utilities for Graph-Mesh ontologies.

This module provides utilities for:
- Subsumption checking (is-a relationships)
- Transitive closure computation
- Consistency checking
- Query utilities for navigating class hierarchies
"""

from __future__ import annotations

from typing import Set, List, Tuple, Optional

from rdflib import Graph, URIRef, RDFS, OWL, RDF, Namespace


def get_subclasses(
    graph: Graph,
    class_uri: URIRef,
    direct_only: bool = False
) -> Set[URIRef]:
    """Get all subclasses of a given class.

    Args:
        graph: RDF graph containing the ontology
        class_uri: URI of the class to query
        direct_only: If True, return only direct subclasses

    Returns:
        Set of URIs representing subclasses
    """
    if direct_only:
        # Direct subclasses only
        return {s for s, p, o in graph.triples((None, RDFS.subClassOf, class_uri))}
    else:
        # All subclasses (transitive closure)
        subclasses = set()
        to_process = {class_uri}
        processed = set()

        while to_process:
            current = to_process.pop()
            if current in processed:
                continue

            processed.add(current)
            direct_subs = {s for s, p, o in graph.triples((None, RDFS.subClassOf, current))}

            for sub in direct_subs:
                if sub not in processed:
                    subclasses.add(sub)
                    to_process.add(sub)

        return subclasses


def get_superclasses(
    graph: Graph,
    class_uri: URIRef,
    direct_only: bool = False
) -> Set[URIRef]:
    """Get all superclasses of a given class.

    Args:
        graph: RDF graph containing the ontology
        class_uri: URI of the class to query
        direct_only: If True, return only direct superclasses

    Returns:
        Set of URIs representing superclasses
    """
    if direct_only:
        # Direct superclasses only
        return {o for s, p, o in graph.triples((class_uri, RDFS.subClassOf, None))}
    else:
        # All superclasses (transitive closure)
        superclasses = set()
        to_process = {class_uri}
        processed = set()

        while to_process:
            current = to_process.pop()
            if current in processed:
                continue

            processed.add(current)
            direct_supers = {o for s, p, o in graph.triples((current, RDFS.subClassOf, None))}

            for sup in direct_supers:
                if sup not in processed:
                    superclasses.add(sup)
                    to_process.add(sup)

        return superclasses


def is_subclass_of(
    graph: Graph,
    subclass_uri: URIRef,
    superclass_uri: URIRef,
    strict: bool = False
) -> bool:
    """Check if one class is a subclass of another.

    Args:
        graph: RDF graph containing the ontology
        subclass_uri: URI of the potential subclass
        superclass_uri: URI of the potential superclass
        strict: If True, the classes must be different (strict subsumption)

    Returns:
        True if subclass_uri is a subclass of superclass_uri
    """
    if not strict and subclass_uri == superclass_uri:
        return True

    superclasses = get_superclasses(graph, subclass_uri, direct_only=False)
    return superclass_uri in superclasses


def compute_class_hierarchy(
    graph: Graph,
    root_class: Optional[URIRef] = None
) -> dict[URIRef, Set[URIRef]]:
    """Compute the complete class hierarchy as a tree structure.

    Args:
        graph: RDF graph containing the ontology
        root_class: Optional root class URI. If None, find all root classes.

    Returns:
        Dictionary mapping each class to its direct subclasses
    """
    hierarchy: dict[URIRef, Set[URIRef]] = {}

    # Get all classes
    all_classes = {s for s, p, o in graph.triples((None, RDF.type, OWL.Class))}
    all_classes.update({s for s, p, o in graph.triples((None, RDF.type, RDFS.Class))})

    # Build parent-child relationships
    for cls in all_classes:
        direct_subs = get_subclasses(graph, cls, direct_only=True)
        hierarchy[cls] = direct_subs

    return hierarchy


def get_root_classes(graph: Graph) -> Set[URIRef]:
    """Get all root classes (classes with no superclass).

    Args:
        graph: RDF graph containing the ontology

    Returns:
        Set of root class URIs
    """
    # Get all classes
    all_classes = {s for s, p, o in graph.triples((None, RDF.type, OWL.Class))}
    all_classes.update({s for s, p, o in graph.triples((None, RDF.type, RDFS.Class))})

    # Find classes with no superclass (except owl:Thing and rdfs:Resource)
    root_classes = set()
    for cls in all_classes:
        superclasses = get_superclasses(graph, cls, direct_only=True)

        # Filter out owl:Thing and rdfs:Resource
        superclasses = {
            s for s in superclasses
            if s not in {OWL.Thing, RDFS.Resource}
        }

        if not superclasses:
            root_classes.add(cls)

    return root_classes


def get_leaf_classes(graph: Graph) -> Set[URIRef]:
    """Get all leaf classes (classes with no subclasses).

    Args:
        graph: RDF graph containing the ontology

    Returns:
        Set of leaf class URIs
    """
    # Get all classes
    all_classes = {s for s, p, o in graph.triples((None, RDF.type, OWL.Class))}
    all_classes.update({s for s, p, o in graph.triples((None, RDF.type, RDFS.Class))})

    # Find classes with no subclasses
    leaf_classes = set()
    for cls in all_classes:
        subclasses = get_subclasses(graph, cls, direct_only=True)
        if not subclasses:
            leaf_classes.add(cls)

    return leaf_classes


def compute_transitive_closure(
    graph: Graph,
    property_uri: URIRef
) -> Set[Tuple[URIRef, URIRef]]:
    """Compute the transitive closure for a property.

    Args:
        graph: RDF graph containing the ontology
        property_uri: URI of the property (e.g., rdfs:subClassOf)

    Returns:
        Set of tuples representing the transitive closure
    """
    closure = set()

    # Get all direct relationships
    direct_rels = {(s, o) for s, p, o in graph.triples((None, property_uri, None))}

    # Compute transitive closure using Warshall's algorithm
    changed = True
    closure = direct_rels.copy()

    while changed:
        changed = False
        new_rels = set()

        for (a, b) in closure:
            for (c, d) in closure:
                if b == c and (a, d) not in closure:
                    new_rels.add((a, d))
                    changed = True

        closure.update(new_rels)

    return closure


def find_common_ancestors(
    graph: Graph,
    class_uri_1: URIRef,
    class_uri_2: URIRef
) -> Set[URIRef]:
    """Find common ancestor classes of two classes.

    Args:
        graph: RDF graph containing the ontology
        class_uri_1: First class URI
        class_uri_2: Second class URI

    Returns:
        Set of common ancestor class URIs
    """
    ancestors_1 = get_superclasses(graph, class_uri_1, direct_only=False)
    ancestors_2 = get_superclasses(graph, class_uri_2, direct_only=False)

    return ancestors_1.intersection(ancestors_2)


def find_lowest_common_ancestor(
    graph: Graph,
    class_uri_1: URIRef,
    class_uri_2: URIRef
) -> Optional[URIRef]:
    """Find the lowest (most specific) common ancestor of two classes.

    Args:
        graph: RDF graph containing the ontology
        class_uri_1: First class URI
        class_uri_2: Second class URI

    Returns:
        URI of the lowest common ancestor, or None if no common ancestor exists
    """
    common_ancestors = find_common_ancestors(graph, class_uri_1, class_uri_2)

    if not common_ancestors:
        return None

    # Find the most specific (lowest) common ancestor
    # An ancestor is lowest if it has no subclasses among the common ancestors
    for ancestor in common_ancestors:
        ancestor_subs = get_subclasses(graph, ancestor, direct_only=False)
        # Check if any other common ancestor is a subclass of this one
        is_lowest = not any(
            other in ancestor_subs
            for other in common_ancestors
            if other != ancestor
        )

        if is_lowest:
            return ancestor

    # Fallback: return any common ancestor
    return next(iter(common_ancestors))


def get_property_domain(
    graph: Graph,
    property_uri: URIRef
) -> Set[URIRef]:
    """Get the domain classes for a property.

    Args:
        graph: RDF graph containing the ontology
        property_uri: URI of the property

    Returns:
        Set of domain class URIs
    """
    return {o for s, p, o in graph.triples((property_uri, RDFS.domain, None))}


def get_property_range(
    graph: Graph,
    property_uri: URIRef
) -> Set[URIRef]:
    """Get the range classes/datatypes for a property.

    Args:
        graph: RDF graph containing the ontology
        property_uri: URI of the property

    Returns:
        Set of range class/datatype URIs
    """
    return {o for s, p, o in graph.triples((property_uri, RDFS.range, None))}


def get_applicable_properties(
    graph: Graph,
    class_uri: URIRef,
    include_inherited: bool = True
) -> dict[str, Set[URIRef]]:
    """Get all properties applicable to a class.

    Args:
        graph: RDF graph containing the ontology
        class_uri: URI of the class
        include_inherited: If True, include properties from superclasses

    Returns:
        Dictionary with 'object' and 'datatype' keys mapping to sets of property URIs
    """
    applicable = {"object": set(), "datatype": set()}

    # Get classes to check (current class + ancestors if including inherited)
    classes_to_check = {class_uri}
    if include_inherited:
        classes_to_check.update(get_superclasses(graph, class_uri, direct_only=False))

    # Find all properties with matching domain
    all_properties = {s for s, p, o in graph.triples((None, RDF.type, OWL.ObjectProperty))}
    all_properties.update({s for s, p, o in graph.triples((None, RDF.type, OWL.DatatypeProperty))})

    for prop in all_properties:
        domains = get_property_domain(graph, prop)

        # Check if any of the domains match our classes
        if any(domain in classes_to_check for domain in domains):
            # Determine if it's an object or datatype property
            if (prop, RDF.type, OWL.ObjectProperty) in graph:
                applicable["object"].add(prop)
            elif (prop, RDF.type, OWL.DatatypeProperty) in graph:
                applicable["datatype"].add(prop)

    return applicable


def print_class_hierarchy(
    graph: Graph,
    root_uri: Optional[URIRef] = None,
    indent: int = 0,
    namespace: Optional[Namespace] = None
) -> str:
    """Generate a text representation of the class hierarchy.

    Args:
        graph: RDF graph containing the ontology
        root_uri: Root class URI to start from (None for all roots)
        indent: Current indentation level
        namespace: Optional namespace for abbreviating URIs

    Returns:
        String representation of the hierarchy
    """
    lines = []

    if root_uri is None:
        # Print all root classes
        roots = get_root_classes(graph)
        for root in sorted(roots, key=str):
            lines.extend(print_class_hierarchy(graph, root, indent, namespace).split('\n'))
    else:
        # Get label or use local name
        label = None
        for s, p, o in graph.triples((root_uri, RDFS.label, None)):
            label = str(o)
            break

        if not label:
            if namespace and str(root_uri).startswith(str(namespace)):
                label = str(root_uri).replace(str(namespace), '')
            else:
                label = str(root_uri).split('#')[-1].split('/')[-1]

        lines.append('  ' * indent + f'- {label}')

        # Recursively print subclasses
        subclasses = get_subclasses(graph, root_uri, direct_only=True)
        for sub in sorted(subclasses, key=str):
            lines.extend(print_class_hierarchy(graph, sub, indent + 1, namespace).split('\n'))

    return '\n'.join(lines)
