"""Example demonstrating parallel alignment with voting and quality metrics.

This script shows how to use the new alignment engine features:
1. Parallel matcher execution (3x speedup)
2. Mapping fusion and voting
3. Conflict resolution
4. Quality metrics and reports
"""

import logging
from pathlib import Path

from graph_mesh_aligner import (
    DEFAULT_MATCHERS,
    run_alignment_parallel,
    fuse_mappings,
    vote,
    VotingConfig,
    VotingStrategy,
    resolve_conflicts,
    generate_quality_report,
    export_fused_mappings,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

LOGGER = logging.getLogger(__name__)


def main():
    """Run parallel alignment with fusion and quality analysis."""

    # Example paths (adjust these to your actual files)
    source_ontology = Path("artifacts/converted/sample-xsd.owl")
    target_ontology = Path("artifacts/meta/meta-ontology.ttl")
    output_dir = Path("artifacts/mappings/parallel-example")

    LOGGER.info("=" * 80)
    LOGGER.info("PARALLEL ALIGNMENT EXAMPLE")
    LOGGER.info("=" * 80)

    # Step 1: Run parallel alignment (3x faster than sequential)
    LOGGER.info("\n1. Running parallel alignment with all matchers...")
    results = run_alignment_parallel(
        matchers=DEFAULT_MATCHERS,
        source_ontology=source_ontology,
        target_ontology=target_ontology,
        output_dir=output_dir,
    )

    # Display results
    LOGGER.info("\nAlignment Results:")
    for result in results:
        status = "✓" if result.success else "✗"
        LOGGER.info(
            f"  {status} {result.matcher_name}: "
            f"{result.execution_time:.2f}s "
            f"{'(success)' if result.success else f'({result.error_message})'}"
        )

    # Calculate speedup (compared to sequential execution)
    total_time = max(r.execution_time for r in results)
    sequential_time = sum(r.execution_time for r in results)
    speedup = sequential_time / total_time if total_time > 0 else 0
    LOGGER.info(f"\nEstimated speedup: {speedup:.1f}x")

    # Step 2: Fuse mappings from successful matchers
    LOGGER.info("\n2. Fusing mappings from successful matchers...")

    mapping_files = {
        result.matcher_name: result.mapping_path
        for result in results
        if result.success
    }

    if not mapping_files:
        LOGGER.error("No successful matchers to fuse!")
        return

    fused_mappings = fuse_mappings(
        mapping_files=mapping_files,
        min_confidence=0.3,  # Filter out low-confidence mappings
    )

    LOGGER.info(f"Fused {len(fused_mappings)} unique mappings")

    # Step 3: Apply ensemble voting
    LOGGER.info("\n3. Applying ensemble voting...")

    # Try different voting strategies
    strategies = [
        ("Majority Voting", VotingConfig(
            strategy=VotingStrategy.MAJORITY,
            min_confidence=0.5,
        )),
        ("High Confidence Threshold", VotingConfig(
            strategy=VotingStrategy.THRESHOLD,
            min_support_count=2,
            min_support_ratio=0.6,
            min_confidence=0.7,
        )),
    ]

    best_mappings = fused_mappings
    for strategy_name, config in strategies:
        LOGGER.info(f"\n  Testing: {strategy_name}")
        voting_result = vote(
            fused_mappings=fused_mappings,
            config=config,
            total_matchers=len(mapping_files),
        )
        LOGGER.info(
            f"    Accepted: {len(voting_result.accepted_mappings)} mappings"
        )

        # Use the first strategy for downstream processing
        if strategy_name == strategies[0][0]:
            best_mappings = voting_result.accepted_mappings

    # Step 4: Resolve conflicts
    LOGGER.info("\n4. Resolving conflicts...")

    conflict_report = resolve_conflicts(
        mappings=best_mappings,
        strategy="confidence",  # Use highest confidence to resolve
    )

    LOGGER.info(f"  Found {conflict_report.total_conflicts} conflicts")
    LOGGER.info(f"  Resolved to {len(conflict_report.resolved_mappings)} mappings")

    # Step 5: Generate quality report
    LOGGER.info("\n5. Generating quality report...")

    report_path = output_dir / "quality_report.txt"
    generate_quality_report(
        mappings=conflict_report.resolved_mappings,
        output_path=report_path,
        conflict_report=conflict_report,
    )

    LOGGER.info(f"  Quality report saved to: {report_path}")

    # Step 6: Export final fused mappings
    LOGGER.info("\n6. Exporting final mappings...")

    final_output = output_dir / "fused_mappings.sssom.tsv"
    export_fused_mappings(
        fused_mappings=conflict_report.resolved_mappings,
        output_path=final_output,
        include_metadata=True,
    )

    LOGGER.info(f"  Final mappings exported to: {final_output}")

    # Summary
    LOGGER.info("\n" + "=" * 80)
    LOGGER.info("SUMMARY")
    LOGGER.info("=" * 80)
    LOGGER.info(f"Matchers executed: {len(results)} ({sum(1 for r in results if r.success)} successful)")
    LOGGER.info(f"Speedup achieved: {speedup:.1f}x")
    LOGGER.info(f"Total unique mappings: {len(fused_mappings)}")
    LOGGER.info(f"After voting: {len(best_mappings)}")
    LOGGER.info(f"After conflict resolution: {len(conflict_report.resolved_mappings)}")
    LOGGER.info(f"Conflicts resolved: {conflict_report.total_conflicts}")
    LOGGER.info("=" * 80)


if __name__ == "__main__":
    main()
