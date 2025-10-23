"""XSD to OWL converter with Ontmalizer integration and fallback support.

This module provides XSD to OWL conversion using:
1. Primary: Ontmalizer (containerized Java tool) for standards-compliant conversion
2. Fallback: xmlschema-based conversion with deep traversal and namespace awareness
"""

from __future__ import annotations
import os
import re
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

import xmlschema
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, XSD, URIRef

from .converter_base import SchemaConverter

logger = logging.getLogger(__name__)

SAFE = re.compile(r"[^A-Za-z0-9._\-]")


class XSDConverter(SchemaConverter):
    """XSD to OWL converter with Ontmalizer integration.

    Provides two conversion methods:
    - Ontmalizer: Standards-compliant conversion via Docker container
    - XMLSchema: Python-based conversion with deep traversal (fallback)
    """

    SCHEMA_TYPE = ['xsd', 'xml']

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize XSD converter.

        Args:
            config: Optional configuration:
                - use_ontmalizer (bool): Use Ontmalizer if available (default: True)
                - ontmalizer_image (str): Docker image name (default: 'graph-mesh-ontmalizer')
                - fallback_to_xmlschema (bool): Fall back to xmlschema if Ontmalizer fails (default: True)
        """
        super().__init__(config)
        self.use_ontmalizer = self.config.get('use_ontmalizer', True)
        self.ontmalizer_image = self.config.get('ontmalizer_image', 'graph-mesh-ontmalizer')
        self.fallback_to_xmlschema = self.config.get('fallback_to_xmlschema', True)

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Return supported file extensions."""
        return ['.xsd', '.xml']

    def convert(self, input_path: str, output_path: str) -> str:
        """Convert XSD to OWL.

        Args:
            input_path: Path to XSD file or list of XSD files
            output_path: Path to output OWL file

        Returns:
            Path to generated OWL file

        Raises:
            ValueError: If conversion fails
        """
        # Check if input is a list of files
        if isinstance(input_path, list):
            return self._convert_multiple(input_path, output_path)

        # Try Ontmalizer first if enabled
        if self.use_ontmalizer:
            try:
                return self._convert_with_ontmalizer(input_path, output_path)
            except Exception as e:
                logger.warning(f"Ontmalizer conversion failed: {e}")
                if not self.fallback_to_xmlschema:
                    raise ValueError(f"Ontmalizer conversion failed: {e}")
                logger.info("Falling back to xmlschema-based conversion")

        # Fallback to xmlschema-based conversion
        return self._convert_with_xmlschema(input_path, output_path)

    def _convert_with_ontmalizer(self, input_path: str, output_path: str) -> str:
        """Convert using Ontmalizer Docker container.

        Args:
            input_path: Path to XSD file
            output_path: Path to output OWL file

        Returns:
            Path to generated OWL file

        Raises:
            RuntimeError: If Docker is not available or conversion fails
        """
        # Check if Docker is available
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("Docker is not available. Cannot use Ontmalizer.")

        # Check if Ontmalizer image exists
        result = subprocess.run(
            ['docker', 'images', '-q', self.ontmalizer_image],
            capture_output=True,
            text=True
        )
        if not result.stdout.strip():
            raise RuntimeError(
                f"Ontmalizer Docker image '{self.ontmalizer_image}' not found. "
                f"Build it with: docker build -t {self.ontmalizer_image} -f docker/ontmalizer.Dockerfile ."
            )

        # Prepare paths
        input_file = Path(input_path).resolve()
        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Run Ontmalizer container
        cmd = [
            'docker', 'run', '--rm',
            '-v', f'{input_file.parent}:/input:ro',
            '-v', f'{output_file.parent}:/output',
            self.ontmalizer_image,
            f'/input/{input_file.name}',
            f'/output/{output_file.name}'
        ]

        logger.info(f"Running Ontmalizer: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"Ontmalizer conversion failed:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        if not output_file.exists():
            raise RuntimeError(f"Ontmalizer did not create output file: {output_file}")

        logger.info(f"Ontmalizer conversion successful: {output_file}")

        # Generate conversion report
        self._generate_ontmalizer_report(output_path)

        return str(output_file)

    def _convert_with_xmlschema(self, input_path: str, output_path: str) -> str:
        """Convert using xmlschema library (fallback method).

        Args:
            input_path: Path to XSD file
            output_path: Path to output OWL file

        Returns:
            Path to generated OWL file
        """
        logger.info(f"Converting XSD with xmlschema: {input_path}")

        schema = xmlschema.XMLSchema(input_path, base_url=os.path.dirname(input_path))

        # Create graph with namespaces
        self.create_graph()

        # Bind schema namespaces
        try:
            for prefix, uri in schema.namespaces.items():
                if uri and prefix:
                    self.add_namespace(prefix, uri)
        except Exception as e:
            logger.warning(f"Failed to bind some namespaces: {e}")

        # Use schema target namespace or base_uri
        default_ns = schema.target_namespace or self.base_uri
        if default_ns not in self.namespaces.values():
            self.add_namespace('gm', default_ns)

        # Convert complex types to classes
        for name, ctype in schema.types.items():
            if ctype.is_complex():
                self._walk_complex_type(
                    ctype,
                    getattr(ctype, "namespace", None) or default_ns,
                    self._local_name_of(str(name))
                )

        # Convert top-level elements
        for name, elem in schema.elements.items():
            etype = getattr(elem, "type", None)
            el_ns = getattr(elem, "namespace", None) or default_ns

            if etype and etype.is_complex():
                self._walk_complex_type(
                    etype,
                    getattr(etype, "namespace", None) or el_ns,
                    self._local_name_of(str(etype.name or name))
                )

            # Create top-level object property
            prop_uri = self._iri_for(el_ns, name)
            self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop_uri, RDFS.label, Literal(name)))

            if etype:
                if etype.is_complex():
                    range_uri = self._iri_for(
                        getattr(etype, "namespace", None) or el_ns,
                        self._local_name_of(str(etype.name or name))
                    )
                    self.graph.add((prop_uri, RDFS.range, range_uri))
                else:
                    self.graph.add((prop_uri, RDFS.range, self._xsd_range_for_simple(etype)))

        # Serialize and generate report
        result = self.serialize_graph(output_path)

        # Generate statistics
        stats = {
            'classes': len(list(self.graph.triples((None, RDF.type, OWL.Class)))),
            'object_properties': len(list(self.graph.triples((None, RDF.type, OWL.ObjectProperty)))),
            'datatype_properties': len(list(self.graph.triples((None, RDF.type, OWL.DatatypeProperty)))),
        }
        self.generate_report(output_path, stats)

        return result

    def _convert_multiple(self, input_paths: List[str], output_path: str) -> str:
        """Convert multiple XSD files into one merged OWL ontology.

        Args:
            input_paths: List of XSD file paths
            output_path: Path to output OWL file

        Returns:
            Path to generated OWL file
        """
        logger.info(f"Converting {len(input_paths)} XSD files to OWL")

        merged = Graph()
        merged.bind('rdf', RDF)
        merged.bind('rdfs', RDFS)
        merged.bind('owl', OWL)
        merged.bind('xsd', XSD)

        # Convert each XSD and merge
        for i, xsd_path in enumerate(input_paths):
            logger.info(f"Converting XSD {i+1}/{len(input_paths)}: {xsd_path}")

            # Use temporary file for individual conversion
            with tempfile.NamedTemporaryFile(suffix='.owl', delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Convert individual file
                self.convert(xsd_path, tmp_path)

                # Parse and merge
                temp_graph = Graph()
                temp_graph.parse(tmp_path)
                merged += temp_graph

            finally:
                # Clean up temp file
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        # Serialize merged graph
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        merged.serialize(destination=str(output_file), format='xml')

        logger.info(f"Merged {len(input_paths)} XSD files to {output_path}")
        return str(output_file)

    def _walk_complex_type(self, ctype, ns: str, class_name: str) -> URIRef:
        """Create OWL class for complex type and walk its content recursively.

        Args:
            ctype: xmlschema complex type
            ns: Namespace URI
            class_name: Class name

        Returns:
            URIRef of the created class
        """
        cls_uri = self._iri_for(ns, class_name)
        self.graph.add((cls_uri, RDF.type, OWL.Class))
        self.graph.add((cls_uri, RDFS.label, Literal(class_name)))

        # Handle inheritance (extension/restriction)
        base_t = getattr(ctype, "base_type", None)
        if base_t and getattr(base_t, "name", None):
            parent_uri = self._iri_for(
                getattr(base_t, "namespace", ns),
                self._local_name_of(str(base_t.name))
            )
            self.graph.add((cls_uri, RDFS.subClassOf, parent_uri))

        # Process attributes
        for aname, attr in getattr(ctype, "attributes", {}).items():
            atype = (getattr(attr, "type", None) or
                    getattr(attr, "simple_type", None) or
                    getattr(attr, "base_type", None) or attr)
            self._add_attribute(cls_uri, aname, atype)

        # Process content particles (elements)
        content = getattr(ctype, "content", None)
        if content:
            for particle in getattr(content, "particles", []):
                child_name = getattr(particle, "name", None)
                child_t = getattr(particle, "type", None)
                if not child_name or not child_t:
                    continue

                # Create object property
                prop_uri = self._iri_for(
                    getattr(particle, "namespace", None) or ns,
                    child_name
                )
                self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
                self.graph.add((prop_uri, RDFS.domain, cls_uri))
                self.graph.add((prop_uri, RDFS.label, Literal(child_name)))

                # Set range
                if child_t.is_complex():
                    child_cls_uri = self._walk_complex_type(
                        child_t,
                        getattr(child_t, "namespace", None) or ns,
                        self._local_name_of(str(child_t.name or child_name))
                    )
                    self.graph.add((prop_uri, RDFS.range, child_cls_uri))
                else:
                    self.graph.add((prop_uri, RDFS.range, self._xsd_range_for_simple(child_t)))

        return cls_uri

    def _add_attribute(self, owner_class: URIRef, attr_name: str, attr_type) -> None:
        """Add attribute as datatype property.

        Args:
            owner_class: Owner class URI
            attr_name: Attribute name
            attr_type: Attribute type
        """
        prop_uri = self._iri_for(getattr(attr_type, "namespace", None), attr_name)
        self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.graph.add((prop_uri, RDFS.domain, owner_class))
        self.graph.add((prop_uri, RDFS.label, Literal(attr_name)))

        # Set range
        try:
            range_uri = self._xsd_range_for_simple(attr_type)
            self.graph.add((prop_uri, RDFS.range, range_uri))
        except Exception:
            self.graph.add((prop_uri, RDFS.range, XSD.string))

    def _iri_for(self, ns_uri: Optional[str], local: str) -> URIRef:
        """Build a URIRef from namespace URI and local name.

        Args:
            ns_uri: Namespace URI (optional)
            local: Local name

        Returns:
            URIRef for the resource
        """
        local = self._safe_local(local)
        if not ns_uri:
            ns_uri = self.base_uri

        # Ensure namespace ends with separator
        if not ns_uri.endswith(('/', '#')):
            ns_uri = ns_uri.rstrip('/') + '#'

        return URIRef(ns_uri + local)

    def _local_name_of(self, qname: str) -> str:
        """Extract local part from qualified name.

        Args:
            qname: Qualified name (e.g., '{namespace}LocalName')

        Returns:
            Local name
        """
        if not qname:
            return "Unnamed"
        if qname.startswith("{") and "}" in qname:
            return qname.split("}", 1)[1] or "Unnamed"
        return qname

    def _safe_local(self, local: str) -> str:
        """Make a safe local name for URIs.

        Args:
            local: Local name

        Returns:
            Sanitized local name
        """
        local = self._local_name_of(local)
        return SAFE.sub("_", local)

    def _xsd_range_for_simple(self, xsd_simple) -> URIRef:
        """Map xmlschema simple type to XSD range.

        Args:
            xsd_simple: xmlschema simple type

        Returns:
            XSD type URIRef
        """
        base = getattr(xsd_simple, "base_type", None)
        name = str(getattr(base, "name", None) or
                  getattr(xsd_simple, "name", None) or "string")
        lname = self._local_name_of(name).lower()

        # Map to XSD types
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

    def _generate_ontmalizer_report(self, output_path: str) -> str:
        """Generate conversion report for Ontmalizer output.

        Args:
            output_path: Path to output OWL file

        Returns:
            Path to report file
        """
        # Parse the output to get statistics
        g = Graph()
        g.parse(output_path)

        stats = {
            'classes': len(list(g.triples((None, RDF.type, OWL.Class)))),
            'object_properties': len(list(g.triples((None, RDF.type, OWL.ObjectProperty)))),
            'datatype_properties': len(list(g.triples((None, RDF.type, OWL.DatatypeProperty)))),
        }

        return self.generate_report(output_path, stats)


# Backward compatibility functions for existing code
def convert_xsd_to_owl(xsd_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert XSD to OWL (backward compatibility wrapper).

    Args:
        xsd_path: Path to XSD file
        output_path: Path to output OWL file
        base_uri: Optional base URI for the ontology

    Returns:
        Path to generated OWL file
    """
    config = {}
    if base_uri:
        config['base_uri'] = base_uri

    converter = XSDConverter(config)
    return converter.convert(xsd_path, output_path)


def convert_xsd_list_to_owl(xsd_paths: List[str], output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert multiple XSD files to OWL (backward compatibility wrapper).

    Args:
        xsd_paths: List of XSD file paths
        output_path: Path to output OWL file
        base_uri: Optional base URI for the ontology

    Returns:
        Path to generated OWL file
    """
    config = {}
    if base_uri:
        config['base_uri'] = base_uri

    converter = XSDConverter(config)
    return converter._convert_multiple(xsd_paths, output_path)
