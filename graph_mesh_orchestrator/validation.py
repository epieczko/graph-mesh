"""Pre-flight validation checks for Graph Mesh pipeline."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import ValidationError as PydanticValidationError

from graph_mesh_orchestrator.errors import (
    DirectoryNotFoundError,
    DockerNotAvailableError,
    FileNotFoundError as GraphMeshFileNotFoundError,
    ManifestValidationError,
    MatcherNotAvailableError,
    PreflightCheckError,
    ResourceAccessError,
)
from graph_mesh_orchestrator.models import FetchType, PipelineManifest


class PreflightValidator:
    """Pre-flight validation for pipeline execution."""

    def __init__(self, manifest_path: Path, workdir: Optional[Path] = None) -> None:
        """Initialize validator.

        Args:
            manifest_path: Path to pipeline manifest
            workdir: Working directory for artifacts
        """
        self.manifest_path = manifest_path
        self.workdir = workdir or Path("artifacts")
        self.manifest: Optional[PipelineManifest] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self, check_docker: bool = True) -> Tuple[bool, List[str], List[str]]:
        """Run all pre-flight checks.

        Args:
            check_docker: Whether to check Docker availability

        Returns:
            Tuple of (success, errors, warnings)
        """
        checks = [
            ("Manifest file existence", self.check_manifest_exists),
            ("Manifest YAML syntax", self.check_manifest_yaml),
            ("Manifest schema validation", self.check_manifest_schema),
            ("Source file availability", self.check_source_files),
            ("Working directory access", self.check_workdir),
            ("Python dependencies", self.check_python_dependencies),
        ]

        if check_docker:
            checks.append(("Docker availability", self.check_docker))

        for check_name, check_func in checks:
            try:
                check_func()
            except PreflightCheckError as e:
                self.errors.append(f"{check_name}: {e.message}")
            except Exception as e:
                self.errors.append(f"{check_name}: Unexpected error - {str(e)}")

        return len(self.errors) == 0, self.errors, self.warnings

    def check_manifest_exists(self) -> None:
        """Check if manifest file exists."""
        if not self.manifest_path.exists():
            raise PreflightCheckError(
                f"Manifest file not found: {self.manifest_path}",
                check_name="manifest_exists",
                suggestion="Verify the manifest path is correct"
            )

        if not self.manifest_path.is_file():
            raise PreflightCheckError(
                f"Manifest path is not a file: {self.manifest_path}",
                check_name="manifest_exists"
            )

    def check_manifest_yaml(self) -> None:
        """Check if manifest is valid YAML."""
        try:
            with open(self.manifest_path, 'r') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PreflightCheckError(
                f"Invalid YAML syntax: {str(e)}",
                check_name="manifest_yaml",
                suggestion="Check YAML indentation and syntax"
            )
        except Exception as e:
            raise PreflightCheckError(
                f"Failed to read manifest: {str(e)}",
                check_name="manifest_yaml"
            )

    def check_manifest_schema(self) -> None:
        """Validate manifest against pydantic schema."""
        try:
            with open(self.manifest_path, 'r') as f:
                data = yaml.safe_load(f)

            self.manifest = PipelineManifest.model_validate(data)

        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                loc = " -> ".join(str(l) for l in error['loc'])
                errors.append(f"{loc}: {error['msg']}")

            raise ManifestValidationError(
                "Manifest validation failed",
                manifest_path=str(self.manifest_path),
                errors=errors
            )
        except Exception as e:
            raise PreflightCheckError(
                f"Manifest schema validation error: {str(e)}",
                check_name="manifest_schema"
            )

    def check_source_files(self) -> None:
        """Check if all source files exist and are accessible."""
        if not self.manifest:
            raise PreflightCheckError(
                "Manifest not loaded",
                check_name="source_files",
                suggestion="Run manifest validation first"
            )

        for source in self.manifest.sources:
            if not source.enabled:
                continue

            # Only check local files
            if source.fetch.type == FetchType.LOCAL:
                paths = []
                if source.fetch.path:
                    paths.append(source.fetch.path)
                if source.fetch.paths:
                    paths.extend(source.fetch.paths)

                for path_str in paths:
                    path = Path(path_str).resolve()
                    if not path.exists():
                        raise GraphMeshFileNotFoundError(
                            f"Source file not found for '{source.id}': {path}",
                            file_path=str(path),
                            resource_type="source_file"
                        )
                    if not path.is_file():
                        raise PreflightCheckError(
                            f"Source path is not a file for '{source.id}': {path}",
                            check_name="source_files"
                        )
                    # Check read permissions
                    if not self._check_file_readable(path):
                        raise ResourceAccessError(
                            f"Cannot read source file for '{source.id}': {path}",
                            resource_path=str(path),
                            operation="read"
                        )

    def check_workdir(self) -> None:
        """Check working directory access."""
        try:
            # Try to create workdir if it doesn't exist
            self.workdir.mkdir(parents=True, exist_ok=True)

            # Test write access
            test_file = self.workdir / ".preflight_test"
            try:
                test_file.write_text("test")
                test_file.unlink()
            except Exception as e:
                raise ResourceAccessError(
                    f"Cannot write to working directory: {self.workdir}",
                    resource_path=str(self.workdir),
                    operation="write"
                )

        except Exception as e:
            if isinstance(e, ResourceAccessError):
                raise
            raise PreflightCheckError(
                f"Working directory check failed: {str(e)}",
                check_name="workdir",
                suggestion="Ensure the directory path is valid and writable"
            )

    def check_docker(self) -> None:
        """Check if Docker is available and running."""
        try:
            import docker
            client = docker.from_env()
            # Try to ping Docker daemon
            client.ping()
            # Close the client
            client.close()
        except ImportError:
            self.warnings.append(
                "Docker Python library not installed. Matchers requiring Docker may fail."
            )
        except Exception as e:
            # Docker not available is a warning, not an error
            # Some pipelines may not need Docker
            self.warnings.append(
                f"Docker not available: {str(e)}. Matchers requiring Docker (e.g., BERTMap) will fail."
            )

    def check_python_dependencies(self) -> None:
        """Check if required Python dependencies are available."""
        required_packages = {
            'rdflib': 'RDF graph manipulation',
            'pydantic': 'Data validation',
            'pyyaml': 'YAML parsing',
            'structlog': 'Structured logging',
        }

        missing = []
        for package, purpose in required_packages.items():
            try:
                __import__(package)
            except ImportError:
                missing.append(f"{package} ({purpose})")

        if missing:
            raise PreflightCheckError(
                f"Missing required Python packages: {', '.join(missing)}",
                check_name="python_dependencies",
                suggestion="Run: pip install -r requirements.txt"
            )

    def check_converter_availability(self, converter_type: str) -> bool:
        """Check if a specific converter is available.

        Args:
            converter_type: Type of converter (xsd, json, etc.)

        Returns:
            True if converter is available
        """
        converter_packages = {
            'xsd': 'xmlschema',
            'json': 'json',  # Built-in
        }

        package = converter_packages.get(converter_type)
        if not package:
            return False

        try:
            __import__(package)
            return True
        except ImportError:
            return False

    def check_matcher_availability(self, matcher_name: str) -> bool:
        """Check if a specific matcher is available.

        Args:
            matcher_name: Name of the matcher

        Returns:
            True if matcher is available
        """
        # This is a simplified check
        # In practice, you'd check Docker images, executables, etc.

        # For now, just check if it's a known matcher
        known_matchers = {'LogMap', 'AML', 'BERTMap'}
        return matcher_name in known_matchers

    @staticmethod
    def _check_file_readable(path: Path) -> bool:
        """Check if file is readable.

        Args:
            path: Path to file

        Returns:
            True if file is readable
        """
        try:
            with open(path, 'r') as f:
                f.read(1)
            return True
        except Exception:
            return False


def validate_manifest_file(manifest_path: Path, strict: bool = True) -> PipelineManifest:
    """Validate a manifest file and return parsed manifest.

    Args:
        manifest_path: Path to manifest file
        strict: If True, raise on validation errors; if False, log warnings

    Returns:
        Validated PipelineManifest

    Raises:
        ManifestValidationError: If validation fails
    """
    validator = PreflightValidator(manifest_path)
    success, errors, warnings = validator.validate_all(check_docker=False)

    if not success:
        if strict:
            raise ManifestValidationError(
                "Manifest validation failed",
                manifest_path=str(manifest_path),
                errors=errors
            )
        else:
            for error in errors:
                print(f"WARNING: {error}", file=sys.stderr)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    return validator.manifest


def run_preflight_checks(
    manifest_path: Path,
    workdir: Optional[Path] = None,
    check_docker: bool = True,
    strict: bool = True
) -> Dict[str, Any]:
    """Run all pre-flight checks and return results.

    Args:
        manifest_path: Path to pipeline manifest
        workdir: Working directory for artifacts
        check_docker: Whether to check Docker availability
        strict: If True, raise on check failures

    Returns:
        Dictionary with check results

    Raises:
        PreflightCheckError: If checks fail and strict=True
    """
    validator = PreflightValidator(manifest_path, workdir)
    success, errors, warnings = validator.validate_all(check_docker=check_docker)

    results = {
        "success": success,
        "errors": errors,
        "warnings": warnings,
        "manifest": validator.manifest.model_dump() if validator.manifest else None,
    }

    if not success and strict:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        raise PreflightCheckError(
            f"Pre-flight checks failed:\n{error_msg}",
            check_name="preflight",
            suggestion="Fix the errors above and try again"
        )

    return results
