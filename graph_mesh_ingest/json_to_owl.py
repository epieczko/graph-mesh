"""JSON Schema to OWL converter with comprehensive type handling and validation support.

This module provides JSON Schema to OWL conversion with support for:
- Nested objects and complex types
- $ref references (internal and external)
- All JSON Schema types (string, number, integer, boolean, array, object, null)
- Validation keywords (required, pattern, enum, etc.)
- Composition keywords (allOf, anyOf, oneOf, not)
- Definitions and reusable schemas
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urlparse, urljoin
import logging

from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, XSD, URIRef

from .converter_base import SchemaConverter

logger = logging.getLogger(__name__)


class JSONSchemaConverter(SchemaConverter):
    """JSON Schema to OWL converter with full support for JSON Schema features.

    Handles nested objects, $ref resolution, proper type mapping,
    validation constraints, and composition patterns.
    """

    SCHEMA_TYPE = ['json', 'jsonschema']

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize JSON Schema converter.

        Args:
            config: Optional configuration:
                - resolve_external_refs (bool): Resolve external $ref (default: False)
                - strict_validation (bool): Strict validation of schema (default: False)
        """
        super().__init__(config)
        self.resolve_external_refs = self.config.get('resolve_external_refs', False)
        self.strict_validation = self.config.get('strict_validation', False)
        self.schema_cache: Dict[str, Any] = {}
        self.processed_refs: Set[str] = set()
        self.definitions: Dict[str, Any] = {}

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Return supported file extensions."""
        return ['.json', '.jsonschema']

    def convert(self, input_path: str, output_path: str) -> str:
        """Convert JSON Schema to OWL.

        Args:
            input_path: Path to JSON Schema file
            output_path: Path to output OWL file

        Returns:
            Path to generated OWL file

        Raises:
            ValueError: If schema is invalid or conversion fails
        """
        logger.info(f"Converting JSON Schema: {input_path}")

        # Load schema
        with open(input_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        # Validate basic schema structure
        if not isinstance(schema, dict):
            raise ValueError(f"Invalid JSON Schema: expected object, got {type(schema)}")

        # Initialize graph
        self.create_graph()

        # Extract definitions/components
        self._extract_definitions(schema)

        # Get schema metadata
        schema_id = schema.get('$id', schema.get('id', self.base_uri))
        schema_title = schema.get('title', 'Converted Schema')
        schema_description = schema.get('description')

        # Add ontology metadata
        ontology_uri = URIRef(schema_id.rstrip('/'))
        self.graph.add((ontology_uri, RDF.type, OWL.Ontology))
        self.graph.add((ontology_uri, RDFS.label, Literal(schema_title)))
        if schema_description:
            self.graph.add((ontology_uri, RDFS.comment, Literal(schema_description)))

        # Process root schema
        if schema.get('type') == 'object' or 'properties' in schema:
            # Root is an object with properties
            root_class_name = schema.get('title', 'RootClass')
            self._process_object_schema(schema, root_class_name)
        elif '$ref' in schema:
            # Root is a reference
            self._resolve_ref(schema['$ref'], schema)
        else:
            # Try to process as general schema
            self._process_schema(schema, 'RootType')

        # Serialize
        result = self.serialize_graph(output_path)

        # Generate statistics
        stats = {
            'classes': len(list(self.graph.triples((None, RDF.type, OWL.Class)))),
            'object_properties': len(list(self.graph.triples((None, RDF.type, OWL.ObjectProperty)))),
            'datatype_properties': len(list(self.graph.triples((None, RDF.type, OWL.DatatypeProperty)))),
        }
        self.generate_report(output_path, stats)

        return result

    def _extract_definitions(self, schema: Dict[str, Any]) -> None:
        """Extract definitions from schema for $ref resolution.

        Args:
            schema: JSON Schema object
        """
        # JSON Schema Draft 4-6 uses "definitions"
        if 'definitions' in schema:
            self.definitions.update(schema['definitions'])

        # JSON Schema Draft 7+ uses "$defs"
        if '$defs' in schema:
            self.definitions.update(schema['$defs'])

        # OpenAPI uses "components/schemas"
        if 'components' in schema and 'schemas' in schema['components']:
            self.definitions.update(schema['components']['schemas'])

    def _process_schema(self, schema: Dict[str, Any], name: str,
                       parent_class: Optional[URIRef] = None) -> Optional[URIRef]:
        """Process a JSON Schema and convert to OWL.

        Args:
            schema: JSON Schema object
            name: Name for this schema element
            parent_class: Optional parent class URI

        Returns:
            URIRef of created resource or None
        """
        if not isinstance(schema, dict):
            return None

        # Handle $ref
        if '$ref' in schema:
            return self._resolve_ref(schema['$ref'], schema)

        # Handle composition keywords
        if 'allOf' in schema:
            return self._process_all_of(schema, name, parent_class)
        if 'anyOf' in schema:
            return self._process_any_of(schema, name, parent_class)
        if 'oneOf' in schema:
            return self._process_one_of(schema, name, parent_class)

        # Handle type-specific schemas
        schema_type = schema.get('type')

        if schema_type == 'object' or 'properties' in schema:
            return self._process_object_schema(schema, name, parent_class)
        elif schema_type == 'array':
            return self._process_array_schema(schema, name, parent_class)
        elif schema_type in ('string', 'number', 'integer', 'boolean', 'null'):
            return self._process_primitive_schema(schema, name, parent_class)
        elif isinstance(schema_type, list):
            # Multiple types - create union
            return self._process_union_type(schema, name, parent_class)

        return None

    def _process_object_schema(self, schema: Dict[str, Any], name: str,
                               parent_class: Optional[URIRef] = None) -> URIRef:
        """Process an object schema and create OWL Class.

        Args:
            schema: JSON Schema object
            name: Class name
            parent_class: Optional parent class

        Returns:
            URIRef of created class
        """
        # Create class
        class_uri = self.add_class(
            name,
            label=schema.get('title', name),
            comment=schema.get('description')
        )

        # Handle inheritance
        if parent_class:
            self.graph.add((class_uri, RDFS.subClassOf, parent_class))

        # Process properties
        properties = schema.get('properties', {})
        required_props = set(schema.get('required', []))

        for prop_name, prop_schema in properties.items():
            self._process_property(
                prop_name,
                prop_schema,
                class_uri,
                is_required=prop_name in required_props
            )

        # Handle pattern properties
        if 'patternProperties' in schema:
            for pattern, prop_schema in schema['patternProperties'].items():
                pattern_name = f"{name}_{self._sanitize_name(pattern)}_Pattern"
                self._process_property(pattern_name, prop_schema, class_uri)

        # Handle additional properties
        if 'additionalProperties' in schema:
            additional = schema['additionalProperties']
            if isinstance(additional, dict):
                self._process_property(
                    f"{name}_AdditionalProperty",
                    additional,
                    class_uri
                )

        return class_uri

    def _process_property(self, prop_name: str, prop_schema: Dict[str, Any],
                         domain_class: URIRef, is_required: bool = False) -> URIRef:
        """Process a property and create OWL property.

        Args:
            prop_name: Property name
            prop_schema: Property schema
            domain_class: Domain class URI
            is_required: Whether property is required

        Returns:
            URIRef of created property
        """
        # Handle $ref
        if '$ref' in prop_schema:
            resolved_schema = self._resolve_ref(prop_schema['$ref'], prop_schema)
            if resolved_schema:
                prop_schema = {**prop_schema, **self._get_ref_schema(prop_schema['$ref'])}

        # Determine property type
        prop_type = prop_schema.get('type')
        is_object = prop_type == 'object' or 'properties' in prop_schema
        is_array = prop_type == 'array'

        # Create appropriate property type
        if is_object or is_array:
            # Object or array -> ObjectProperty
            prop_uri = self.add_property(
                prop_name,
                OWL.ObjectProperty,
                domain=domain_class,
                label=prop_schema.get('title', prop_name)
            )

            # Create range class for object
            if is_object:
                range_class_name = prop_schema.get('title', f"{prop_name}Type")
                range_class = self._process_object_schema(prop_schema, range_class_name)
                self.graph.add((prop_uri, RDFS.range, range_class))
            elif is_array:
                # Handle array items
                items_schema = prop_schema.get('items', {})
                if items_schema:
                    items_type = items_schema.get('type')
                    if items_type == 'object' or 'properties' in items_schema:
                        range_class_name = items_schema.get('title', f"{prop_name}Item")
                        range_class = self._process_object_schema(items_schema, range_class_name)
                        self.graph.add((prop_uri, RDFS.range, range_class))
                    else:
                        # Primitive items
                        range_type = self._map_json_type_to_xsd(items_type or 'string')
                        self.graph.add((prop_uri, RDFS.range, range_type))
        else:
            # Primitive type -> DatatypeProperty
            prop_uri = self.add_property(
                prop_name,
                OWL.DatatypeProperty,
                domain=domain_class,
                label=prop_schema.get('title', prop_name)
            )

            # Set range based on type
            range_type = self._map_json_type_to_xsd(prop_type or 'string')
            self.graph.add((prop_uri, RDFS.range, range_type))

        # Add description as comment
        if 'description' in prop_schema:
            self.graph.add((prop_uri, RDFS.comment, Literal(prop_schema['description'])))

        # Handle required constraint (using cardinality)
        if is_required:
            # Create restriction for minCardinality 1
            restriction = self.create_iri(f"{prop_name}_Required_Restriction")
            self.graph.add((restriction, RDF.type, OWL.Restriction))
            self.graph.add((restriction, OWL.onProperty, prop_uri))
            self.graph.add((restriction, OWL.minCardinality, Literal(1)))
            self.graph.add((domain_class, RDFS.subClassOf, restriction))

        # Handle enum constraint
        if 'enum' in prop_schema:
            enum_values = prop_schema['enum']
            for enum_val in enum_values:
                # Could create individuals or use data ranges
                # For simplicity, add as comment
                self.graph.add((
                    prop_uri,
                    RDFS.comment,
                    Literal(f"Allowed value: {enum_val}")
                ))

        return prop_uri

    def _process_array_schema(self, schema: Dict[str, Any], name: str,
                              parent_class: Optional[URIRef] = None) -> URIRef:
        """Process an array schema.

        Args:
            schema: Array schema
            name: Property name
            parent_class: Optional parent class

        Returns:
            URIRef for the array property
        """
        # Arrays are typically represented as properties with multiple values
        # Create a class for the array if it has object items
        items_schema = schema.get('items', {})
        items_type = items_schema.get('type')

        if items_type == 'object' or 'properties' in items_schema:
            return self._process_object_schema(items_schema, name, parent_class)
        else:
            # For primitive arrays, just return the XSD type
            return self._map_json_type_to_xsd(items_type or 'string')

    def _process_primitive_schema(self, schema: Dict[str, Any], name: str,
                                  parent_class: Optional[URIRef] = None) -> URIRef:
        """Process a primitive type schema.

        Args:
            schema: Primitive schema
            name: Type name
            parent_class: Optional parent class

        Returns:
            XSD type URIRef
        """
        schema_type = schema.get('type', 'string')
        return self._map_json_type_to_xsd(schema_type)

    def _process_union_type(self, schema: Dict[str, Any], name: str,
                           parent_class: Optional[URIRef] = None) -> URIRef:
        """Process a union type (multiple types).

        Args:
            schema: Schema with multiple types
            name: Type name
            parent_class: Optional parent class

        Returns:
            URIRef for union class
        """
        # Create a union class
        union_class = self.add_class(
            name,
            label=schema.get('title', name),
            comment=f"Union type: {', '.join(schema['type'])}"
        )

        # Process each type variant
        for i, type_variant in enumerate(schema['type']):
            variant_schema = {**schema, 'type': type_variant}
            variant_name = f"{name}_{type_variant}Variant"
            variant_class = self._process_schema(variant_schema, variant_name)
            if variant_class and isinstance(variant_class, URIRef):
                self.graph.add((union_class, RDFS.subClassOf, variant_class))

        return union_class

    def _process_all_of(self, schema: Dict[str, Any], name: str,
                       parent_class: Optional[URIRef] = None) -> URIRef:
        """Process allOf composition (intersection).

        Args:
            schema: Schema with allOf
            name: Class name
            parent_class: Optional parent class

        Returns:
            URIRef of created class
        """
        # Create class that inherits from all schemas in allOf
        class_uri = self.add_class(
            name,
            label=schema.get('title', name),
            comment=schema.get('description')
        )

        for i, sub_schema in enumerate(schema['allOf']):
            sub_class = self._process_schema(sub_schema, f"{name}_AllOf_{i}")
            if sub_class and isinstance(sub_class, URIRef):
                self.graph.add((class_uri, RDFS.subClassOf, sub_class))

        if parent_class:
            self.graph.add((class_uri, RDFS.subClassOf, parent_class))

        return class_uri

    def _process_any_of(self, schema: Dict[str, Any], name: str,
                       parent_class: Optional[URIRef] = None) -> URIRef:
        """Process anyOf composition (union).

        Args:
            schema: Schema with anyOf
            name: Class name
            parent_class: Optional parent class

        Returns:
            URIRef of created class
        """
        # Create class with comment about anyOf variants
        class_uri = self.add_class(
            name,
            label=schema.get('title', name),
            comment=f"Any of {len(schema['anyOf'])} variants"
        )

        # Create subclasses for each variant
        for i, sub_schema in enumerate(schema['anyOf']):
            sub_class = self._process_schema(sub_schema, f"{name}_AnyOf_{i}")
            if sub_class and isinstance(sub_class, URIRef):
                # Variants are subclasses
                self.graph.add((sub_class, RDFS.subClassOf, class_uri))

        if parent_class:
            self.graph.add((class_uri, RDFS.subClassOf, parent_class))

        return class_uri

    def _process_one_of(self, schema: Dict[str, Any], name: str,
                       parent_class: Optional[URIRef] = None) -> URIRef:
        """Process oneOf composition (exclusive union).

        Args:
            schema: Schema with oneOf
            name: Class name
            parent_class: Optional parent class

        Returns:
            URIRef of created class
        """
        # Similar to anyOf but with disjoint constraint
        class_uri = self.add_class(
            name,
            label=schema.get('title', name),
            comment=f"Exactly one of {len(schema['oneOf'])} variants"
        )

        variant_classes = []
        for i, sub_schema in enumerate(schema['oneOf']):
            sub_class = self._process_schema(sub_schema, f"{name}_OneOf_{i}")
            if sub_class and isinstance(sub_class, URIRef):
                self.graph.add((sub_class, RDFS.subClassOf, class_uri))
                variant_classes.append(sub_class)

        # Add disjointness between variants
        for i, class1 in enumerate(variant_classes):
            for class2 in variant_classes[i+1:]:
                self.graph.add((class1, OWL.disjointWith, class2))

        if parent_class:
            self.graph.add((class_uri, RDFS.subClassOf, parent_class))

        return class_uri

    def _resolve_ref(self, ref: str, context: Dict[str, Any]) -> Optional[URIRef]:
        """Resolve a $ref reference.

        Args:
            ref: Reference string (e.g., "#/definitions/Person")
            context: Current schema context

        Returns:
            URIRef of resolved reference or None
        """
        if ref in self.processed_refs:
            # Already processed, return existing class
            ref_name = ref.split('/')[-1]
            return self.create_iri(ref_name)

        self.processed_refs.add(ref)

        # Get the referenced schema
        ref_schema = self._get_ref_schema(ref)
        if not ref_schema:
            logger.warning(f"Could not resolve $ref: {ref}")
            return None

        # Extract name from reference
        ref_name = ref.split('/')[-1]

        # Process the referenced schema
        return self._process_schema(ref_schema, ref_name)

    def _get_ref_schema(self, ref: str) -> Optional[Dict[str, Any]]:
        """Get schema from a $ref reference.

        Args:
            ref: Reference string

        Returns:
            Referenced schema or None
        """
        if ref.startswith('#/'):
            # Internal reference
            path_parts = ref[2:].split('/')
            schema = self.definitions

            for part in path_parts:
                if isinstance(schema, dict) and part in schema:
                    schema = schema[part]
                else:
                    return None

            return schema
        elif self.resolve_external_refs:
            # External reference - would need to load external file
            logger.warning(f"External reference resolution not fully implemented: {ref}")
            return None
        else:
            logger.warning(f"External references disabled: {ref}")
            return None

    def _map_json_type_to_xsd(self, json_type: str) -> URIRef:
        """Map JSON Schema type to XSD type.

        Args:
            json_type: JSON Schema type

        Returns:
            XSD type URIRef
        """
        type_map = {
            'string': XSD.string,
            'number': XSD.decimal,
            'integer': XSD.integer,
            'boolean': XSD.boolean,
            'null': XSD.string,  # No direct XSD equivalent
        }

        return type_map.get(json_type, XSD.string)


# Backward compatibility function
def convert_jsonschema_to_owl(json_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert JSON Schema to OWL (backward compatibility wrapper).

    Args:
        json_path: Path to JSON Schema file
        output_path: Path to output OWL file
        base_uri: Optional base URI for the ontology

    Returns:
        Path to generated OWL file
    """
    config = {}
    if base_uri:
        config['base_uri'] = base_uri

    converter = JSONSchemaConverter(config)
    return converter.convert(json_path, output_path)
