"""Alignment utilities for Graph-Mesh."""

from .matchers import (
    AlignmentMatcher,
    ContainerMatcher,
    DEFAULT_MATCHERS,
    MatcherResult,
    run_alignment,
    run_alignment_async,
    run_alignment_parallel,
)
from .fusion import (
    Mapping,
    FusedMapping,
    load_sssom_mappings,
    fuse_mappings,
    filter_by_support,
    filter_by_consensus_confidence,
    export_fused_mappings,
    identify_conflicts,
)
from .voting import (
    VotingStrategy,
    VotingConfig,
    VotingResult,
    vote,
    calculate_matcher_agreement,
    suggest_matcher_weights,
)
from .quality import (
    QualityMetrics,
    ConflictReport,
    calculate_quality_metrics,
    resolve_conflicts,
    filter_by_confidence,
    generate_quality_report,
    compare_with_reference,
)

__all__ = [
    # Matchers
    "AlignmentMatcher",
    "ContainerMatcher",
    "DEFAULT_MATCHERS",
    "MatcherResult",
    "run_alignment",
    "run_alignment_async",
    "run_alignment_parallel",
    # Fusion
    "Mapping",
    "FusedMapping",
    "load_sssom_mappings",
    "fuse_mappings",
    "filter_by_support",
    "filter_by_consensus_confidence",
    "export_fused_mappings",
    "identify_conflicts",
    # Voting
    "VotingStrategy",
    "VotingConfig",
    "VotingResult",
    "vote",
    "calculate_matcher_agreement",
    "suggest_matcher_weights",
    # Quality
    "QualityMetrics",
    "ConflictReport",
    "calculate_quality_metrics",
    "resolve_conflicts",
    "filter_by_confidence",
    "generate_quality_report",
    "compare_with_reference",
]
