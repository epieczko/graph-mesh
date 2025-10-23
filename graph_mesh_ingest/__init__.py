"""Graph Mesh Schema Ingest - Schema to OWL Conversion.

This package provides a plugin-based system for converting various schema formats
to OWL ontologies. Supported formats include:
- XSD (XML Schema) - via Ontmalizer or xmlschema
- JSON Schema - with nested objects, $ref, and validation
- CSV/TSV - with CSVW patterns and type inference

The conversion system uses a plugin architecture where converters automatically
register themselves and can be retrieved by schema type.
"""

from .converter_base import (
    SchemaConverter,
    ConverterRegistry,
    get_converter,
)

# Import converters to trigger auto-registration
from .xsd_to_owl import (
    XSDConverter,
    convert_xsd_to_owl,
    convert_xsd_list_to_owl,
)

from .json_to_owl import (
    JSONSchemaConverter,
    convert_jsonschema_to_owl,
)

from .csv_to_owl import (
    CSVConverter,
    convert_csv_to_owl,
    convert_tsv_to_owl,
)

__all__ = [
    # Base classes
    'SchemaConverter',
    'ConverterRegistry',
    'get_converter',

    # Converter classes
    'XSDConverter',
    'JSONSchemaConverter',
    'CSVConverter',

    # Backward compatibility functions
    'convert_xsd_to_owl',
    'convert_xsd_list_to_owl',
    'convert_jsonschema_to_owl',
    'convert_csv_to_owl',
    'convert_tsv_to_owl',
]

__version__ = '1.0.0'
