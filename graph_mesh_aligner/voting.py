"""Ensemble voting mechanisms for ontology alignment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from graph_mesh_aligner.fusion import FusedMapping

LOGGER = logging.getLogger(__name__)


class VotingStrategy(Enum):
    """Available voting strategies for ensemble alignment."""

    MAJORITY = "majority"  # Mapping accepted if majority of matchers agree
    UNANIMOUS = "unanimous"  # Mapping accepted only if all matchers agree
    WEIGHTED = "weighted"  # Weighted voting based on matcher performance
    THRESHOLD = "threshold"  # Mapping accepted if support exceeds threshold
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by confidence scores


@dataclass
class VotingConfig:
    """Configuration for voting strategy."""

    strategy: VotingStrategy = VotingStrategy.MAJORITY
    min_support_count: int = 2  # Minimum number of supporting matchers
    min_support_ratio: float = 0.5  # Minimum ratio of matchers (0.0 to 1.0)
    min_confidence: float = 0.0  # Minimum individual confidence
    matcher_weights: Dict[str, float] | None = None  # Custom weights per matcher


@dataclass
class VotingResult:
    """Result of voting process."""

    accepted_mappings: List[FusedMapping]
    rejected_mappings: List[FusedMapping]
    total_matchers: int
    voting_strategy: VotingStrategy


def apply_majority_voting(
    fused_mappings: List[FusedMapping],
    total_matchers: int,
) -> List[FusedMapping]:
    """Accept mappings supported by majority of matchers.

    Args:
        fused_mappings: List of fused mappings
        total_matchers: Total number of matchers in the ensemble

    Returns:
        Mappings supported by majority
    """
    majority_threshold = (total_matchers / 2.0) + 0.5  # More than half

    accepted = [m for m in fused_mappings if m.support_count >= majority_threshold]

    LOGGER.info(
        f"Majority voting: {len(accepted)}/{len(fused_mappings)} mappings accepted "
        f"(threshold: {majority_threshold:.1f}/{total_matchers})"
    )

    return accepted


def apply_unanimous_voting(
    fused_mappings: List[FusedMapping],
    total_matchers: int,
) -> List[FusedMapping]:
    """Accept only mappings supported by all matchers.

    Args:
        fused_mappings: List of fused mappings
        total_matchers: Total number of matchers in the ensemble

    Returns:
        Mappings supported by all matchers
    """
    accepted = [m for m in fused_mappings if m.support_count == total_matchers]

    LOGGER.info(
        f"Unanimous voting: {len(accepted)}/{len(fused_mappings)} mappings accepted "
        f"(all {total_matchers} matchers must agree)"
    )

    return accepted


def apply_weighted_voting(
    fused_mappings: List[FusedMapping],
    matcher_weights: Dict[str, float],
    threshold: float = 0.5,
) -> List[FusedMapping]:
    """Accept mappings based on weighted votes from matchers.

    Args:
        fused_mappings: List of fused mappings
        matcher_weights: Weight for each matcher (should sum to 1.0)
        threshold: Minimum weighted vote to accept mapping

    Returns:
        Mappings exceeding weighted threshold
    """
    accepted = []

    for mapping in fused_mappings:
        # Calculate weighted vote
        weighted_vote = sum(
            matcher_weights.get(matcher, 0.0) for matcher in mapping.supporting_matchers
        )

        if weighted_vote >= threshold:
            accepted.append(mapping)

    LOGGER.info(
        f"Weighted voting: {len(accepted)}/{len(fused_mappings)} mappings accepted "
        f"(threshold: {threshold:.2f})"
    )

    return accepted


def apply_confidence_weighted_voting(
    fused_mappings: List[FusedMapping],
    matcher_weights: Dict[str, float],
    threshold: float = 0.5,
) -> List[FusedMapping]:
    """Accept mappings based on weighted confidence scores.

    Combines matcher weights with confidence scores for each mapping.

    Args:
        fused_mappings: List of fused mappings
        matcher_weights: Weight for each matcher
        threshold: Minimum weighted confidence to accept mapping

    Returns:
        Mappings exceeding weighted confidence threshold
    """
    accepted = []

    for mapping in fused_mappings:
        # Calculate weighted confidence
        weighted_confidence = sum(
            matcher_weights.get(matcher, 0.0) * mapping.confidences.get(matcher, 0.0)
            for matcher in mapping.supporting_matchers
        )

        if weighted_confidence >= threshold:
            accepted.append(mapping)

    LOGGER.info(
        f"Confidence-weighted voting: {len(accepted)}/{len(fused_mappings)} mappings accepted "
        f"(threshold: {threshold:.2f})"
    )

    return accepted


def apply_threshold_voting(
    fused_mappings: List[FusedMapping],
    min_support_count: int,
    min_support_ratio: float,
    total_matchers: int,
) -> List[FusedMapping]:
    """Accept mappings based on support count and ratio thresholds.

    Args:
        fused_mappings: List of fused mappings
        min_support_count: Minimum absolute number of supporting matchers
        min_support_ratio: Minimum ratio of supporting matchers (0.0 to 1.0)
        total_matchers: Total number of matchers

    Returns:
        Mappings meeting both thresholds
    """
    min_count_from_ratio = int(min_support_ratio * total_matchers)
    effective_threshold = max(min_support_count, min_count_from_ratio)

    accepted = [m for m in fused_mappings if m.support_count >= effective_threshold]

    LOGGER.info(
        f"Threshold voting: {len(accepted)}/{len(fused_mappings)} mappings accepted "
        f"(threshold: {effective_threshold}/{total_matchers})"
    )

    return accepted


def vote(
    fused_mappings: List[FusedMapping],
    config: VotingConfig,
    total_matchers: int,
) -> VotingResult:
    """Apply voting strategy to select high-quality mappings.

    Args:
        fused_mappings: List of fused mappings
        config: Voting configuration
        total_matchers: Total number of matchers in ensemble

    Returns:
        VotingResult with accepted and rejected mappings
    """
    LOGGER.info(f"Applying {config.strategy.value} voting strategy")

    # Pre-filter by minimum confidence if specified
    if config.min_confidence > 0:
        pre_filtered = [
            m for m in fused_mappings if m.consensus_confidence >= config.min_confidence
        ]
        LOGGER.info(
            f"Pre-filtered by confidence (>= {config.min_confidence:.2f}): "
            f"{len(pre_filtered)}/{len(fused_mappings)}"
        )
        fused_mappings = pre_filtered

    # Apply voting strategy
    if config.strategy == VotingStrategy.MAJORITY:
        accepted = apply_majority_voting(fused_mappings, total_matchers)

    elif config.strategy == VotingStrategy.UNANIMOUS:
        accepted = apply_unanimous_voting(fused_mappings, total_matchers)

    elif config.strategy == VotingStrategy.WEIGHTED:
        if not config.matcher_weights:
            LOGGER.warning("No matcher weights provided, using equal weights")
            config.matcher_weights = {f"matcher_{i}": 1.0 / total_matchers for i in range(total_matchers)}

        accepted = apply_weighted_voting(
            fused_mappings,
            config.matcher_weights,
            threshold=config.min_support_ratio,
        )

    elif config.strategy == VotingStrategy.CONFIDENCE_WEIGHTED:
        if not config.matcher_weights:
            LOGGER.warning("No matcher weights provided, using equal weights")
            config.matcher_weights = {f"matcher_{i}": 1.0 / total_matchers for i in range(total_matchers)}

        accepted = apply_confidence_weighted_voting(
            fused_mappings,
            config.matcher_weights,
            threshold=config.min_support_ratio,
        )

    elif config.strategy == VotingStrategy.THRESHOLD:
        accepted = apply_threshold_voting(
            fused_mappings,
            config.min_support_count,
            config.min_support_ratio,
            total_matchers,
        )

    else:
        raise ValueError(f"Unknown voting strategy: {config.strategy}")

    # Determine rejected mappings
    accepted_keys = {m.get_key() for m in accepted}
    rejected = [m for m in fused_mappings if m.get_key() not in accepted_keys]

    return VotingResult(
        accepted_mappings=accepted,
        rejected_mappings=rejected,
        total_matchers=total_matchers,
        voting_strategy=config.strategy,
    )


def calculate_matcher_agreement(fused_mappings: List[FusedMapping]) -> Dict[tuple[str, str], float]:
    """Calculate pairwise agreement between matchers.

    Args:
        fused_mappings: List of fused mappings

    Returns:
        Dictionary of (matcher1, matcher2) -> agreement_score
    """
    # Collect all matcher names
    all_matchers = set()
    for mapping in fused_mappings:
        all_matchers.update(mapping.supporting_matchers)

    matcher_list = sorted(all_matchers)

    # Calculate agreement for each pair
    agreement_scores = {}

    for i, matcher1 in enumerate(matcher_list):
        for matcher2 in matcher_list[i + 1 :]:
            # Count mappings where both matchers agree
            both_agree = sum(
                1
                for m in fused_mappings
                if matcher1 in m.supporting_matchers and matcher2 in m.supporting_matchers
            )

            # Count mappings where at least one supports
            either_supports = sum(
                1
                for m in fused_mappings
                if matcher1 in m.supporting_matchers or matcher2 in m.supporting_matchers
            )

            # Calculate Jaccard similarity
            agreement = both_agree / either_supports if either_supports > 0 else 0.0
            agreement_scores[(matcher1, matcher2)] = agreement

    return agreement_scores


def suggest_matcher_weights(
    fused_mappings: List[FusedMapping],
    reference_mappings: List[FusedMapping] | None = None,
) -> Dict[str, float]:
    """Suggest optimal matcher weights based on performance.

    If reference mappings are provided, weights are based on precision.
    Otherwise, weights are based on pairwise agreement with other matchers.

    Args:
        fused_mappings: List of fused mappings
        reference_mappings: Optional reference (gold standard) mappings

    Returns:
        Dictionary of matcher_name -> suggested_weight
    """
    # Collect all matcher names
    all_matchers = set()
    for mapping in fused_mappings:
        all_matchers.update(mapping.supporting_matchers)

    if reference_mappings:
        # Weight by precision against reference
        reference_keys = {m.get_key() for m in reference_mappings}
        matcher_scores = {}

        for matcher in all_matchers:
            # Mappings from this matcher
            matcher_mappings = [
                m for m in fused_mappings if matcher in m.supporting_matchers
            ]
            matcher_keys = {m.get_key() for m in matcher_mappings}

            # Calculate precision
            true_positives = len(matcher_keys & reference_keys)
            precision = true_positives / len(matcher_keys) if matcher_keys else 0.0
            matcher_scores[matcher] = precision

    else:
        # Weight by average agreement with other matchers
        agreement_scores = calculate_matcher_agreement(fused_mappings)
        matcher_scores = {}

        for matcher in all_matchers:
            # Calculate average agreement with all other matchers
            agreements = [
                score
                for (m1, m2), score in agreement_scores.items()
                if m1 == matcher or m2 == matcher
            ]
            avg_agreement = sum(agreements) / len(agreements) if agreements else 0.0
            matcher_scores[matcher] = avg_agreement

    # Normalize to sum to 1.0
    total_score = sum(matcher_scores.values())
    if total_score > 0:
        matcher_weights = {
            matcher: score / total_score for matcher, score in matcher_scores.items()
        }
    else:
        # Equal weights if no scores
        matcher_weights = {matcher: 1.0 / len(all_matchers) for matcher in all_matchers}

    LOGGER.info("Suggested matcher weights:")
    for matcher, weight in sorted(matcher_weights.items(), key=lambda x: x[1], reverse=True):
        LOGGER.info(f"  {matcher}: {weight:.3f}")

    return matcher_weights
