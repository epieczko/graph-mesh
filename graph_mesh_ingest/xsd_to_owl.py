"""Namespace-aware XSD → OWL converter with deep traversal and safe IRIs."""
from __future__ import annotations
import os
import re
from typing import Optional
import xmlschema
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, XSD, URIRef

SAFE = re.compile(r"[^A-Za-z0-9._\-]")

def local_name_of(qname: str) -> str:
    """Extract local part from '{ns}Local' or 'Local'."""
    if not qname:
        return "Unnamed"
    if qname.startswith("{") and "}" in qname:
        return qname.split("}", 1)[1] or "Unnamed"
    return qname

def safe_local(local: str) -> str:
    """Make a safe local name for URIs."""
    local = local_name_of(local)
    return SAFE.sub("_", local)

def iri_for(ns_uri: Optional[str], local: str) -> URIRef:
    """Build a URIRef from namespace URI and local name."""
    local = safe_local(local)
    if not ns_uri:
        # fallback to gm default if source ns missing
        ns_uri = "https://graph-mesh.org/schema/"
    # ensure ns ends with slash or hash
    if not ns_uri.endswith(('/', '#')):
        ns_uri = ns_uri.rstrip('/') + '#'
    return URIRef(ns_uri + local)

def xsd_range_for_simple(xsd_simple) -> URIRef:
    """Map xmlschema simple type to XSD range (best-effort)."""
    # Use base_type name if present, fall back to string
    base = getattr(xsd_simple, "base_type", None)
    name = str(getattr(base, "name", None) or getattr(xsd_simple, "name", None) or "string")
    lname = local_name_of(name).lower()
    # coarse mapping
    if any(k in lname for k in ["int", "integer", "long", "short", "byte"]):
        return XSD.integer
    if "decimal" in lname or "float" in lname or "double" in lname or "number" in lname:
        return XSD.decimal
    if "date" in lname and "time" in lname:
        return XSD.dateTime
    if lname == "date":
        return XSD.date
    if "time" in lname:
        return XSD.time
    if "bool" in lname:
        return XSD.boolean
    if "anyuri" in lname or "uri" in lname:
        return XSD.anyURI
    return XSD.string

def add_attribute(g: Graph, owner_class: URIRef, attr_name: str, attr_type) -> None:
    prop = iri_for(getattr(attr_type, "namespace", None), attr_name)
    g.add((prop, RDF.type, OWL.DatatypeProperty))
    g.add((prop, RDFS.domain, owner_class))
    g.add((prop, RDFS.label, Literal(attr_name)))
    # range if simple
    try:
        g.add((prop, RDFS.range, xsd_range_for_simple(attr_type)))
    except Exception:
        g.add((prop, RDFS.range, XSD.string))

def walk_complex_type(g: Graph, ctype, ns: str, class_name: str) -> URIRef:
    """Create/return class for a complexType and walk its content recursively."""
    cls = iri_for(ns, class_name)
    g.add((cls, RDF.type, OWL.Class))
    g.add((cls, RDFS.label, Literal(class_name)))
    # inheritance (extension/restriction)
    base_t = getattr(ctype, "base_type", None)
    if base_t and getattr(base_t, "name", None):
        parent = iri_for(getattr(base_t, "namespace", ns), local_name_of(str(base_t.name)))
        g.add((cls, RDFS.subClassOf, parent))
    # attributes
    for aname, attr in getattr(ctype, "attributes", {}).items():
        atype = getattr(attr, "type", None) or getattr(attr, "simple_type", None) or getattr(attr, "base_type", None)
        add_attribute(g, cls, aname, atype or attr)
    # content particles
    content = getattr(ctype, "content", None)
    if not content:
        return cls
    for particle in getattr(content, "particles", []):
        child_name = getattr(particle, "name", None)
        child_t = getattr(particle, "type", None)
        if not child_name or not child_t:
            continue
        # object property for element
        prop = iri_for(getattr(particle, "namespace", None) or ns, child_name)
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.domain, cls))
        g.add((prop, RDFS.label, Literal(child_name)))
        # range is class for complex, xsd for simple
        if child_t.is_complex():
            child_cls = walk_complex_type(g, child_t, getattr(child_t, "namespace", None) or ns, local_name_of(str(child_t.name or child_name)))
            g.add((prop, RDFS.range, child_cls))
        else:
            g.add((prop, RDFS.range, xsd_range_for_simple(child_t)))
    return cls

def convert_xsd_to_owl(xsd_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Namespace-aware, deep traversal conversion."""
    schema = xmlschema.XMLSchema(xsd_path, base_url=os.path.dirname(xsd_path))
    # dynamic graph + prefix binding for known namespaces
    g = Graph()
    # bind common namespaces from schema.namespaces if available
    ns_items = []
    try:
        ns_items = list(getattr(schema, "namespaces", {}).items())
    except Exception:
        ns_items = []
    for prefix, uri in ns_items:
        if uri:
            try:
                g.bind(prefix or "ns", Namespace(uri))
            except Exception:
                pass

    # default bind (will be used when we build IRIs)
    default_ns = schema.target_namespace or base_uri or "https://graph-mesh.org/schema/"
    g.bind("gm", Namespace(default_ns))
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    # classes from complex types
    for name, ctype in schema.types.items():
        if ctype.is_complex():
            walk_complex_type(g, ctype, getattr(ctype, "namespace", None) or default_ns, local_name_of(str(name)))

    # top-level elements (create properties pointing from their "owner" if needed)
    for name, elem in schema.elements.items():
        etype = getattr(elem, "type", None)
        el_ns = getattr(elem, "namespace", None) or default_ns
        # Top-level element: we still emit a label and, if complex, ensure its class exists.
        if etype and etype.is_complex():
            walk_complex_type(g, etype, getattr(etype, "namespace", None) or el_ns, local_name_of(str(etype.name or name)))
        # Also emit a top-level object property that can be used as entry
        prop = iri_for(el_ns, name)
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.label, Literal(name)))
        if etype:
            if etype.is_complex():
                g.add((prop, RDFS.range, iri_for(getattr(etype, "namespace", None) or el_ns, local_name_of(str(etype.name or name)))))
            else:
                g.add((prop, RDFS.range, xsd_range_for_simple(etype)))

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    g.serialize(destination=output_path, format="xml")

    # write a tiny conversion report
    if out_dir:
        report = os.path.join(out_dir, "conversion_report.txt")
        try:
            cls_count = len(list(g.triples((None, RDF.type, OWL.Class))))
            op_count  = len(list(g.triples((None, RDF.type, OWL.ObjectProperty))))
            dp_count  = len(list(g.triples((None, RDF.type, OWL.DatatypeProperty))))
            with open(report, "w", encoding="utf-8") as f:
                f.write(
                    "Classes: {0}\nObjectProperties: {1}\nDatatypeProperties: {2}\n".format(
                        cls_count,
                        op_count,
                        dp_count,
                    )
                )
        except Exception:
            pass

    return output_path

def convert_xsd_list_to_owl(xsd_paths: list[str], output_path: str, base_uri: Optional[str] = None) -> str:
    """Merge multiple XSDs into one OWL ontology using the recursive converter."""
    from rdflib import Graph
    merged = Graph()
    for xsd_path in xsd_paths:
        temp = Graph()
        tmp_path = output_path + ".tmp.owl"
        convert_xsd_to_owl(xsd_path, tmp_path, base_uri)
        temp.parse(tmp_path)
        merged += temp
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    merged.serialize(destination=output_path, format="xml")
    return output_path
