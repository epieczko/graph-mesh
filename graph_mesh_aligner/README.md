# Graph-Mesh Alignment Engine

High-performance ontology alignment system with parallel execution, ensemble voting, and quality metrics.

## Features

### 1. Parallel Matcher Execution (3x Speedup)

Execute multiple alignment matchers in parallel using asyncio for significant performance improvements.

```python
from graph_mesh_aligner import DEFAULT_MATCHERS, run_alignment_parallel

# Run all matchers in parallel
results = run_alignment_parallel(
    matchers=DEFAULT_MATCHERS,
    source_ontology=source_path,
    target_ontology=target_path,
    output_dir=output_dir,
)

# Check results
for result in results:
    print(f"{result.matcher_name}: {result.execution_time:.2f}s - {'✓' if result.success else '✗'}")
```

**Key Features:**
- Asynchronous execution with `asyncio`
- Timeout handling (default: 5 minutes per matcher)
- Health checks before execution
- Detailed execution metrics (timing, errors)

### 2. Mapping Fusion

Combine and deduplicate mappings from multiple matchers.

```python
from graph_mesh_aligner import fuse_mappings

# Fuse mappings from multiple matchers
mapping_files = {
    "LogMap": Path("logmap.sssom.tsv"),
    "AML": Path("aml.sssom.tsv"),
    "BERTMap": Path("bertmap.sssom.tsv"),
}

fused = fuse_mappings(
    mapping_files=mapping_files,
    min_confidence=0.5,  # Filter low-confidence mappings
)

# Each fused mapping includes:
# - consensus_confidence: Average confidence across matchers
# - supporting_matchers: List of matchers that agree
# - support_count: Number of supporting matchers
```

### 3. Ensemble Voting

Multiple voting strategies to select high-quality mappings.

```python
from graph_mesh_aligner import vote, VotingConfig, VotingStrategy

# Majority voting
config = VotingConfig(
    strategy=VotingStrategy.MAJORITY,
    min_confidence=0.5,
)

result = vote(
    fused_mappings=fused,
    config=config,
    total_matchers=3,
)

print(f"Accepted: {len(result.accepted_mappings)} mappings")
```

**Available Strategies:**

| Strategy | Description |
|----------|-------------|
| `MAJORITY` | Accept if majority of matchers agree |
| `UNANIMOUS` | Accept only if all matchers agree |
| `WEIGHTED` | Weight votes by matcher performance |
| `CONFIDENCE_WEIGHTED` | Weight by confidence scores |
| `THRESHOLD` | Accept if support exceeds threshold |

### 4. Conflict Resolution

Resolve conflicting mappings (same subject → different objects).

```python
from graph_mesh_aligner import resolve_conflicts

report = resolve_conflicts(
    mappings=fused_mappings,
    strategy="confidence",  # or "support", "specificity", "keep_all"
)

print(f"Conflicts: {report.total_conflicts}")
print(f"Resolved: {len(report.resolved_mappings)}")
```

**Resolution Strategies:**

- `confidence`: Select mapping with highest consensus confidence
- `support`: Select mapping with most supporting matchers
- `specificity`: Prefer more specific predicates (e.g., exactMatch > closeMatch)
- `keep_all`: Keep all conflicting mappings

### 5. Quality Metrics & Reports

Generate comprehensive quality reports for your alignments.

```python
from graph_mesh_aligner import generate_quality_report

report_path = generate_quality_report(
    mappings=final_mappings,
    output_path=Path("quality_report.txt"),
    conflict_report=conflict_report,
)
```

**Metrics Included:**

- Total mappings, unique subjects/objects
- Confidence statistics (avg, min, max, distribution)
- Support statistics (matchers per mapping)
- Predicate distribution
- Conflict analysis

## Complete Workflow Example

```python
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

# 1. Parallel alignment
results = run_alignment_parallel(
    matchers=DEFAULT_MATCHERS,
    source_ontology=Path("source.owl"),
    target_ontology=Path("target.owl"),
    output_dir=Path("output/"),
)

# 2. Fuse mappings
mapping_files = {r.matcher_name: r.mapping_path for r in results if r.success}
fused = fuse_mappings(mapping_files, min_confidence=0.5)

# 3. Apply voting
config = VotingConfig(strategy=VotingStrategy.MAJORITY)
voting_result = vote(fused, config, total_matchers=len(mapping_files))

# 4. Resolve conflicts
conflict_report = resolve_conflicts(voting_result.accepted_mappings, strategy="confidence")

# 5. Generate quality report
generate_quality_report(
    conflict_report.resolved_mappings,
    Path("quality_report.txt"),
    conflict_report,
)

# 6. Export final mappings
export_fused_mappings(
    conflict_report.resolved_mappings,
    Path("final_mappings.sssom.tsv"),
)
```

## Performance Improvements

### Parallel Execution

- **Sequential**: Matchers run one after another
  - Time = T₁ + T₂ + T₃ (sum of all execution times)

- **Parallel**: Matchers run simultaneously
  - Time = max(T₁, T₂, T₃) (longest single matcher)

- **Expected Speedup**: 3x for 3 matchers with similar execution times

### Timeout Handling

Each matcher has configurable timeout (default: 300s). Failed matchers don't block others.

```python
from graph_mesh_aligner import ContainerMatcher

matcher = ContainerMatcher(
    name="LogMap",
    image="graph-mesh/logmap:latest",
    output_filename="logmap.sssom.tsv",
    timeout=600,  # 10 minutes
    health_check_enabled=True,
)
```

## Advanced Features

### Custom Matcher Weights

Weight matchers based on past performance:

```python
from graph_mesh_aligner import suggest_matcher_weights, VotingConfig, VotingStrategy

# Automatically suggest weights based on agreement
weights = suggest_matcher_weights(fused_mappings)

# Use in weighted voting
config = VotingConfig(
    strategy=VotingStrategy.WEIGHTED,
    matcher_weights=weights,
    min_support_ratio=0.6,
)
```

### Confidence Filtering

Filter mappings at multiple stages:

```python
# During fusion
fused = fuse_mappings(mapping_files, min_confidence=0.3)

# During voting
config = VotingConfig(min_confidence=0.7)

# As post-processing
from graph_mesh_aligner import filter_by_confidence
high_confidence = filter_by_confidence(fused, min_confidence=0.8)
```

### Reference-Based Evaluation

Compare with gold standard alignments:

```python
from graph_mesh_aligner import compare_with_reference

metrics = compare_with_reference(
    mappings=final_mappings,
    reference_mappings=gold_standard,
)

print(f"Precision: {metrics['precision']:.3f}")
print(f"Recall: {metrics['recall']:.3f}")
print(f"F1-Score: {metrics['f1_score']:.3f}")
```

## API Reference

### matchers.py

- `ContainerMatcher`: Docker-based matcher with timeout and health checks
- `run_alignment()`: Sequential execution (backward compatible)
- `run_alignment_parallel()`: Parallel execution (recommended)
- `run_alignment_async()`: Async execution for integration

### fusion.py

- `fuse_mappings()`: Combine mappings from multiple matchers
- `load_sssom_mappings()`: Load SSSOM TSV files
- `export_fused_mappings()`: Export to SSSOM format
- `identify_conflicts()`: Find conflicting mappings

### voting.py

- `vote()`: Apply voting strategy
- `VotingStrategy`: Enum of available strategies
- `VotingConfig`: Configuration for voting
- `calculate_matcher_agreement()`: Pairwise matcher agreement
- `suggest_matcher_weights()`: Auto-suggest weights

### quality.py

- `calculate_quality_metrics()`: Compute comprehensive metrics
- `resolve_conflicts()`: Apply conflict resolution strategy
- `generate_quality_report()`: Create detailed report
- `filter_by_confidence()`: Filter by consensus confidence
- `compare_with_reference()`: Evaluate against gold standard

## Configuration

### Matcher Configuration

```python
ContainerMatcher(
    name="CustomMatcher",
    image="my-matcher:latest",
    output_filename="custom.sssom.tsv",
    timeout=600,  # seconds
    health_check_enabled=True,
)
```

### Voting Configuration

```python
VotingConfig(
    strategy=VotingStrategy.THRESHOLD,
    min_support_count=2,      # At least 2 matchers
    min_support_ratio=0.6,    # At least 60% of matchers
    min_confidence=0.5,       # Individual confidence >= 0.5
    matcher_weights=None,     # Optional custom weights
)
```

## Troubleshooting

### Timeout Issues

If matchers frequently timeout:

```python
# Increase timeout
matcher.timeout = 900  # 15 minutes

# Or disable health checks for faster startup
matcher.health_check_enabled = False
```

### Docker Issues

Ensure Docker is running and images are available:

```bash
docker images | grep graph-mesh
# Should show: logmap, aml, bertmap
```

### Low Consensus

If few mappings survive voting:

```python
# Reduce thresholds
config = VotingConfig(
    strategy=VotingStrategy.THRESHOLD,
    min_support_count=1,      # Accept single matcher
    min_support_ratio=0.33,   # Accept 1/3 agreement
    min_confidence=0.3,       # Lower confidence bar
)
```

## See Also

- [SSSOM Specification](https://mapping-commons.github.io/sssom/)
- [Example Script](../examples/parallel_alignment_example.py)
- [Graph-Mesh Documentation](../README.md)
