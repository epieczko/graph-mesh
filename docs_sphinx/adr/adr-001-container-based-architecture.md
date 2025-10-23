# ADR-001: Container-Based Architecture

**Status**: Accepted

**Date**: 2025-01

**Deciders**: Graph-Mesh Team

## Context

The Graph-Mesh system needs to integrate multiple ontology matching tools (LogMap, AML, BERTMap) that:
- Have diverse technology stacks (Java, Python, pre-trained models)
- Require different runtime environments and dependencies
- May have conflicting dependency versions
- Need to be executed in isolation for reproducibility
- Should be easily swappable or upgradable

We need to decide on an integration approach that provides:
- Dependency isolation
- Reproducible builds
- Easy deployment
- Version control for tools

## Decision

We will adopt a **container-based architecture** using Docker for all matcher tools and the orchestrator.

### Key Decisions:

1. **Each matcher runs in a dedicated Docker container**
   - LogMap: Java 17 + Alpine base
   - AML: Java 17 + Alpine base
   - BERTMap: Python 3.10 + slim base
   - Ontmalizer: Java 17 + Alpine base (multi-stage build)

2. **Communication via shared volumes**
   - Matchers read/write to `/artifacts` mounted volume
   - No network communication required
   - File-based contract: matchers consume OWL, produce SSSOM

3. **Orchestrator controls lifecycle**
   - Python Docker SDK for container management
   - Orchestrator starts matcher containers on-demand
   - Docker socket mounted for API access

4. **Docker Compose for development**
   - Single command to build and run entire pipeline
   - Service dependencies declared explicitly
   - Easy to add new services

## Consequences

### Positive

- **Isolation**: Each tool runs in its own environment with exact dependencies
- **Reproducibility**: Docker images ensure consistent builds across environments
- **Version Control**: Image tags allow pinning specific tool versions
- **Easy Onboarding**: Single `docker compose up` runs everything
- **Testing**: Can test individual matchers in isolation
- **Portability**: Works identically on any system with Docker
- **Scalability**: Can scale matchers independently (future Kubernetes support)

### Negative

- **Overhead**: Docker adds some performance overhead
- **Complexity**: Developers need Docker knowledge
- **Build Time**: Initial builds can be slow (mitigated by layer caching)
- **Resource Usage**: Each container consumes memory/CPU
- **Docker Socket Security**: Mounting Docker socket poses security risks (orchestrator has full Docker access)

### Neutral

- **File I/O**: File-based communication is simple but limits real-time streaming
- **No Service Mesh**: Currently no need for service discovery or load balancing
- **Local Development**: Docker required for local development (can't run natively)

## Alternatives Considered

### 1. Native Installation

Install all tools directly on host system.

**Rejected because**:
- Dependency conflicts between Java/Python versions
- Difficult to reproduce environments
- Hard to onboard new developers
- Version management nightmare

### 2. Virtual Environments Only

Use Python venv/conda for Python tools, manual Java installs for others.

**Rejected because**:
- Only solves Python dependency isolation
- Doesn't help with Java tools
- Still environment-specific

### 3. Kubernetes from the Start

Deploy entire system on Kubernetes.

**Rejected because**:
- Over-engineering for current scale
- Adds unnecessary complexity
- Can migrate to K8s later if needed
- Docker Compose sufficient for now

### 4. Virtual Machines

Run each matcher in a full VM.

**Rejected because**:
- Much heavier than containers
- Slower startup times
- Higher resource usage
- More complex management

## Implementation Notes

### Dockerfile Best Practices

- Use multi-stage builds to reduce image size (Ontmalizer)
- Pin base image versions for reproducibility
- Use Alpine for smaller images when possible
- Layer caching: install dependencies before copying code
- Run as non-root user (future enhancement)

### Security Considerations

- Docker socket mounting gives orchestrator full Docker access
  - **Risk**: Compromised orchestrator could control host
  - **Mitigation**: Run in trusted environments only
  - **Future**: Consider Docker API proxy with limited permissions

### Performance Optimization

- Pre-build images in CI/CD
- Use Docker BuildKit for faster builds
- Implement layer caching strategies
- Consider read-only container filesystems (future)

## References

- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
- Docker Compose Documentation: https://docs.docker.com/compose/
- Python Docker SDK: https://docker-py.readthedocs.io/

## Related ADRs

- [ADR-002: Manifest-Driven Pipeline](adr-002-manifest-driven-pipeline.md)
- [ADR-004: Modular Package Structure](adr-004-modular-package-structure.md)
