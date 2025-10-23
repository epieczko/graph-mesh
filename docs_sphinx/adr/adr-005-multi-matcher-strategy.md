# ADR-005: Multi-Matcher Strategy

**Status**: Accepted

**Date**: 2025-01

**Deciders**: Graph-Mesh Team

## Context

Ontology alignment is a challenging problem with no single best solution. Different matchers excel in different scenarios:

- **LogMap**: Strong on logic-based reasoning and consistency
- **AML**: Balanced approach with multiple strategies
- **BERTMap**: Semantic similarity using language models

Research shows that combining multiple matchers often produces better results than any single matcher:
- Higher recall (find more correct mappings)
- Better coverage (different matchers find different mappings)
- Confidence aggregation (agreements increase confidence)
- Ensemble learning benefits

We need to decide:
- Should we support multiple matchers?
- How do we handle conflicting mappings?
- How do we aggregate results?
- What's the user experience?

## Decision

We will adopt a **multi-matcher ensemble strategy** where users can run multiple matchers and combine their results.

### Key Decisions:

1. **User Chooses Matchers**
   ```yaml
   matchers:
     - logmap
     - aml
     - bertmap
   ```

2. **Parallel Execution**
   - All matchers run concurrently
   - No dependencies between matchers
   - Docker Compose handles orchestration

3. **Individual SSSOM Outputs**
   - Each matcher produces separate SSSOM file
   - Preserved for provenance and debugging
   - Users can inspect per-matcher results

4. **Fusion Stage Aggregation**
   - Fusion stage reads all SSSOM files
   - Combines mappings using configurable strategy
   - Default: Union with highest confidence

5. **No Automatic Conflict Resolution (v1)**
   - Keep all mappings initially
   - Let downstream tools handle conflicts
   - Future: Add conflict resolution strategies

6. **Extensible Matcher Registry**
   - Easy to add new matchers
   - No code changes to core pipeline
   - Docker container + SSSOM output = matcher

## Consequences

### Positive

- **Better Results**: Ensemble typically outperforms individual matchers
- **Flexibility**: Users choose appropriate matchers for their use case
- **Redundancy**: If one matcher fails, others may succeed
- **Confidence**: Multiple matchers agreeing increases confidence
- **Research-Aligned**: Matches best practices in ontology matching community
- **Future-Proof**: Easy to add new matchers as they emerge

### Negative

- **Longer Execution Time**: Running 3 matchers takes ~3x longer (mitigated by parallelization)
- **Higher Resource Usage**: Multiple containers running simultaneously
- **Duplicate Mappings**: Need to handle duplicates from different matchers
- **Complexity**: More outputs to manage and understand

### Neutral

- **User Choice**: Users must decide which matchers to use (provides flexibility but requires knowledge)
- **No Automatic Conflict Resolution**: Punt conflict resolution to future version

## Alternatives Considered

### 1. Single Matcher Only

Support only one matcher (e.g., LogMap).

**Rejected because**:
- Limits result quality
- No redundancy if matcher fails
- Different use cases need different matchers
- Industry trend is toward ensembles

### 2. Forced Ensemble

Always run all matchers, no user choice.

**Rejected because**:
- Wastes resources if user only needs one
- Slower for simple use cases
- Less flexible
- Higher cost

### 3. Sequential Execution

Run matchers one after another.

**Rejected because**:
- Much slower (additive time)
- No benefit over parallel execution
- Underutilizes compute resources

### 4. Automatic Best Matcher Selection

Automatically choose best matcher based on ontology characteristics.

**Rejected because**:
- Requires ML model to predict best matcher
- Complex to implement and maintain
- Hard to explain to users
- Can add later as enhancement

### 5. Voting System

Require multiple matchers to agree before accepting mapping.

**Rejected because**:
- Reduces recall (misses unique mappings)
- Too conservative
- Can be implemented as post-processing filter

## Implementation Details

### Matcher Registry

```python
from dataclasses import dataclass

@dataclass
class ContainerMatcher:
    name: str
    image: str
    command_template: str

MATCHERS = {
    "logmap": ContainerMatcher(
        name="logmap",
        image="graph-mesh/logmap:latest",
        command_template="logmap {input1} {input2} {output}"
    ),
    "aml": ContainerMatcher(
        name="aml",
        image="graph-mesh/aml:latest",
        command_template="aml {input1} {input2} {output}"
    ),
    "bertmap": ContainerMatcher(
        name="bertmap",
        image="graph-mesh/bertmap:latest",
        command_template="bertmap {input1} {input2} {output}"
    ),
}
```

### Parallel Execution

```python
import docker
from concurrent.futures import ThreadPoolExecutor

def run_alignment(converted_graphs, matchers, artifacts_dir):
    """Run multiple matchers in parallel."""
    client = docker.from_env()

    def run_matcher(matcher_name):
        matcher = MATCHERS[matcher_name]
        # Run container, wait for completion
        # Convert output to SSSOM
        return f"{matcher_name}_mappings.sssom.tsv"

    # Run all matchers in parallel
    with ThreadPoolExecutor(max_workers=len(matchers)) as executor:
        mapping_files = list(executor.map(run_matcher, matchers))

    return mapping_files
```

### Aggregation Strategy

```python
def aggregate_mappings(mapping_files, strategy="union"):
    """Combine mappings from multiple matchers."""
    all_mappings = []

    for file in mapping_files:
        msdf = sssom.parse(file)
        all_mappings.append(msdf.df)

    combined = pd.concat(all_mappings)

    if strategy == "union":
        # Keep all mappings, deduplicate by keeping highest confidence
        result = combined.sort_values("confidence", ascending=False)
        result = result.drop_duplicates(
            subset=["subject_id", "object_id"],
            keep="first"
        )
    elif strategy == "intersection":
        # Keep only mappings found by all matchers
        result = combined.groupby(["subject_id", "object_id"]).filter(
            lambda x: len(x) >= len(mapping_files)
        )
    elif strategy == "weighted":
        # Weighted average of confidence scores
        result = combined.groupby(["subject_id", "object_id"]).agg({
            "confidence": "mean",
            "mapping_provider": lambda x: ",".join(x)
        }).reset_index()

    return result
```

### User Experience

**Manifest Configuration**:

```yaml
# Use all matchers
matchers:
  - logmap
  - aml
  - bertmap

# Use single matcher
matchers:
  - logmap

# Use subset
matchers:
  - logmap
  - aml
```

**Output Artifacts**:

```
artifacts/
├── logmap_mappings.sssom.tsv      # Individual outputs
├── aml_mappings.sssom.tsv
├── bertmap_mappings.sssom.tsv
└── merged_graph.ttl               # Fusion uses all mappings
```

**Analyzing Results**:

```python
import pandas as pd

# Compare matchers
logmap = pd.read_csv("artifacts/logmap_mappings.sssom.tsv", sep="\t")
aml = pd.read_csv("artifacts/aml_mappings.sssom.tsv", sep="\t")
bertmap = pd.read_csv("artifacts/bertmap_mappings.sssom.tsv", sep="\t")

print(f"LogMap: {len(logmap)} mappings")
print(f"AML: {len(aml)} mappings")
print(f"BERTMap: {len(bertmap)} mappings")

# Find agreements
all_mappings = pd.concat([logmap, aml, bertmap])
agreements = all_mappings.groupby(["subject_id", "object_id"]).size()
strong_agreements = agreements[agreements >= 2]
print(f"Agreed by 2+ matchers: {len(strong_agreements)}")
```

## Matcher Selection Guidance

### LogMap

**Best For**:
- Well-structured ontologies with formal axioms
- Need for consistency checking
- High precision requirements

**Strengths**:
- Logical reasoning
- Inconsistency repair
- Fast execution

**Limitations**:
- May miss lexical similarities
- Requires formal semantics

### AML

**Best For**:
- General-purpose alignment
- Diverse ontology types
- Balanced precision/recall

**Strengths**:
- Multiple matching strategies
- Good balance
- Configurable

**Limitations**:
- Not specialized for any specific case

### BERTMap

**Best For**:
- Ontologies with rich textual descriptions
- Cross-domain matching
- Natural language labels

**Strengths**:
- Semantic understanding
- Pre-trained language models
- Handles synonyms well

**Limitations**:
- Slower execution
- Higher memory usage
- Requires good labels

### Recommendation Table

| Use Case | Recommended Matchers |
|----------|---------------------|
| High-quality formal ontologies | LogMap + AML |
| Text-heavy ontologies | BERTMap + AML |
| Cross-domain integration | All three |
| Quick testing | LogMap only |
| Maximum coverage | All three |

## Future Enhancements

### 1. Confidence Aggregation

Combine confidence scores from multiple matchers:

```python
def aggregate_confidence(mappings, method="mean"):
    """Aggregate confidence scores."""
    if method == "mean":
        return mappings.groupby(["subject_id", "object_id"])["confidence"].mean()
    elif method == "max":
        return mappings.groupby(["subject_id", "object_id"])["confidence"].max()
    elif method == "weighted":
        # Weight by matcher performance
        weights = {"logmap": 0.4, "aml": 0.3, "bertmap": 0.3}
        # Apply weights...
```

### 2. Conflict Resolution

Handle contradictory mappings:

```python
def resolve_conflicts(mappings):
    """Resolve contradictory mappings."""
    # If A → B and A → C (C ≠ B), keep highest confidence
    conflicts = mappings.groupby("subject_id").filter(lambda x: len(x) > 1)
    resolved = conflicts.sort_values("confidence").drop_duplicates("subject_id", keep="last")
    return resolved
```

### 3. Active Learning

Learn from user feedback to improve matcher selection:
- Track which matchers produce mappings users accept/reject
- Adjust weights accordingly
- Recommend matchers based on ontology characteristics

### 4. Matcher Parameters

Allow users to configure matcher behavior:

```yaml
matchers:
  - name: logmap
    params:
      threshold: 0.7
      repair_inconsistencies: true
  - name: bertmap
    params:
      model: bert-base-uncased
```

### 5. Conditional Execution

Run matchers conditionally:

```yaml
matchers:
  - name: logmap
    run_if: ontology_size < 10000
  - name: bertmap
    run_if: has_textual_labels
```

## Performance Considerations

### Parallel Execution Time

Approximate execution times (example ontologies):

| Matcher | Sequential | Parallel (3 matchers) |
|---------|-----------|----------------------|
| LogMap  | 5 min     | 5 min                |
| AML     | 7 min     | 7 min                |
| BERTMap | 10 min    | 10 min               |
| **Total** | **22 min** | **~10 min** |

Parallel execution provides ~2.2x speedup for 3 matchers.

### Resource Requirements

| Matcher | Memory | CPU |
|---------|--------|-----|
| LogMap  | ~2 GB  | 1-2 cores |
| AML     | ~2 GB  | 1-2 cores |
| BERTMap | ~4 GB  | 2-4 cores |
| **Total** | **~8 GB** | **4-8 cores** |

## References

- Ontology Alignment Evaluation Initiative (OAEI): http://oaei.ontologymatching.org/
- "Matching Ontologies in the Wild: A Machine Learning Approach" (2019)
- LogMap: https://github.com/ernestojimenezruiz/logmap-matcher
- AML: https://github.com/AgreementMakerLight/AML-Project
- BERTMap: https://github.com/KRR-Oxford/BERTMap

## Related ADRs

- [ADR-001: Container-Based Architecture](adr-001-container-based-architecture.md)
- [ADR-003: SSSOM Mapping Format](adr-003-sssom-mapping-format.md)
- [ADR-002: Manifest-Driven Pipeline](adr-002-manifest-driven-pipeline.md)
