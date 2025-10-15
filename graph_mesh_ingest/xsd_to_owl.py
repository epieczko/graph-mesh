"""Recursive XSD to OWL converter with deep tree traversal."""
from __future__ import annotations
import os
from typing import Optional
import xmlschema
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal


def sanitize_name(name: str) -> str:
    if not name:
        return "Unnamed"
    if "}" in name and name.startswith("{"):
        name = name.split("}", 1)[1]
    name = name.replace(" ", "_").replace("/", "_").replace(":", "_")
    return name


def _walk_complex_type(g, base, ctype, parent_class=None):
    """Recursively walk an xmlschema.XsdComplexType and add relationships."""
    current_class = base[sanitize_name(str(ctype.name or parent_class or "AnonymousType"))]
    g.add((current_class, RDF.type, OWL.Class))
    g.add((current_class, RDFS.label, Literal(str(ctype.name or parent_class or "AnonymousType"))))

    # Handle inheritance
    if getattr(ctype, "base_type", None) and getattr(ctype.base_type, "name", None):
        parent = base[sanitize_name(str(ctype.base_type.name))]
        g.add((current_class, RDFS.subClassOf, parent))

    # Handle attributes
    for attr_name, attr in ctype.attributes.items():
        prop = base[sanitize_name(attr_name)]
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.domain, current_class))
        g.add((prop, RDFS.label, Literal(attr_name)))

    # Handle child elements / sequences
    content = getattr(ctype, "content", None)
    if not content:
        return
    for particle in getattr(content, "particles", []):
        child = getattr(particle, "name", None)
        if child:
            child_prop = base[sanitize_name(child)]
            g.add((child_prop, RDF.type, OWL.ObjectProperty))
            g.add((child_prop, RDFS.domain, current_class))
            g.add((child_prop, RDFS.label, Literal(child)))
            # recurse into nested complex types
            if particle.type and particle.type.is_complex():
                _walk_complex_type(g, base, particle.type, parent_class=child)


def convert_xsd_to_owl(xsd_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    schema = xmlschema.XMLSchema(xsd_path, base_url=os.path.dirname(xsd_path))
    effective_base_uri = (
        base_uri or schema.target_namespace or "https://graph-mesh.org/schema/"
    )
    g = Graph()
    base = Namespace(effective_base_uri)
    g.bind("gm", base)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    for name, ctype in schema.types.items():
        if ctype.is_complex():
            _walk_complex_type(g, base, ctype)

    for name, elem in schema.elements.items():
        prop = base[sanitize_name(name)]
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.label, Literal(name)))
        if elem.type and elem.type.is_complex():
            _walk_complex_type(g, base, elem.type, parent_class=name)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    g.serialize(destination=output_path, format="xml")
    return output_path
