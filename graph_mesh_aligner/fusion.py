"""Mapping fusion system for combining alignments from multiple matchers."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass
class Mapping:
    """Represents a single entity mapping."""

    subject_id: str
    object_id: str
    predicate_id: str
    confidence: float
    matcher_name: str
    mapping_justification: str | None = None

    def get_key(self) -> tuple[str, str, str]:
        """Return a unique key for this mapping."""
        return (self.subject_id, self.object_id, self.predicate_id)


@dataclass
class FusedMapping:
    """Represents a fused mapping from multiple matchers."""

    subject_id: str
    object_id: str
    predicate_id: str
    confidences: Dict[str, float]  # matcher_name -> confidence
    supporting_matchers: List[str]
    consensus_confidence: float
    mapping_justification: str | None = None

    @property
    def support_count(self) -> int:
        """Number of matchers that support this mapping."""
        return len(self.supporting_matchers)

    def get_key(self) -> tuple[str, str, str]:
        """Return a unique key for this mapping."""
        return (self.subject_id, self.object_id, self.predicate_id)


def load_sssom_mappings(file_path: Path, matcher_name: str) -> List[Mapping]:
    """Load mappings from SSSOM TSV file.

    Args:
        file_path: Path to SSSOM TSV file
        matcher_name: Name of the matcher that produced this file

    Returns:
        List of Mapping objects
    """
    if not file_path.exists():
        LOGGER.warning(f"Mapping file not found: {file_path}")
        return []

    try:
        # SSSOM format uses TSV with specific column names
        df = pd.read_csv(file_path, sep="\t", comment="#")

        mappings = []
        for _, row in df.iterrows():
            # Handle different SSSOM column naming conventions
            subject_id = row.get("subject_id") or row.get("subject")
            object_id = row.get("object_id") or row.get("object")
            predicate_id = row.get("predicate_id") or row.get("predicate", "skos:closeMatch")
            confidence = float(row.get("confidence") or row.get("similarity", 1.0))
            justification = row.get("mapping_justification")

            if subject_id and object_id:
                mappings.append(
                    Mapping(
                        subject_id=str(subject_id),
                        object_id=str(object_id),
                        predicate_id=str(predicate_id),
                        confidence=confidence,
                        matcher_name=matcher_name,
                        mapping_justification=justification,
                    )
                )

        LOGGER.info(f"Loaded {len(mappings)} mappings from {matcher_name}")
        return mappings

    except Exception as exc:
        LOGGER.error(f"Error loading SSSOM file {file_path}: {exc}")
        return []


def fuse_mappings(
    mapping_files: Dict[str, Path],
    min_confidence: float = 0.0,
) -> List[FusedMapping]:
    """Fuse mappings from multiple matchers.

    Args:
        mapping_files: Dictionary of matcher_name -> mapping_file_path
        min_confidence: Minimum confidence threshold for individual mappings

    Returns:
        List of fused mappings with consensus information
    """
    LOGGER.info(f"Fusing mappings from {len(mapping_files)} matchers")

    # Load all mappings
    all_mappings: List[Mapping] = []
    for matcher_name, file_path in mapping_files.items():
        mappings = load_sssom_mappings(file_path, matcher_name)
        # Filter by minimum confidence
        mappings = [m for m in mappings if m.confidence >= min_confidence]
        all_mappings.extend(mappings)

    LOGGER.info(f"Total mappings loaded: {len(all_mappings)}")

    # Group mappings by their key (subject, object, predicate)
    mapping_groups: Dict[tuple, List[Mapping]] = defaultdict(list)
    for mapping in all_mappings:
        mapping_groups[mapping.get_key()].append(mapping)

    # Create fused mappings
    fused_mappings: List[FusedMapping] = []
    for key, mappings in mapping_groups.items():
        subject_id, object_id, predicate_id = key

        # Collect confidence scores from each matcher
        confidences: Dict[str, float] = {}
        supporting_matchers: List[str] = []

        for mapping in mappings:
            if mapping.matcher_name not in confidences:
                supporting_matchers.append(mapping.matcher_name)
            # Keep the highest confidence if multiple mappings from same matcher
            confidences[mapping.matcher_name] = max(
                confidences.get(mapping.matcher_name, 0.0), mapping.confidence
            )

        # Calculate consensus confidence (average of all supporting matchers)
        consensus_confidence = sum(confidences.values()) / len(confidences)

        # Collect justifications
        justifications = [m.mapping_justification for m in mappings if m.mapping_justification]
        combined_justification = "; ".join(justifications) if justifications else None

        fused_mappings.append(
            FusedMapping(
                subject_id=subject_id,
                object_id=object_id,
                predicate_id=predicate_id,
                confidences=confidences,
                supporting_matchers=supporting_matchers,
                consensus_confidence=consensus_confidence,
                mapping_justification=combined_justification,
            )
        )

    LOGGER.info(f"Created {len(fused_mappings)} fused mappings")
    return fused_mappings


def filter_by_support(
    fused_mappings: List[FusedMapping],
    min_support: int = 2,
) -> List[FusedMapping]:
    """Filter fused mappings by minimum number of supporting matchers.

    Args:
        fused_mappings: List of fused mappings
        min_support: Minimum number of matchers that must agree

    Returns:
        Filtered list of mappings
    """
    filtered = [m for m in fused_mappings if m.support_count >= min_support]
    LOGGER.info(
        f"Filtered by support (min={min_support}): "
        f"{len(filtered)}/{len(fused_mappings)} mappings retained"
    )
    return filtered


def filter_by_consensus_confidence(
    fused_mappings: List[FusedMapping],
    min_consensus: float = 0.5,
) -> List[FusedMapping]:
    """Filter fused mappings by consensus confidence threshold.

    Args:
        fused_mappings: List of fused mappings
        min_consensus: Minimum consensus confidence (0.0 to 1.0)

    Returns:
        Filtered list of mappings
    """
    filtered = [m for m in fused_mappings if m.consensus_confidence >= min_consensus]
    LOGGER.info(
        f"Filtered by consensus confidence (min={min_consensus:.2f}): "
        f"{len(filtered)}/{len(fused_mappings)} mappings retained"
    )
    return filtered


def export_fused_mappings(
    fused_mappings: List[FusedMapping],
    output_path: Path,
    include_metadata: bool = True,
) -> Path:
    """Export fused mappings to SSSOM TSV format.

    Args:
        fused_mappings: List of fused mappings
        output_path: Path to output SSSOM file
        include_metadata: Whether to include fusion metadata in comments

    Returns:
        Path to the exported file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create DataFrame
    rows = []
    for mapping in fused_mappings:
        row = {
            "subject_id": mapping.subject_id,
            "predicate_id": mapping.predicate_id,
            "object_id": mapping.object_id,
            "confidence": mapping.consensus_confidence,
            "mapping_tool": "graph-mesh-fusion",
            "mapping_justification": mapping.mapping_justification or "ensemble_fusion",
            "comment": f"Support: {mapping.support_count} matchers: {', '.join(mapping.supporting_matchers)}",
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Write with metadata header
    with open(output_path, "w") as f:
        if include_metadata:
            f.write("# Fused mapping set from multiple ontology matchers\n")
            f.write(f"# Total mappings: {len(fused_mappings)}\n")
            f.write("# Fusion method: ensemble consensus\n")
            f.write("#\n")

        # Write DataFrame as TSV
        df.to_csv(f, sep="\t", index=False)

    LOGGER.info(f"Exported {len(fused_mappings)} fused mappings to {output_path}")
    return output_path


def identify_conflicts(fused_mappings: List[FusedMapping]) -> Dict[str, List[FusedMapping]]:
    """Identify conflicting mappings (same subject mapped to different objects).

    Args:
        fused_mappings: List of fused mappings

    Returns:
        Dictionary mapping subject_id to list of conflicting mappings
    """
    subject_mappings: Dict[str, List[FusedMapping]] = defaultdict(list)

    for mapping in fused_mappings:
        subject_mappings[mapping.subject_id].append(mapping)

    # Filter to only subjects with multiple different object mappings
    conflicts = {
        subject: mappings
        for subject, mappings in subject_mappings.items()
        if len(set(m.object_id for m in mappings)) > 1
    }

    if conflicts:
        LOGGER.warning(f"Found {len(conflicts)} subjects with conflicting mappings")

    return conflicts
