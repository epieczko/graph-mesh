"""CSV/TSV to OWL converter using CSVW (CSV on the Web) patterns.

This module provides CSV and TSV to OWL conversion with support for:
- Column-to-property mappings
- Type inference and explicit type specification
- CSVW metadata files (optional)
- Custom delimiters (CSV, TSV, and custom)
- Header row detection and column naming
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, XSD, URIRef

from .converter_base import SchemaConverter

logger = logging.getLogger(__name__)


class CSVConverter(SchemaConverter):
    """CSV/TSV to OWL converter using CSVW patterns.

    Converts CSV/TSV files to OWL ontologies by:
    - Creating a class representing the row type
    - Creating properties for each column
    - Inferring or using explicit type mappings
    - Supporting CSVW metadata for advanced configuration
    """

    SCHEMA_TYPE = ['csv', 'tsv']

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize CSV converter.

        Args:
            config: Optional configuration:
                - delimiter (str): Column delimiter (default: auto-detect)
                - has_header (bool): Whether first row is header (default: True)
                - row_class_name (str): Name for row class (default: 'Row')
                - type_mapping (dict): Column name to XSD type mapping
                - metadata_file (str): Path to CSVW metadata JSON file
                - sample_size (int): Number of rows to sample for type inference (default: 100)
        """
        super().__init__(config)
        self.delimiter = self.config.get('delimiter')  # Auto-detect if None
        self.has_header = self.config.get('has_header', True)
        self.row_class_name = self.config.get('row_class_name', 'Row')
        self.type_mapping = self.config.get('type_mapping', {})
        self.metadata_file = self.config.get('metadata_file')
        self.sample_size = self.config.get('sample_size', 100)

    @classmethod
    def supported_extensions(cls) -> List[str]:
        """Return supported file extensions."""
        return ['.csv', '.tsv', '.txt']

    def convert(self, input_path: str, output_path: str) -> str:
        """Convert CSV/TSV to OWL.

        Args:
            input_path: Path to CSV/TSV file
            output_path: Path to output OWL file

        Returns:
            Path to generated OWL file

        Raises:
            ValueError: If file cannot be parsed or conversion fails
        """
        logger.info(f"Converting CSV/TSV: {input_path}")

        input_file = Path(input_path)

        # Auto-detect delimiter if not specified
        delimiter = self.delimiter
        if not delimiter:
            delimiter = self._detect_delimiter(input_path)
            logger.info(f"Detected delimiter: {repr(delimiter)}")

        # Load CSVW metadata if provided
        metadata = {}
        if self.metadata_file:
            metadata = self._load_csvw_metadata(self.metadata_file)
        else:
            # Try to find metadata file with same name
            metadata_path = input_file.with_suffix(input_file.suffix + '-metadata.json')
            if metadata_path.exists():
                logger.info(f"Found CSVW metadata: {metadata_path}")
                metadata = self._load_csvw_metadata(str(metadata_path))

        # Parse CSV
        columns, rows = self._parse_csv(input_path, delimiter)

        if not columns:
            raise ValueError(f"No columns found in CSV file: {input_path}")

        logger.info(f"Found {len(columns)} columns and {len(rows)} rows")

        # Infer types from data if not provided
        inferred_types = self._infer_column_types(columns, rows, metadata)

        # Create graph
        self.create_graph()

        # Create row class
        row_class_name = metadata.get('row_class', self.row_class_name)
        row_class_uri = self.add_class(
            row_class_name,
            label=metadata.get('title', row_class_name),
            comment=metadata.get('description', f'Represents a row in {input_file.name}')
        )

        # Create properties for each column
        for i, column_name in enumerate(columns):
            # Get column metadata
            col_metadata = self._get_column_metadata(column_name, i, metadata)

            # Determine property name
            prop_name = col_metadata.get('name', column_name)

            # Determine type
            col_type = (
                self.type_mapping.get(column_name) or
                col_metadata.get('datatype') or
                inferred_types.get(column_name, 'string')
            )

            # Map to XSD type
            xsd_type = self._map_type_to_xsd(col_type)

            # Create property
            prop_uri = self.add_property(
                prop_name,
                OWL.DatatypeProperty,
                domain=row_class_uri,
                range_=xsd_type,
                label=col_metadata.get('title', prop_name)
            )

            # Add description
            if 'description' in col_metadata:
                self.graph.add((prop_uri, RDFS.comment, Literal(col_metadata['description'])))

            # Add required constraint
            if col_metadata.get('required', False):
                restriction = self.create_iri(f"{prop_name}_Required_Restriction")
                self.graph.add((restriction, RDF.type, OWL.Restriction))
                self.graph.add((restriction, OWL.onProperty, prop_uri))
                self.graph.add((restriction, OWL.minCardinality, Literal(1)))
                self.graph.add((row_class_uri, RDFS.subClassOf, restriction))

        # Serialize
        result = self.serialize_graph(output_path)

        # Generate statistics
        stats = {
            'classes': 1,  # Row class
            'datatype_properties': len(columns),
            'columns': len(columns),
            'rows_sampled': min(len(rows), self.sample_size)
        }
        self.generate_report(output_path, stats)

        return result

    def _detect_delimiter(self, file_path: str) -> str:
        """Auto-detect CSV delimiter.

        Args:
            file_path: Path to CSV file

        Returns:
            Detected delimiter character
        """
        # Check file extension first
        ext = Path(file_path).suffix.lower()
        if ext == '.tsv':
            return '\t'

        # Sample first few lines
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sample = ''.join([f.readline() for _ in range(10)])

        # Use csv.Sniffer to detect
        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            return delimiter
        except Exception as e:
            logger.warning(f"Could not detect delimiter: {e}, defaulting to comma")
            return ','

    def _parse_csv(self, file_path: str, delimiter: str) -> tuple[List[str], List[Dict[str, str]]]:
        """Parse CSV file.

        Args:
            file_path: Path to CSV file
            delimiter: Column delimiter

        Returns:
            Tuple of (column_names, rows)
        """
        columns = []
        rows = []

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f, delimiter=delimiter)

            # Read header
            if self.has_header:
                try:
                    columns = next(reader)
                    columns = [self._sanitize_column_name(col) for col in columns]
                except StopIteration:
                    return [], []
            else:
                # Generate column names
                first_row = next(reader, None)
                if not first_row:
                    return [], []
                columns = [f"column_{i}" for i in range(len(first_row))]
                rows.append(dict(zip(columns, first_row)))

            # Read data rows (sample for type inference)
            for i, row in enumerate(reader):
                if i >= self.sample_size:
                    break
                if len(row) == len(columns):
                    rows.append(dict(zip(columns, row)))

        return columns, rows

    def _sanitize_column_name(self, name: str) -> str:
        """Sanitize column name to be a valid property name.

        Args:
            name: Original column name

        Returns:
            Sanitized column name
        """
        # Remove whitespace and special characters
        name = name.strip()
        if not name:
            return 'unnamed_column'

        # Use base class sanitization
        return self._sanitize_name(name)

    def _infer_column_types(self, columns: List[str], rows: List[Dict[str, str]],
                           metadata: Dict[str, Any]) -> Dict[str, str]:
        """Infer column types from data.

        Args:
            columns: Column names
            rows: Sample rows
            metadata: CSVW metadata

        Returns:
            Dictionary mapping column names to inferred types
        """
        types = {}

        for column in columns:
            # Check if type is specified in metadata
            col_meta = self._get_column_metadata(column, columns.index(column), metadata)
            if 'datatype' in col_meta:
                types[column] = col_meta['datatype']
                continue

            # Infer from data
            values = [row.get(column, '') for row in rows if row.get(column, '').strip()]
            inferred_type = self._infer_type_from_values(values)
            types[column] = inferred_type

        return types

    def _infer_type_from_values(self, values: List[str]) -> str:
        """Infer data type from sample values.

        Args:
            values: List of sample values

        Returns:
            Inferred type name
        """
        if not values:
            return 'string'

        # Check for boolean
        bool_values = {'true', 'false', 'yes', 'no', '0', '1', 't', 'f', 'y', 'n'}
        if all(v.lower() in bool_values for v in values if v):
            return 'boolean'

        # Check for integer
        try:
            [int(v) for v in values if v]
            return 'integer'
        except ValueError:
            pass

        # Check for decimal
        try:
            [float(v) for v in values if v]
            return 'decimal'
        except ValueError:
            pass

        # Check for date (basic check)
        if all(self._looks_like_date(v) for v in values if v):
            return 'date'

        # Default to string
        return 'string'

    def _looks_like_date(self, value: str) -> bool:
        """Check if value looks like a date.

        Args:
            value: String value

        Returns:
            True if looks like a date
        """
        # Very basic check for common date patterns
        date_patterns = ['-', '/', '.']
        digit_count = sum(c.isdigit() for c in value)
        separator_count = sum(value.count(p) for p in date_patterns)

        return digit_count >= 4 and separator_count >= 1

    def _map_type_to_xsd(self, type_name: str) -> URIRef:
        """Map type name to XSD type.

        Args:
            type_name: Type name (string, integer, boolean, etc.)

        Returns:
            XSD type URIRef
        """
        type_map = {
            'string': XSD.string,
            'integer': XSD.integer,
            'int': XSD.integer,
            'decimal': XSD.decimal,
            'float': XSD.float,
            'double': XSD.double,
            'number': XSD.decimal,
            'boolean': XSD.boolean,
            'bool': XSD.boolean,
            'date': XSD.date,
            'datetime': XSD.dateTime,
            'time': XSD.time,
            'anyuri': XSD.anyURI,
            'uri': XSD.anyURI,
        }

        return type_map.get(type_name.lower(), XSD.string)

    def _load_csvw_metadata(self, metadata_path: str) -> Dict[str, Any]:
        """Load CSVW metadata file.

        Args:
            metadata_path: Path to metadata JSON file

        Returns:
            Metadata dictionary
        """
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            logger.info(f"Loaded CSVW metadata from {metadata_path}")
            return metadata
        except Exception as e:
            logger.warning(f"Failed to load CSVW metadata: {e}")
            return {}

    def _get_column_metadata(self, column_name: str, column_index: int,
                            metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for a specific column.

        Args:
            column_name: Column name
            column_index: Column index
            metadata: CSVW metadata

        Returns:
            Column metadata dictionary
        """
        # CSVW metadata structure: { "tableSchema": { "columns": [...] } }
        table_schema = metadata.get('tableSchema', {})
        columns = table_schema.get('columns', [])

        # Find column by name or index
        for col_meta in columns:
            if col_meta.get('name') == column_name:
                return col_meta
            if col_meta.get('titles') == column_name:
                return col_meta

        if column_index < len(columns):
            return columns[column_index]

        return {}


# Backward compatibility function
def convert_csv_to_owl(csv_path: str, output_path: str, base_uri: Optional[str] = None,
                      delimiter: Optional[str] = None) -> str:
    """Convert CSV to OWL (convenience function).

    Args:
        csv_path: Path to CSV file
        output_path: Path to output OWL file
        base_uri: Optional base URI for the ontology
        delimiter: Optional delimiter (auto-detected if not provided)

    Returns:
        Path to generated OWL file
    """
    config = {}
    if base_uri:
        config['base_uri'] = base_uri
    if delimiter:
        config['delimiter'] = delimiter

    converter = CSVConverter(config)
    return converter.convert(csv_path, output_path)


def convert_tsv_to_owl(tsv_path: str, output_path: str, base_uri: Optional[str] = None) -> str:
    """Convert TSV to OWL (convenience function).

    Args:
        tsv_path: Path to TSV file
        output_path: Path to output OWL file
        base_uri: Optional base URI for the ontology

    Returns:
        Path to generated OWL file
    """
    config = {'delimiter': '\t'}
    if base_uri:
        config['base_uri'] = base_uri

    converter = CSVConverter(config)
    return converter.convert(tsv_path, output_path)
