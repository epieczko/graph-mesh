"""Enhanced XSD to OWL converter with relationship extraction."""
from __future__ import annotations
import os
from typing import Optional
import xmlschema
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef

def convert_xsd_to_owl(xsd_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert an XSD file into a detailed OWL ontology with relationships."""
    schema = xmlschema.XMLSchema(xsd_path, base_url=os.path.dirname(xsd_path))
    g = Graph()
    base = Namespace(base_uri or "https://graph-mesh.org/schema/")
    g.bind("gm", base)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    # ---- Classes for complexTypes ----
    for name, xtype in schema.types.items():
        cls = base[name]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(name)))
        # inheritance
        if getattr(xtype, "base_type", None):
            parent = base[str(xtype.base_type.name)]
            g.add((cls, RDFS.subClassOf, parent))

    # ---- Elements & composition ----
    for name, elem in schema.elements.items():
        elem_res = base[name]
        g.add((elem_res, RDF.type, OWL.ObjectProperty))
        g.add((elem_res, RDFS.label, Literal(name)))

        if elem.type.is_complex():
            domain = base[getattr(elem.parent, "name", name)]
            g.add((elem_res, RDFS.domain, domain))
            # range points to type class
            g.add((elem_res, RDFS.range, base[str(elem.type.name)]))
            # traverse child attributes/elements
            if elem.type.content:
                for child in getattr(elem.type.content, "particles", []):
                    child_name = getattr(child, "name", None)
                    if child_name:
                        child_prop = base[child_name]
                        g.add((child_prop, RDF.type, OWL.ObjectProperty))
                        g.add((child_prop, RDFS.domain, base[str(elem.type.name)]))
                        g.add((child_prop, RDFS.label, Literal(child_name)))

        # handle attributes
        for attr_name, attr in elem.attributes.items():
            prop = base[attr_name]
            g.add((prop, RDF.type, OWL.DatatypeProperty))
            g.add((prop, RDFS.domain, base[str(elem.type.name)]))
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
