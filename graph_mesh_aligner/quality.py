"""Mapping quality metrics and conflict resolution strategies."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

from graph_mesh_aligner.fusion import FusedMapping

LOGGER = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality metrics for a set of mappings."""

    total_mappings: int
    unique_subjects: int
    unique_objects: int
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    avg_support_count: float
    min_support_count: int
    max_support_count: int
    confidence_distribution: Dict[str, int] = field(default_factory=dict)  # Range -> count
    support_distribution: Dict[int, int] = field(default_factory=dict)  # Support -> count
    predicate_distribution: Dict[str, int] = field(default_factory=dict)  # Predicate -> count


@dataclass
class ConflictReport:
    """Report of mapping conflicts."""

    total_conflicts: int
    conflicting_subjects: List[str]
    conflict_details: Dict[str, List[FusedMapping]]  # subject_id -> conflicting mappings
    resolution_strategy: str
    resolved_mappings: List[FusedMapping]


def calculate_quality_metrics(mappings: List[FusedMapping]) -> QualityMetrics:
    """Calculate comprehensive quality metrics for a set of mappings.

    Args:
        mappings: List of fused mappings

    Returns:
        QualityMetrics object with detailed statistics
    """
    if not mappings:
        LOGGER.warning("No mappings provided for quality calculation")
        return QualityMetrics(
            total_mappings=0,
            unique_subjects=0,
            unique_objects=0,
            avg_confidence=0.0,
            min_confidence=0.0,
            max_confidence=0.0,
            avg_support_count=0.0,
            min_support_count=0,
            max_support_count=0,
        )

    # Basic counts
    total_mappings = len(mappings)
    unique_subjects = len(set(m.subject_id for m in mappings))
    unique_objects = len(set(m.object_id for m in mappings))

    # Confidence statistics
    confidences = [m.consensus_confidence for m in mappings]
    avg_confidence = sum(confidences) / len(confidences)
    min_confidence = min(confidences)
    max_confidence = max(confidences)

    # Support statistics
    support_counts = [m.support_count for m in mappings]
    avg_support_count = sum(support_counts) / len(support_counts)
    min_support_count = min(support_counts)
    max_support_count = max(support_counts)

    # Confidence distribution (bins: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
    confidence_distribution = {
        "0.0-0.2": sum(1 for c in confidences if 0.0 <= c < 0.2),
        "0.2-0.4": sum(1 for c in confidences if 0.2 <= c < 0.4),
        "0.4-0.6": sum(1 for c in confidences if 0.4 <= c < 0.6),
        "0.6-0.8": sum(1 for c in confidences if 0.6 <= c < 0.8),
        "0.8-1.0": sum(1 for c in confidences if 0.8 <= c <= 1.0),
    }

    # Support distribution
    support_distribution = {}
    for count in support_counts:
        support_distribution[count] = support_distribution.get(count, 0) + 1

    # Predicate distribution
    predicate_distribution = {}
    for mapping in mappings:
        pred = mapping.predicate_id
        predicate_distribution[pred] = predicate_distribution.get(pred, 0) + 1

    metrics = QualityMetrics(
        total_mappings=total_mappings,
        unique_subjects=unique_subjects,
        unique_objects=unique_objects,
        avg_confidence=avg_confidence,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        avg_support_count=avg_support_count,
        min_support_count=min_support_count,
        max_support_count=max_support_count,
        confidence_distribution=confidence_distribution,
        support_distribution=support_distribution,
        predicate_distribution=predicate_distribution,
    )

    LOGGER.info(f"Quality metrics calculated for {total_mappings} mappings")
    return metrics


def identify_conflicts(mappings: List[FusedMapping]) -> Dict[str, List[FusedMapping]]:
    """Identify subjects with conflicting object mappings.

    Args:
        mappings: List of fused mappings

    Returns:
        Dictionary of subject_id -> list of conflicting mappings
    """
    subject_mappings: Dict[str, List[FusedMapping]] = defaultdict(list)

    for mapping in mappings:
        subject_mappings[mapping.subject_id].append(mapping)

    # Filter to only subjects with multiple different objects
    conflicts = {
        subject: mappings_list
        for subject, mappings_list in subject_mappings.items()
        if len(set(m.object_id for m in mappings_list)) > 1
    }

    if conflicts:
        LOGGER.warning(f"Found {len(conflicts)} subjects with conflicting mappings")
    else:
        LOGGER.info("No conflicts detected")

    return conflicts


def resolve_conflicts_by_confidence(
    conflicts: Dict[str, List[FusedMapping]]
) -> List[FusedMapping]:
    """Resolve conflicts by selecting mapping with highest consensus confidence.

    Args:
        conflicts: Dictionary of subject_id -> conflicting mappings

    Returns:
        List of resolved mappings (one per subject)
    """
    resolved = []

    for subject, mappings_list in conflicts.items():
        # Select mapping with highest consensus confidence
        best_mapping = max(mappings_list, key=lambda m: m.consensus_confidence)
        resolved.append(best_mapping)
        LOGGER.debug(
            f"Resolved conflict for {subject}: "
            f"selected {best_mapping.object_id} (confidence: {best_mapping.consensus_confidence:.3f})"
        )

    LOGGER.info(f"Resolved {len(resolved)} conflicts by confidence")
    return resolved


def resolve_conflicts_by_support(
    conflicts: Dict[str, List[FusedMapping]]
) -> List[FusedMapping]:
    """Resolve conflicts by selecting mapping with most supporting matchers.

    If there's a tie, use consensus confidence as tiebreaker.

    Args:
        conflicts: Dictionary of subject_id -> conflicting mappings

    Returns:
        List of resolved mappings (one per subject)
    """
    resolved = []

    for subject, mappings_list in conflicts.items():
        # Sort by support count (descending), then by confidence (descending)
        sorted_mappings = sorted(
            mappings_list,
            key=lambda m: (m.support_count, m.consensus_confidence),
            reverse=True,
        )
        best_mapping = sorted_mappings[0]
        resolved.append(best_mapping)
        LOGGER.debug(
            f"Resolved conflict for {subject}: "
            f"selected {best_mapping.object_id} (support: {best_mapping.support_count})"
        )

    LOGGER.info(f"Resolved {len(resolved)} conflicts by support count")
    return resolved


def resolve_conflicts_by_specificity(
    conflicts: Dict[str, List[FusedMapping]]
) -> List[FusedMapping]:
    """Resolve conflicts by preferring more specific predicates.

    Predicate hierarchy: equivalentClass > closeMatch > relatedMatch

    Args:
        conflicts: Dictionary of subject_id -> conflicting mappings

    Returns:
        List of resolved mappings (one per subject)
    """
    # Define predicate specificity ranking (higher is more specific)
    predicate_rank = {
        "owl:equivalentClass": 3,
        "skos:exactMatch": 3,
        "skos:closeMatch": 2,
        "skos:relatedMatch": 1,
        "skos:broadMatch": 1,
        "skos:narrowMatch": 1,
    }

    resolved = []

    for subject, mappings_list in conflicts.items():
        # Sort by predicate specificity, then confidence
        sorted_mappings = sorted(
            mappings_list,
            key=lambda m: (
                predicate_rank.get(m.predicate_id, 0),
                m.consensus_confidence,
            ),
            reverse=True,
        )
        best_mapping = sorted_mappings[0]
        resolved.append(best_mapping)
        LOGGER.debug(
            f"Resolved conflict for {subject}: "
            f"selected {best_mapping.object_id} (predicate: {best_mapping.predicate_id})"
        )

    LOGGER.info(f"Resolved {len(resolved)} conflicts by predicate specificity")
    return resolved


def resolve_conflicts_keep_all(
    conflicts: Dict[str, List[FusedMapping]]
) -> List[FusedMapping]:
    """Keep all conflicting mappings (no resolution).

    Args:
        conflicts: Dictionary of subject_id -> conflicting mappings

    Returns:
        List of all conflicting mappings
    """
    all_mappings = []
    for mappings_list in conflicts.values():
        all_mappings.extend(mappings_list)

    LOGGER.info(f"Kept all {len(all_mappings)} conflicting mappings (no resolution)")
    return all_mappings


def resolve_conflicts(
    mappings: List[FusedMapping],
    strategy: str = "confidence",
) -> ConflictReport:
    """Resolve conflicts in mappings using specified strategy.

    Args:
        mappings: List of fused mappings
        strategy: Resolution strategy: 'confidence', 'support', 'specificity', 'keep_all'

    Returns:
        ConflictReport with resolution details
    """
    LOGGER.info(f"Resolving conflicts using '{strategy}' strategy")

    # Identify conflicts
    conflicts = identify_conflicts(mappings)

    if not conflicts:
        return ConflictReport(
            total_conflicts=0,
            conflicting_subjects=[],
            conflict_details={},
            resolution_strategy=strategy,
            resolved_mappings=mappings,  # No conflicts, return all mappings
        )

    # Apply resolution strategy
    if strategy == "confidence":
        resolved = resolve_conflicts_by_confidence(conflicts)
    elif strategy == "support":
        resolved = resolve_conflicts_by_support(conflicts)
    elif strategy == "specificity":
        resolved = resolve_conflicts_by_specificity(conflicts)
    elif strategy == "keep_all":
        resolved = resolve_conflicts_keep_all(conflicts)
    else:
        LOGGER.warning(f"Unknown strategy '{strategy}', using 'confidence'")
        resolved = resolve_conflicts_by_confidence(conflicts)

    # Combine resolved mappings with non-conflicting ones
    conflict_subjects = set(conflicts.keys())
    non_conflicting = [m for m in mappings if m.subject_id not in conflict_subjects]
    all_resolved = non_conflicting + resolved

    return ConflictReport(
        total_conflicts=len(conflicts),
        conflicting_subjects=sorted(conflicts.keys()),
        conflict_details=conflicts,
        resolution_strategy=strategy,
        resolved_mappings=all_resolved,
    )


def filter_by_confidence(
    mappings: List[FusedMapping],
    min_confidence: float,
) -> List[FusedMapping]:
    """Filter mappings by minimum consensus confidence.

    Args:
        mappings: List of fused mappings
        min_confidence: Minimum consensus confidence threshold (0.0 to 1.0)

    Returns:
        Filtered mappings
    """
    filtered = [m for m in mappings if m.consensus_confidence >= min_confidence]
    LOGGER.info(
        f"Filtered by confidence (>= {min_confidence:.2f}): "
        f"{len(filtered)}/{len(mappings)} mappings retained"
    )
    return filtered


def filter_by_support(
    mappings: List[FusedMapping],
    min_support: int,
) -> List[FusedMapping]:
    """Filter mappings by minimum number of supporting matchers.

    Args:
        mappings: List of fused mappings
        min_support: Minimum number of supporting matchers

    Returns:
        Filtered mappings
    """
    filtered = [m for m in mappings if m.support_count >= min_support]
    LOGGER.info(
        f"Filtered by support (>= {min_support}): "
        f"{len(filtered)}/{len(mappings)} mappings retained"
    )
    return filtered


def generate_quality_report(
    mappings: List[FusedMapping],
    output_path: Path,
    conflict_report: ConflictReport | None = None,
) -> Path:
    """Generate a comprehensive quality report.

    Args:
        mappings: List of fused mappings
        output_path: Path to save the report
        conflict_report: Optional conflict resolution report

    Returns:
        Path to the generated report
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = calculate_quality_metrics(mappings)

    with open(output_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("MAPPING QUALITY REPORT\n")
        f.write("=" * 80 + "\n\n")

        # Overview
        f.write("OVERVIEW\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Mappings:       {metrics.total_mappings}\n")
        f.write(f"Unique Subjects:      {metrics.unique_subjects}\n")
        f.write(f"Unique Objects:       {metrics.unique_objects}\n")
        f.write(f"Coverage Ratio:       {metrics.total_mappings / max(metrics.unique_subjects, 1):.2f}\n\n")

        # Confidence Statistics
        f.write("CONFIDENCE STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Average Confidence:   {metrics.avg_confidence:.3f}\n")
        f.write(f"Min Confidence:       {metrics.min_confidence:.3f}\n")
        f.write(f"Max Confidence:       {metrics.max_confidence:.3f}\n\n")

        f.write("Confidence Distribution:\n")
        for range_str, count in sorted(metrics.confidence_distribution.items()):
            pct = (count / metrics.total_mappings * 100) if metrics.total_mappings > 0 else 0
            f.write(f"  {range_str}: {count:5d} ({pct:5.1f}%)\n")
        f.write("\n")

        # Support Statistics
        f.write("SUPPORT STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Average Support:      {metrics.avg_support_count:.2f}\n")
        f.write(f"Min Support:          {metrics.min_support_count}\n")
        f.write(f"Max Support:          {metrics.max_support_count}\n\n")

        f.write("Support Distribution:\n")
        for support, count in sorted(metrics.support_distribution.items()):
            pct = (count / metrics.total_mappings * 100) if metrics.total_mappings > 0 else 0
            f.write(f"  {support} matchers: {count:5d} ({pct:5.1f}%)\n")
        f.write("\n")

        # Predicate Distribution
        f.write("PREDICATE DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        for predicate, count in sorted(
            metrics.predicate_distribution.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (count / metrics.total_mappings * 100) if metrics.total_mappings > 0 else 0
            f.write(f"  {predicate}: {count:5d} ({pct:5.1f}%)\n")
        f.write("\n")

        # Conflict Information
        if conflict_report:
            f.write("CONFLICT RESOLUTION\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Conflicts:      {conflict_report.total_conflicts}\n")
            f.write(f"Resolution Strategy:  {conflict_report.resolution_strategy}\n")
            f.write(f"Resolved Mappings:    {len(conflict_report.resolved_mappings)}\n\n")

            if conflict_report.conflicting_subjects:
                f.write("Sample Conflicting Subjects (first 10):\n")
                for subject in conflict_report.conflicting_subjects[:10]:
                    f.write(f"  - {subject}\n")
                if len(conflict_report.conflicting_subjects) > 10:
                    f.write(f"  ... and {len(conflict_report.conflicting_subjects) - 10} more\n")
                f.write("\n")

        f.write("=" * 80 + "\n")

    LOGGER.info(f"Quality report generated: {output_path}")
    return output_path


def compare_with_reference(
    mappings: List[FusedMapping],
    reference_mappings: List[FusedMapping],
) -> Dict[str, float]:
    """Compare mappings with a reference (gold standard) set.

    Args:
        mappings: Mappings to evaluate
        reference_mappings: Reference/gold standard mappings

    Returns:
        Dictionary with precision, recall, and F1 scores
    """
    mapping_keys = {m.get_key() for m in mappings}
    reference_keys = {m.get_key() for m in reference_mappings}

    true_positives = len(mapping_keys & reference_keys)
    false_positives = len(mapping_keys - reference_keys)
    false_negatives = len(reference_keys - mapping_keys)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    LOGGER.info(f"Comparison with reference: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}")

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }
