"""Utility helpers for the Graph-Mesh orchestrator."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

try:  # pragma: no cover - executed only when PyYAML is available.
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - offline fallback path.
    yaml = None  # type: ignore


def _parse_scalar(value: str) -> Any:
    """Parse a minimal subset of YAML scalars used in manifests."""
    value = value.strip()
    if not value:
        return ""

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]

    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]

    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None

    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _next_container_info(
    lines: Sequence[str], start: int, parent_indent: int
) -> Tuple[str, int]:
    """Infer whether the upcoming block represents a dict or list."""
    for idx in range(start, len(lines)):
        stripped = lines[idx].strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(lines[idx]) - len(lines[idx].lstrip(" "))
        if indent <= parent_indent:
            break
        container_type = "list" if stripped.startswith("- ") else "dict"
        return container_type, max(parent_indent + 1, indent - 1)
    return "dict", parent_indent + 1


def _minimal_yaml_load(text: str) -> Dict[str, Any]:
    """Fallback YAML loader supporting simple key/value manifests.

    This parser handles the nested dictionaries and inline lists that appear in
    the project manifests. It is intentionally lightweight so the orchestrator
    can run in sandboxed environments where PyYAML is unavailable.
    """

    lines = text.splitlines()
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, root)]

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Unexpected list item outside of a list context.")
            item_body = stripped[2:].strip()
            if not item_body:
                new_item: Any = {}
                parent.append(new_item)
                stack.append((indent, new_item))
                continue

            if ":" in item_body:
                key, value = item_body.split(":", 1)
                key = key.strip()
                value = value.strip()
                item_dict: Dict[str, Any] = {}
                parent.append(item_dict)
                stack.append((indent, item_dict))
                if value:
                    item_dict[key] = _parse_scalar(value)
                else:
                    container_type, child_indent = _next_container_info(
                        lines, idx + 1, indent
                    )
                    if container_type == "list":
                        child_container: Any = []
                    else:
                        child_container = {}
                    item_dict[key] = child_container
                    stack.append((child_indent, child_container))
                continue

            parent.append(_parse_scalar(item_body))
            continue

        if ":" not in stripped:
            raise ValueError(f"Invalid manifest line: {raw_line}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not isinstance(parent, dict):
            raise ValueError("Cannot assign a key/value pair inside a list item.")

        if value:
            parent[key] = _parse_scalar(value)
        else:
            container_type, child_indent = _next_container_info(lines, idx + 1, indent)
            if container_type == "list":
                next_container: Any = []
            else:
                next_container = {}
            parent[key] = next_container
            stack.append((child_indent, next_container))

    return root


def load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML manifest, falling back to a minimal parser when necessary."""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    if yaml is not None:
        return yaml.safe_load(text)  # type: ignore[union-attr]
    return _minimal_yaml_load(text)
