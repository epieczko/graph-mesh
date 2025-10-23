"""Pydantic models for manifest validation and data structures."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class FetchType(str, Enum):
    """Supported fetch types for data sources."""
    LOCAL = "local"
    HTTP = "http"
    HTTPS = "https"
    GIT = "git"
    S3 = "s3"


class ConvertType(str, Enum):
    """Supported conversion types for schemas."""
    XSD = "xsd"
    JSON = "json"
    CSV = "csv"


class MatcherType(str, Enum):
    """Supported matcher types for alignment."""
    LOGMAP = "LogMap"
    AML = "AML"
    BERTMAP = "BERTMap"


class FetchConfig(BaseModel):
    """Configuration for fetching source data."""

    type: FetchType = Field(default=FetchType.LOCAL, description="Type of fetch operation")
    path: Optional[str] = Field(default=None, description="Single path for the source")
    paths: Optional[List[str]] = Field(default=None, description="Multiple paths for the source")
    url: Optional[str] = Field(default=None, description="URL for remote sources")
    branch: Optional[str] = Field(default=None, description="Git branch (for git fetch)")
    credentials: Optional[Dict[str, str]] = Field(default=None, description="Authentication credentials")

    @model_validator(mode='after')
    def validate_fetch_config(self) -> 'FetchConfig':
        """Ensure at least one path source is provided."""
        if self.type == FetchType.LOCAL:
            if not self.path and not self.paths:
                raise ValueError("Local fetch requires 'path' or 'paths'")
        elif self.type in (FetchType.HTTP, FetchType.HTTPS, FetchType.S3):
            if not self.url:
                raise ValueError(f"{self.type.value} fetch requires 'url'")
        elif self.type == FetchType.GIT:
            if not self.url:
                raise ValueError("Git fetch requires 'url'")
        return self

    @field_validator('path', 'paths')
    @classmethod
    def validate_paths_exist(cls, v: Optional[Union[str, List[str]]]) -> Optional[Union[str, List[str]]]:
        """Validate that local paths exist (only for local fetch)."""
        # Note: Actual file existence check is done in pre-flight validation
        return v


class ConvertConfig(BaseModel):
    """Configuration for schema conversion."""

    type: ConvertType = Field(default=ConvertType.XSD, description="Type of conversion")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional conversion options")
    namespace: Optional[str] = Field(default=None, description="Target namespace for OWL conversion")
    prefix: Optional[str] = Field(default=None, description="Prefix for generated URIs")


class SourceConfig(BaseModel):
    """Configuration for a single data source."""

    id: str = Field(..., description="Unique identifier for the source", alias="identifier")
    fetch: FetchConfig = Field(default_factory=FetchConfig, description="Fetch configuration")
    convert: ConvertConfig = Field(default_factory=ConvertConfig, description="Conversion configuration")
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    description: Optional[str] = Field(default=None, description="Human-readable description")

    class Config:
        populate_by_name = True

    @field_validator('id')
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Ensure identifier is valid."""
        if not v or not v.strip():
            raise ValueError("Source identifier cannot be empty")
        # Ensure safe for filesystem
        if any(char in v for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            raise ValueError("Source identifier contains invalid filesystem characters")
        return v.strip()


class MetaOntologyType(str, Enum):
    """Supported meta-ontology types."""
    GENERIC = "generic"
    FIBO = "fibo"
    CUSTOM = "custom"
    COMPOSITE = "composite"


class MetaOntologyConfig(BaseModel):
    """Configuration for the meta-ontology provider."""

    type: MetaOntologyType = Field(
        default=MetaOntologyType.GENERIC,
        description="Type of meta-ontology to use"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific options"
    )

    @field_validator('options')
    @classmethod
    def validate_options(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
        """Validate provider-specific options."""
        # Note: Detailed validation happens in provider initialization
        return v

    class Config:
        use_enum_values = True


class AlignmentConfig(BaseModel):
    """Configuration for the alignment stage."""

    matchers: List[str] = Field(
        default_factory=lambda: ["LogMap", "AML", "BERTMap"],
        description="List of matchers to use"
    )
    timeout: Optional[int] = Field(default=300, description="Timeout per matcher in seconds")
    threshold: Optional[float] = Field(default=0.5, description="Confidence threshold for mappings")

    @field_validator('matchers')
    @classmethod
    def validate_matchers(cls, v: List[str]) -> List[str]:
        """Ensure all matchers are supported."""
        valid_matchers = {m.value for m in MatcherType}
        for matcher in v:
            if matcher not in valid_matchers:
                raise ValueError(f"Unsupported matcher: {matcher}. Valid options: {valid_matchers}")
        return v


class PipelineConfig(BaseModel):
    """Configuration for pipeline execution."""

    max_retries: int = Field(default=3, description="Maximum retry attempts for failed stages")
    retry_delay: int = Field(default=5, description="Delay between retries in seconds")
    parallel_sources: bool = Field(default=False, description="Process sources in parallel")
    checkpoint_enabled: bool = Field(default=True, description="Enable checkpointing for resume")
    fail_fast: bool = Field(default=False, description="Stop on first error")
    cleanup_on_success: bool = Field(default=False, description="Remove intermediate artifacts on success")


class PipelineManifest(BaseModel):
    """Complete pipeline manifest with validation."""

    name: str = Field(..., description="Pipeline name/identifier")
    version: str = Field(default="1.0", description="Manifest version")
    description: Optional[str] = Field(default=None, description="Pipeline description")
    meta_ontology: MetaOntologyConfig = Field(
        default_factory=MetaOntologyConfig,
        description="Meta-ontology provider configuration"
    )
    sources: List[SourceConfig] = Field(..., min_length=1, description="List of data sources")
    matchers: List[str] = Field(
        default_factory=lambda: ["LogMap", "AML", "BERTMap"],
        description="Matchers for alignment"
    )
    alignment: AlignmentConfig = Field(default_factory=AlignmentConfig, description="Alignment configuration")
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig, description="Pipeline execution config")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure pipeline name is valid."""
        if not v or not v.strip():
            raise ValueError("Pipeline name cannot be empty")
        return v.strip()

    @field_validator('sources')
    @classmethod
    def validate_unique_sources(cls, v: List[SourceConfig]) -> List[SourceConfig]:
        """Ensure all source identifiers are unique."""
        ids = [source.id for source in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate source identifiers found: {set(duplicates)}")
        return v

    @model_validator(mode='after')
    def validate_matchers_alignment(self) -> 'PipelineManifest':
        """Ensure matchers list matches alignment config."""
        if self.matchers and not self.alignment.matchers:
            self.alignment.matchers = self.matchers
        elif self.alignment.matchers and not self.matchers:
            self.matchers = self.alignment.matchers
        return self


class PipelineState(str, Enum):
    """Pipeline execution states."""
    PENDING = "pending"
    VALIDATING = "validating"
    FETCHING = "fetching"
    INGESTING = "ingesting"
    ALIGNING = "aligning"
    FUSING = "fusing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceState(BaseModel):
    """State tracking for individual source processing."""

    source_id: str
    fetched: bool = False
    ingested: bool = False
    aligned: bool = False
    error: Optional[str] = None
    fetch_path: Optional[str] = None
    converted_path: Optional[str] = None
    mapping_paths: List[str] = Field(default_factory=list)


class PipelineCheckpoint(BaseModel):
    """Checkpoint data for pipeline resume capability."""

    manifest_path: str
    workdir: str
    state: PipelineState
    current_stage: str
    sources: Dict[str, SourceState]
    meta_ontology_path: Optional[str] = None
    merged_graph_path: Optional[str] = None
    timestamp: str
    error_message: Optional[str] = None

    def to_file(self, path: Path) -> None:
        """Save checkpoint to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def from_file(cls, path: Path) -> 'PipelineCheckpoint':
        """Load checkpoint from file."""
        return cls.model_validate_json(path.read_text())

    def is_complete(self) -> bool:
        """Check if pipeline is complete."""
        return self.state == PipelineState.COMPLETED

    def is_failed(self) -> bool:
        """Check if pipeline has failed."""
        return self.state == PipelineState.FAILED

    def can_resume(self) -> bool:
        """Check if pipeline can be resumed."""
        return self.state not in (PipelineState.COMPLETED, PipelineState.CANCELLED)
