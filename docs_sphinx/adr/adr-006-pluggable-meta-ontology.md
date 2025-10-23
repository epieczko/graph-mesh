# ADR-006: Pluggable Meta-Ontology Architecture

**Status:** Accepted

**Date:** 2025-01-23

**Context:** Design decision for making meta-ontologies configurable and domain-specific

---

## Context

Graph-Mesh was initially designed with a fixed 7-class generic meta-ontology (Entity, Agent, Contract, Event, Location, Regulation, Metric). While this provided a simple starting point, it became apparent that different domains have vastly different semantic requirements:

### Problems with Fixed Generic Ontology:

1. **Domain Mismatch:** Financial services projects (like RiskExec) need FIBO-level concepts (Loan, Mortgage, CreditRisk), not abstract "Entity" classes
2. **Limited Expressiveness:** 7 classes cannot capture domain-specific relationships and hierarchies
3. **Poor Alignment Quality:** Generic classes lead to ambiguous alignments (is a Patient an Entity? Agent? Both?)
4. **Not Reusable:** Healthcare, manufacturing, legal domains each need different semantic backbones
5. **Missed Industry Standards:** FIBO (financial), SNOMED (healthcare), ISA-95 (manufacturing) are established standards we couldn't leverage

### User Feedback:

Real-world use case from RiskExec project highlighted the need:
- Integrating FIBO, MISMO, XBRL, HMDA for financial services
- Generic ontology was inadequate for financial domain concepts
- Need for FIBO as semantic backbone, not 7 generic classes

---

## Decision

We will implement a **pluggable meta-ontology architecture** where users can choose the semantic backbone appropriate for their domain.

### Architecture Components:

1. **Abstract Provider Interface** (`MetaOntologyProvider`)
   - Defines contract all providers must implement
   - Methods: `build_graph()`, `get_alignment_targets()`, `get_namespace()`, etc.

2. **Provider Registry** (`MetaOntologyRegistry`)
   - Central registry for provider types
   - Factory pattern for creating providers from configuration
   - Supports user-defined custom providers

3. **Built-in Providers:**
   - **Generic:** Original 7-class ontology (default, backward compatible)
   - **FIBO:** Financial Industry Business Ontology (modular loading)
   - **Custom:** Load any OWL ontology from file/URL
   - **Composite:** Combine multiple providers

4. **Manifest Configuration:**
   - New `meta_ontology` field in pipeline manifests
   - Pydantic validation for provider config
   - Defaults to generic for backward compatibility

### Implementation:

```python
# Abstract interface
class MetaOntologyProvider(ABC):
    @abstractmethod
    def get_info(self) -> MetaOntologyInfo: ...
    @abstractmethod
    def build_graph(self) -> Graph: ...
    @abstractmethod
    def get_alignment_targets(self) -> list[URIRef]: ...
    @abstractmethod
    def get_namespace(self) -> Namespace: ...

# Usage in manifest
meta_ontology:
  type: fibo
  options:
    modules: [FND, LOAN]
```

---

## Consequences

### Positive:

1. **Domain Flexibility:**
   - Financial services can use FIBO
   - Healthcare can use FHIR/SNOMED
   - Manufacturing can use ISA-95
   - Research can use generic

2. **Better Alignment Quality:**
   - Domain-specific concepts improve matcher accuracy
   - More precise semantic relationships
   - Industry-standard vocabularies recognized by external systems

3. **Reusability:**
   - Graph-Mesh becomes useful across domains
   - Not limited to one semantic model
   - Community can contribute domain providers

4. **Extensibility:**
   - Users can register custom providers
   - Composite providers for multi-domain projects
   - No code changes needed to add new providers

5. **Backward Compatibility:**
   - Old code/manifests still work (default to generic)
   - Gradual migration path
   - No breaking changes

### Negative:

1. **Increased Complexity:**
   - More code to maintain (4 providers vs 1 fixed ontology)
   - Provider interface requires documentation
   - Users must choose appropriate provider

2. **Performance Considerations:**
   - Large ontologies (FIBO ~1500 classes) take time to load
   - Mitigated by caching and modular loading
   - Generic provider still instant for quick prototyping

3. **Configuration Overhead:**
   - Users must understand domain ontologies
   - FIBO requires selecting appropriate modules
   - Documentation burden increased

4. **Testing Complexity:**
   - Must test all provider types
   - Integration tests for each provider
   - More edge cases to cover

---

## Alternatives Considered

### Alternative 1: Fixed FIBO Ontology

Replace generic with FIBO as the only meta-ontology.

**Rejected because:**
- Not all users need financial concepts
- FIBO is large and slow to load
- Would break existing generic use cases
- Healthcare/manufacturing domains wouldn't benefit

### Alternative 2: Multiple Fixed Ontologies

Provide 2-3 fixed ontologies (generic, FIBO, healthcare) with simple switch.

**Rejected because:**
- Still inflexible for custom domains
- Maintenance burden of maintaining multiple fixed ontologies
- Cannot combine ontologies
- No extensibility for user-defined ontologies

### Alternative 3: Runtime Ontology Modification

Allow users to modify/extend the generic ontology at runtime.

**Rejected because:**
- Complex API for modifications
- Difficult to validate correctness
- Doesn't leverage existing industry ontologies
- Error-prone

### Alternative 4: No Meta-Ontology (Pairwise Alignment)

Align schemas directly to each other without meta-ontology pivot.

**Rejected because:**
- N×(N-1) alignments needed instead of N
- No unified query interface
- Cannot reason across schemas
- Alignment complexity grows quadratically

---

## Implementation Plan

### Phase 1: Core Infrastructure (Completed)
- [x] Create `MetaOntologyProvider` interface
- [x] Create `MetaOntologyRegistry`
- [x] Refactor existing code into `GenericMetaOntology`
- [x] Implement `FIBOMetaOntology` provider
- [x] Implement `CustomMetaOntology` provider
- [x] Implement `CompositeMetaOntology` provider
- [x] Add `meta_ontology` field to `PipelineManifest` (Pydantic)
- [x] Update `meta_ontology.py` for backward compatibility

### Phase 2: Pipeline Integration (In Progress)
- [ ] Update `orchestrate()` to use provider registry
- [ ] Pass provider to alignment stage
- [ ] Update artifact naming based on provider
- [ ] Add provider info to pipeline logs

### Phase 3: Testing (Pending)
- [ ] Unit tests for each provider
- [ ] Integration tests with different providers
- [ ] Property-based tests for provider interface
- [ ] Test backward compatibility

### Phase 4: Documentation (In Progress)
- [x] Pluggable meta-ontology guide
- [x] Example manifests for each provider
- [x] ADR-006 (this document)
- [ ] Update main documentation
- [ ] API reference for providers
- [ ] Migration guide

---

## Success Metrics

1. **Adoption:** Users successfully use FIBO for financial projects
2. **Extensibility:** At least one community-contributed provider
3. **Backward Compat:** No existing pipelines break
4. **Performance:** FIBO caching reduces load time to <5 seconds on subsequent runs
5. **Documentation:** Users can switch providers without support requests

---

## Related ADRs

- [ADR-001: Container-Based Architecture](./adr-001-container-based-architecture.md)
- [ADR-002: Manifest-Driven Pipeline](./adr-002-manifest-driven-pipeline.md)
- [ADR-005: Multi-Matcher Strategy](./adr-005-multi-matcher-strategy.md)

---

## References

- [FIBO Ontology](https://spec.edmcouncil.org/fibo/)
- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [Basic Formal Ontology (BFO)](https://basic-formal-ontology.org/)
- [DOLCE Ontology](http://www.loa.istc.cnr.it/dolce/overview.html)
- [Ontology Alignment Evaluation Initiative](http://oaei.ontologymatching.org/)

---

## Decision Makers

- System Architect
- Domain Experts (Financial Services)
- Graph-Mesh Core Team

---

## Change History

- 2025-01-23: Initial draft and acceptance
