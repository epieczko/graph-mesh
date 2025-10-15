"""Enhanced XSD to OWL converter with dynamic base URI selection."""
from __future__ import annotations
import os
from typing import Optional
import xmlschema
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef


def sanitize_name(name: str) -> str:
    """Normalize XSD QNames or names with namespaces into safe URI suffixes."""
    if not name:
        return "Unnamed"
    if "}" in name and name.startswith("{"):
        name = name.split("}", 1)[1]
    name = name.replace(" ", "_").replace("/", "_").replace(":", "_")
    return name


def convert_xsd_to_owl(xsd_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert an XSD file into a detailed OWL ontology with relationships and namespace preservation."""
    schema = xmlschema.XMLSchema(xsd_path, base_url=os.path.dirname(xsd_path))
    # Dynamically choose base URI: use targetNamespace if available, otherwise fallback
    effective_base_uri = (
        base_uri or schema.target_namespace or "https://graph-mesh.org/schema/"
    )
    g = Graph()
    base = Namespace(effective_base_uri)
    g.bind("gm", base)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    # ---- Classes for complexTypes ----
    for name, xtype in schema.types.items():
        cls = base[sanitize_name(name)]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(name)))
        # inheritance
        if getattr(xtype, "base_type", None):
            parent = base[sanitize_name(str(xtype.base_type.name))]
            g.add((cls, RDFS.subClassOf, parent))

    # ---- Elements & composition ----
    for name, elem in schema.elements.items():
        elem_res = base[sanitize_name(name)]
        g.add((elem_res, RDF.type, OWL.ObjectProperty))
        g.add((elem_res, RDFS.label, Literal(name)))

        if elem.type.is_complex():
            domain = base[sanitize_name(getattr(elem.parent, "name", name))]
            g.add((elem_res, RDFS.domain, domain))
            # range points to type class
            g.add((elem_res, RDFS.range, base[sanitize_name(str(elem.type.name))]))
            # traverse child attributes/elements
            if elem.type.content:
                for child in getattr(elem.type.content, "particles", []):
                    child_name = getattr(child, "name", None)
                    if child_name:
                        child_prop = base[sanitize_name(child_name)]
                        g.add((child_prop, RDF.type, OWL.ObjectProperty))
                        g.add((child_prop, RDFS.domain, base[sanitize_name(str(elem.type.name))]))
                        g.add((child_prop, RDFS.label, Literal(child_name)))

        # handle attributes
        for attr_name, attr in elem.attributes.items():
            prop = base[sanitize_name(attr_name)]
            g.add((prop, RDF.type, OWL.DatatypeProperty))
            g.add((prop, RDFS.domain, base[sanitize_name(str(elem.type.name))]))
            g.add((prop, RDFS.label, Literal(attr_name)))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    g.serialize(destination=output_path, format="xml")
    return output_path

def convert_xsd_list_to_owl(xsd_paths: list[str], output_path: str, base_uri: Optional[str] = None) -> str:
    """Merge multiple XSDs into one OWL ontology with relationships."""
    from rdflib import Graph
    merged = Graph()
    for path in xsd_paths:
        temp = Graph()
        convert_xsd_to_owl(path, output_path + ".tmp.owl", base_uri)
        temp.parse(output_path + ".tmp.owl")
        merged += temp
    merged.serialize(destination=output_path, format="xml")
    return output_path
