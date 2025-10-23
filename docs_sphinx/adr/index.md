# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting key architectural decisions made in the Graph-Mesh project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR follows this structure:

- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: The issue motivating this decision
- **Decision**: The change being proposed or decided
- **Consequences**: The resulting context after applying the decision

## Index of ADRs

```{toctree}
:maxdepth: 1

adr-001-container-based-architecture
adr-002-manifest-driven-pipeline
adr-003-sssom-mapping-format
adr-004-modular-package-structure
adr-005-multi-matcher-strategy
```

## Quick Reference

| ADR | Title | Status |
|-----|-------|--------|
| [001](adr-001-container-based-architecture.md) | Container-Based Architecture | Accepted |
| [002](adr-002-manifest-driven-pipeline.md) | Manifest-Driven Pipeline | Accepted |
| [003](adr-003-sssom-mapping-format.md) | SSSOM Mapping Format | Accepted |
| [004](adr-004-modular-package-structure.md) | Modular Package Structure | Accepted |
| [005](adr-005-multi-matcher-strategy.md) | Multi-Matcher Strategy | Accepted |

## Creating New ADRs

When making significant architectural decisions:

1. Copy the ADR template
2. Assign the next sequential number
3. Fill in all sections
4. Submit for review via pull request
5. Update this index when accepted
