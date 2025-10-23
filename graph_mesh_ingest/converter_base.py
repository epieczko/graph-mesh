"""
Abstract base class for schema-to-OWL converters with plugin architecture.

This module provides a plugin system for registering and using different
schema converters (XSD, JSON Schema, CSV, etc.) with shared utilities
for namespace handling, URI generation, and OWL graph serialization.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, List, Any, Type
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
import logging

logger = logging.getLogger(__name__)


class ConverterRegistry:
    """Registry for converter plugins."""

    _converters: Dict[str, Type['SchemaConverter']] = {}

    @classmethod
    def register(cls, schema_type: str, converter_class: Type['SchemaConverter']) -> None:
        """Register a converter for a specific schema type.

        Args:
            schema_type: The schema type identifier (e.g., 'xsd', 'json', 'csv')
            converter_class: The converter class to register
        """
        cls._converters[schema_type.lower()] = converter_class
        logger.info(f"Registered converter for schema type: {schema_type}")

    @classmethod
    def get_converter(cls, schema_type: str) -> Optional[Type['SchemaConverter']]:
        """Get a converter class for a specific schema type.

        Args:
            schema_type: The schema type identifier

        Returns:
            The converter class or None if not found
        """
        return cls._converters.get(schema_type.lower())

    @classmethod
    def list_converters(cls) -> List[str]:
        """List all registered converter types.

        Returns:
            List of registered schema types
        """
        return list(cls._converters.keys())


class SchemaConverter(ABC):
    """Abstract base class for schema-to-OWL converters.

    Subclasses must implement:
    - convert(): Main conversion logic
    - supported_extensions(): File extensions this converter handles

    Provides shared utilities for:
    - Namespace management
    - URI generation
    - OWL graph creation and serialization
    - Configuration management
    """

    # Default namespaces used across converters
    DEFAULT_BASE_URI = "https://graph-mesh.org/schema/"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize converter with optional configuration.

        Args:
            config: Optional configuration dictionary with converter-specific settings
        """
        self.config = config or {}
        self.base_uri = self.config.get('base_uri', self.DEFAULT_BASE_URI)
        self.graph: Optional[Graph] = None
        self.namespaces: Dict[str, Namespace] = {}

    def __init_subclass__(cls, **kwargs):
        """Automatically register converter subclasses."""
        super().__init_subclass__(**kwargs)
        # Auto-register converters when they're defined
        if not hasattr(cls, '_abstract'):
            schema_types = getattr(cls, 'SCHEMA_TYPE', None)
            if schema_types:
                if isinstance(schema_types, str):
                    schema_types = [schema_types]
                for schema_type in schema_types:
                    ConverterRegistry.register(schema_type, cls)

    @abstractmethod
    def convert(self, input_path: str, output_path: str) -> str:
        """Convert schema to OWL format.

        Args:
            input_path: Path to input schema file
            output_path: Path to output OWL file

        Returns:
            Path to the generated OWL file

        Raises:
            ValueError: If input file is invalid or conversion fails
        """
        pass

    @classmethod
    @abstractmethod
    def supported_extensions(cls) -> List[str]:
        """Return list of supported file extensions (e.g., ['.xsd', '.xml']).

        Returns:
            List of file extensions this converter can handle
        """
        pass

    def create_graph(self, base_namespace: Optional[str] = None) -> Graph:
        """Create an RDF graph with standard OWL namespaces.

        Args:
            base_namespace: Optional base namespace URI (defaults to base_uri)

        Returns:
            Initialized RDF Graph with namespace bindings
        """
        self.graph = Graph()

        # Bind standard namespaces
        self.graph.bind('rdf', RDF)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('owl', OWL)
        self.graph.bind('xsd', XSD)

        # Bind base namespace
        base_ns = base_namespace or self.base_uri
        self.namespaces['base'] = Namespace(base_ns)
        self.graph.bind('', self.namespaces['base'])

        # Add OWL Ontology declaration
        ontology_uri = URIRef(base_ns.rstrip('/'))
        self.graph.add((ontology_uri, RDF.type, OWL.Ontology))

        return self.graph

    def add_namespace(self, prefix: str, uri: str) -> Namespace:
        """Add and bind a namespace to the graph.

        Args:
            prefix: Namespace prefix
            uri: Namespace URI

        Returns:
            The created Namespace object
        """
        if not self.graph:
            raise ValueError("Graph not initialized. Call create_graph() first.")

        ns = Namespace(uri)
        self.namespaces[prefix] = ns
        self.graph.bind(prefix, ns)
        return ns

    def create_iri(self, local_name: str, namespace: Optional[str] = None) -> URIRef:
        """Create a safe IRI for a resource.

        Args:
            local_name: Local name for the resource
            namespace: Namespace key (defaults to 'base')

        Returns:
            URIRef for the resource
        """
        # Sanitize local name
        safe_name = self._sanitize_name(local_name)

        # Get namespace
        ns_key = namespace or 'base'
        ns = self.namespaces.get(ns_key, self.namespaces['base'])

        return URIRef(ns + safe_name)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in URIs.

        Args:
            name: Name to sanitize

        Returns:
            Sanitized name safe for URIs
        """
        # Remove namespace prefixes
        if '{' in name and '}' in name:
            name = name.split('}')[1]
        if ':' in name:
            name = name.split(':')[-1]

        # Replace unsafe characters
        unsafe_chars = {' ': '_', '-': '_', '.': '_', '/': '_',
                       '\\': '_', '(': '_', ')': '_', '[': '_', ']': '_',
                       '{': '_', '}': '_', '<': '_', '>': '_', '&': '_',
                       '@': '_', '#': '_', '%': '_', '?': '_', '=': '_'}

        for char, replacement in unsafe_chars.items():
            name = name.replace(char, replacement)

        # Ensure it doesn't start with a number
        if name and name[0].isdigit():
            name = 'n' + name

        return name

    def serialize_graph(self, output_path: str, format: str = 'xml') -> str:
        """Serialize the OWL graph to a file.

        Args:
            output_path: Path to output file
            format: RDF serialization format (xml, turtle, n3, etc.)

        Returns:
            Path to the serialized file
        """
        if not self.graph:
            raise ValueError("No graph to serialize. Call create_graph() first.")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        self.graph.serialize(destination=str(output_file), format=format)
        logger.info(f"Serialized OWL graph to {output_file}")

        return str(output_file)

    def add_class(self, class_name: str, label: Optional[str] = None,
                  comment: Optional[str] = None, namespace: Optional[str] = None) -> URIRef:
        """Add an OWL Class to the graph.

        Args:
            class_name: Name of the class
            label: Optional rdfs:label
            comment: Optional rdfs:comment
            namespace: Optional namespace key

        Returns:
            URIRef of the created class
        """
        if not self.graph:
            raise ValueError("Graph not initialized. Call create_graph() first.")

        class_uri = self.create_iri(class_name, namespace)
        self.graph.add((class_uri, RDF.type, OWL.Class))

        if label:
            self.graph.add((class_uri, RDFS.label, Literal(label)))
        if comment:
            self.graph.add((class_uri, RDFS.comment, Literal(comment)))

        return class_uri

    def add_property(self, property_name: str, property_type: URIRef,
                    domain: Optional[URIRef] = None, range_: Optional[URIRef] = None,
                    label: Optional[str] = None, namespace: Optional[str] = None) -> URIRef:
        """Add a property (Object or Datatype) to the graph.

        Args:
            property_name: Name of the property
            property_type: OWL.ObjectProperty or OWL.DatatypeProperty
            domain: Optional domain class
            range_: Optional range (class or datatype)
            label: Optional rdfs:label
            namespace: Optional namespace key

        Returns:
            URIRef of the created property
        """
        if not self.graph:
            raise ValueError("Graph not initialized. Call create_graph() first.")

        prop_uri = self.create_iri(property_name, namespace)
        self.graph.add((prop_uri, RDF.type, property_type))

        if domain:
            self.graph.add((prop_uri, RDFS.domain, domain))
        if range_:
            self.graph.add((prop_uri, RDFS.range, range_))
        if label:
            self.graph.add((prop_uri, RDFS.label, Literal(label)))

        return prop_uri

    def map_datatype_to_xsd(self, datatype: str) -> URIRef:
        """Map a schema datatype to XSD type.

        Args:
            datatype: Datatype string (e.g., 'string', 'integer', 'boolean')

        Returns:
            XSD type URIRef
        """
        type_mapping = {
            'string': XSD.string,
            'integer': XSD.integer,
            'int': XSD.int,
            'long': XSD.long,
            'short': XSD.short,
            'byte': XSD.byte,
            'decimal': XSD.decimal,
            'float': XSD.float,
            'double': XSD.double,
            'boolean': XSD.boolean,
            'date': XSD.date,
            'time': XSD.time,
            'datetime': XSD.dateTime,
            'duration': XSD.duration,
            'anyuri': XSD.anyURI,
            'uri': XSD.anyURI,
        }

        return type_mapping.get(datatype.lower(), XSD.string)

    def generate_report(self, output_path: str, stats: Dict[str, int]) -> str:
        """Generate a conversion report file.

        Args:
            output_path: Path to output OWL file
            stats: Dictionary of statistics (e.g., {'classes': 10, 'properties': 25})

        Returns:
            Path to the report file
        """
        report_path = Path(output_path).parent / 'conversion_report.txt'

        with open(report_path, 'w') as f:
            f.write(f"Schema Conversion Report\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Output File: {output_path}\n")
            f.write(f"Converter: {self.__class__.__name__}\n\n")
            f.write(f"Statistics:\n")
            for key, value in stats.items():
                f.write(f"  {key.replace('_', ' ').title()}: {value}\n")

        logger.info(f"Generated conversion report at {report_path}")
        return str(report_path)


def get_converter(schema_type: str, config: Optional[Dict[str, Any]] = None) -> Optional[SchemaConverter]:
    """Factory function to get a converter instance for a schema type.

    Args:
        schema_type: The schema type identifier (e.g., 'xsd', 'json', 'csv')
        config: Optional configuration for the converter

    Returns:
        Initialized converter instance or None if type not found
    """
    converter_class = ConverterRegistry.get_converter(schema_type)
    if converter_class:
        return converter_class(config)
    return None
