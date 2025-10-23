"""Custom exception hierarchy for Graph Mesh orchestrator."""

from __future__ import annotations

from typing import Any, Dict, Optional


class GraphMeshError(Exception):
    """Base exception for all Graph Mesh errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize error with message and optional details.

        Args:
            message: Human-readable error message
            details: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for structured logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# Validation Errors

class ValidationError(GraphMeshError):
    """Base class for validation errors."""
    pass


class ManifestValidationError(ValidationError):
    """Raised when manifest validation fails."""

    def __init__(self, message: str, manifest_path: Optional[str] = None, errors: Optional[list] = None) -> None:
        details = {}
        if manifest_path:
            details["manifest_path"] = manifest_path
        if errors:
            details["validation_errors"] = errors
        super().__init__(message, details)


class SchemaValidationError(ValidationError):
    """Raised when schema/data validation fails."""

    def __init__(self, message: str, schema_path: Optional[str] = None, field: Optional[str] = None) -> None:
        details = {}
        if schema_path:
            details["schema_path"] = schema_path
        if field:
            details["field"] = field
        super().__init__(message, details)


class PreflightCheckError(ValidationError):
    """Raised when pre-flight checks fail."""

    def __init__(self, message: str, check_name: str, suggestion: Optional[str] = None) -> None:
        details = {"check_name": check_name}
        if suggestion:
            details["suggestion"] = suggestion
        super().__init__(message, details)


# Pipeline Errors

class PipelineError(GraphMeshError):
    """Base class for pipeline execution errors."""
    pass


class PipelineStateError(PipelineError):
    """Raised when pipeline state is invalid or corrupted."""

    def __init__(self, message: str, current_state: Optional[str] = None, expected_state: Optional[str] = None) -> None:
        details = {}
        if current_state:
            details["current_state"] = current_state
        if expected_state:
            details["expected_state"] = expected_state
        super().__init__(message, details)


class PipelineConfigurationError(PipelineError):
    """Raised when pipeline configuration is invalid."""

    def __init__(self, message: str, config_key: Optional[str] = None) -> None:
        details = {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, details)


class CheckpointError(PipelineError):
    """Raised when checkpoint operations fail."""

    def __init__(self, message: str, checkpoint_path: Optional[str] = None, operation: Optional[str] = None) -> None:
        details = {}
        if checkpoint_path:
            details["checkpoint_path"] = checkpoint_path
        if operation:
            details["operation"] = operation
        super().__init__(message, details)


# Stage-Specific Errors

class StageError(PipelineError):
    """Base class for stage-specific errors."""

    def __init__(self, message: str, stage: str, source_id: Optional[str] = None, **kwargs: Any) -> None:
        details = {"stage": stage}
        if source_id:
            details["source_id"] = source_id
        details.update(kwargs)
        super().__init__(message, details)


class FetchError(StageError):
    """Raised when fetching source data fails."""

    def __init__(self, message: str, source_id: str, fetch_type: Optional[str] = None, path: Optional[str] = None) -> None:
        details = {}
        if fetch_type:
            details["fetch_type"] = fetch_type
        if path:
            details["path"] = path
        super().__init__(message, stage="fetch", source_id=source_id, **details)


class IngestError(StageError):
    """Raised when ingestion/conversion fails."""

    def __init__(self, message: str, source_id: str, converter_type: Optional[str] = None, input_path: Optional[str] = None) -> None:
        details = {}
        if converter_type:
            details["converter_type"] = converter_type
        if input_path:
            details["input_path"] = input_path
        super().__init__(message, stage="ingest", source_id=source_id, **details)


class AlignmentError(StageError):
    """Raised when alignment/matching fails."""

    def __init__(self, message: str, source_id: str, matcher: Optional[str] = None, **kwargs: Any) -> None:
        details = {}
        if matcher:
            details["matcher"] = matcher
        details.update(kwargs)
        super().__init__(message, stage="alignment", source_id=source_id, **details)


class FusionError(StageError):
    """Raised when graph fusion fails."""

    def __init__(self, message: str, graph_count: Optional[int] = None) -> None:
        details = {}
        if graph_count:
            details["graph_count"] = graph_count
        super().__init__(message, stage="fusion", **details)


# Resource Errors

class ResourceError(GraphMeshError):
    """Base class for resource-related errors."""
    pass


class FileNotFoundError(ResourceError):
    """Raised when a required file is not found."""

    def __init__(self, message: str, file_path: str, resource_type: Optional[str] = None) -> None:
        details = {"file_path": file_path}
        if resource_type:
            details["resource_type"] = resource_type
        super().__init__(message, details)


class DirectoryNotFoundError(ResourceError):
    """Raised when a required directory is not found."""

    def __init__(self, message: str, directory_path: str) -> None:
        super().__init__(message, {"directory_path": directory_path})


class ResourceAccessError(ResourceError):
    """Raised when resource access fails due to permissions."""

    def __init__(self, message: str, resource_path: str, operation: str) -> None:
        super().__init__(message, {"resource_path": resource_path, "operation": operation})


# Dependency Errors

class DependencyError(GraphMeshError):
    """Base class for dependency-related errors."""
    pass


class DockerNotAvailableError(DependencyError):
    """Raised when Docker is not available or not running."""

    def __init__(self, message: str = "Docker is not available or not running") -> None:
        super().__init__(message, {"suggestion": "Please install Docker and ensure the Docker daemon is running"})


class MatcherNotAvailableError(DependencyError):
    """Raised when a required matcher is not available."""

    def __init__(self, matcher_name: str, reason: Optional[str] = None) -> None:
        message = f"Matcher '{matcher_name}' is not available"
        details = {"matcher_name": matcher_name}
        if reason:
            message += f": {reason}"
            details["reason"] = reason
        super().__init__(message, details)


class ConverterNotAvailableError(DependencyError):
    """Raised when a required converter is not available."""

    def __init__(self, converter_type: str) -> None:
        message = f"Converter for type '{converter_type}' is not registered"
        super().__init__(message, {"converter_type": converter_type})


# Recovery and Retry Errors

class RecoverableError(GraphMeshError):
    """Base class for errors that can be retried."""

    def __init__(self, message: str, retry_count: int = 0, max_retries: int = 3, **kwargs: Any) -> None:
        details = {"retry_count": retry_count, "max_retries": max_retries}
        details.update(kwargs)
        super().__init__(message, details)

    def can_retry(self) -> bool:
        """Check if error can be retried."""
        return self.details.get("retry_count", 0) < self.details.get("max_retries", 3)


class TransientError(RecoverableError):
    """Raised for transient errors that should be retried."""
    pass


class NetworkError(TransientError):
    """Raised when network operations fail."""

    def __init__(self, message: str, url: Optional[str] = None, **kwargs: Any) -> None:
        details = kwargs
        if url:
            details["url"] = url
        super().__init__(message, **details)


class TimeoutError(TransientError):
    """Raised when an operation times out."""

    def __init__(self, message: str, operation: str, timeout_seconds: Optional[int] = None) -> None:
        details = {"operation": operation}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, **details)


# Critical Errors

class CriticalError(GraphMeshError):
    """Base class for critical errors that cannot be recovered."""
    pass


class DataCorruptionError(CriticalError):
    """Raised when data corruption is detected."""

    def __init__(self, message: str, affected_resource: str) -> None:
        super().__init__(message, {"affected_resource": affected_resource})


class SystemError(CriticalError):
    """Raised for system-level errors."""

    def __init__(self, message: str, system_component: Optional[str] = None) -> None:
        details = {}
        if system_component:
            details["system_component"] = system_component
        super().__init__(message, details)
