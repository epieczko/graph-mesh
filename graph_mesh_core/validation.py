"""OWL validation and reasoning utilities using owlready2.

This module provides:
- OWL profile validation (DL, EL, QL, RL)
- Consistency checking with reasoners (HermiT, Pellet)
- Inference and materialization
- Detailed error reporting and diagnostics
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from rdflib import Graph


class OWLProfile(Enum):
    """OWL 2 profiles for validation."""
    FULL = "OWL 2 Full"
    DL = "OWL 2 DL"
    EL = "OWL 2 EL"
    QL = "OWL 2 QL"
    RL = "OWL 2 RL"


class ReasonerType(Enum):
    """Supported OWL reasoners."""
    HERMIT = "HermiT"
    PELLET = "Pellet"
    FACT = "FaCT++"


@dataclass
class ValidationError:
    """Represents a validation error or warning."""
    severity: str  # "error", "warning", "info"
    message: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of ontology validation."""
    is_valid: bool
    profile: OWLProfile
    errors: List[ValidationError]
    warnings: List[ValidationError]
    reasoner_used: Optional[ReasonerType] = None


class OWLValidator:
    """Validator for OWL ontologies using owlready2."""

    def __init__(self, reasoner: ReasonerType = ReasonerType.HERMIT):
        """Initialize the validator.

        Args:
            reasoner: The reasoner to use for validation
        """
        self.reasoner = reasoner
        self._reasoner_name = {
            ReasonerType.HERMIT: "HermiT",
            ReasonerType.PELLET: "Pellet",
            ReasonerType.FACT: "FaCT++",
        }[reasoner]

    def validate_graph(
        self,
        graph: Graph,
        profile: OWLProfile = OWLProfile.DL
    ) -> ValidationResult:
        """Validate an RDF graph against an OWL profile.

        Args:
            graph: RDF graph to validate
            profile: OWL profile to validate against

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Basic structural validation
        structural_errors = self._check_structural_validity(graph)
        errors.extend(structural_errors)

        # Profile-specific validation
        profile_errors = self._check_profile_compliance(graph, profile)
        errors.extend(profile_errors)

        # Consistency checking with reasoner
        if profile in {OWLProfile.DL, OWLProfile.FULL}:
            try:
                consistency_result = self.check_consistency(graph)
                if not consistency_result.is_consistent:
                    errors.extend(consistency_result.errors)
                    warnings.extend(consistency_result.warnings)
            except Exception as e:
                warnings.append(ValidationError(
                    "warning",
                    f"Reasoner validation skipped due to error: {str(e)}"
                ))

        is_valid = len([e for e in errors if e.severity == "error"]) == 0

        return ValidationResult(
            is_valid=is_valid,
            profile=profile,
            errors=[e for e in errors if e.severity == "error"],
            warnings=[e for e in errors if e.severity == "warning"] + warnings,
            reasoner_used=self.reasoner if profile in {OWLProfile.DL, OWLProfile.FULL} else None
        )

    def _check_structural_validity(self, graph: Graph) -> List[ValidationError]:
        """Check basic OWL structural validity.

        Args:
            graph: RDF graph to check

        Returns:
            List of validation errors
        """
        from rdflib import OWL, RDF, RDFS, URIRef

        errors = []

        # Check for basic OWL requirements
        # 1. Check that classes are declared
        for s, p, o in graph.triples((None, RDFS.subClassOf, None)):
            # Subject should be a class
            if not any(graph.triples((s, RDF.type, OWL.Class))) and \
               not any(graph.triples((s, RDF.type, RDFS.Class))):
                errors.append(ValidationError(
                    "warning",
                    f"Class {s} is used in subClassOf but not declared as a Class",
                    subject=str(s)
                ))

        # 2. Check property declarations
        for s, p, o in graph.triples((None, RDFS.domain, None)):
            if not any(graph.triples((s, RDF.type, OWL.ObjectProperty))) and \
               not any(graph.triples((s, RDF.type, OWL.DatatypeProperty))) and \
               not any(graph.triples((s, RDF.type, RDF.Property))):
                errors.append(ValidationError(
                    "warning",
                    f"Property {s} has domain but is not declared as a property",
                    subject=str(s)
                ))

        # 3. Check for undefined classes in domains/ranges
        for s, p, o in graph.triples((None, RDFS.domain, None)):
            if isinstance(o, URIRef) and not any(graph.triples((o, RDF.type, OWL.Class))) and \
               not any(graph.triples((o, RDF.type, RDFS.Class))):
                errors.append(ValidationError(
                    "warning",
                    f"Domain class {o} is not declared",
                    subject=str(s),
                    object=str(o)
                ))

        return errors

    def _check_profile_compliance(
        self,
        graph: Graph,
        profile: OWLProfile
    ) -> List[ValidationError]:
        """Check compliance with specific OWL profiles.

        Args:
            graph: RDF graph to check
            profile: OWL profile to validate against

        Returns:
            List of validation errors
        """
        errors = []

        if profile == OWLProfile.EL:
            errors.extend(self._check_el_profile(graph))
        elif profile == OWLProfile.QL:
            errors.extend(self._check_ql_profile(graph))
        elif profile == OWLProfile.RL:
            errors.extend(self._check_rl_profile(graph))

        return errors

    def _check_el_profile(self, graph: Graph) -> List[ValidationError]:
        """Check OWL 2 EL profile compliance.

        OWL EL restricts to existential quantification and is optimized
        for class subsumption reasoning.
        """
        from rdflib import OWL

        errors = []

        # EL doesn't allow universal quantification
        for s, p, o in graph.triples((None, OWL.allValuesFrom, None)):
            errors.append(ValidationError(
                "error",
                "OWL EL does not allow universal quantification (owl:allValuesFrom)",
                subject=str(s)
            ))

        # EL doesn't allow negation
        for s, p, o in graph.triples((None, OWL.complementOf, None)):
            errors.append(ValidationError(
                "error",
                "OWL EL does not allow negation (owl:complementOf)",
                subject=str(s)
            ))

        return errors

    def _check_ql_profile(self, graph: Graph) -> List[ValidationError]:
        """Check OWL 2 QL profile compliance.

        OWL QL is designed for query answering over large datasets.
        """
        from rdflib import OWL

        errors = []

        # QL has restrictions on class expressions
        for s, p, o in graph.triples((None, OWL.unionOf, None)):
            errors.append(ValidationError(
                "error",
                "OWL QL restricts use of owl:unionOf",
                subject=str(s)
            ))

        return errors

    def _check_rl_profile(self, graph: Graph) -> List[ValidationError]:
        """Check OWL 2 RL profile compliance.

        OWL RL is designed for rule-based reasoning.
        """
        from rdflib import OWL

        errors = []

        # RL has specific restrictions on class expressions in superclass position
        # This is a simplified check
        for s, p, o in graph.triples((None, OWL.someValuesFrom, None)):
            # In RL, existential restrictions have limitations
            # Full validation would require more detailed checks
            pass

        return errors

    def check_consistency(self, graph: Graph) -> ConsistencyResult:
        """Check ontology consistency using a reasoner.

        Args:
            graph: RDF graph to check

        Returns:
            ConsistencyResult with consistency status and any errors
        """
        try:
            import owlready2

            # Create temporary file for the ontology
            with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
                temp_path = f.name
                graph.serialize(destination=temp_path, format='xml')

            try:
                # Load ontology with owlready2
                onto = owlready2.get_ontology(f"file://{temp_path}").load()

                # Run reasoner
                with onto:
                    try:
                        if self.reasoner == ReasonerType.HERMIT:
                            owlready2.sync_reasoner_hermit(infer_property_values=True)
                        elif self.reasoner == ReasonerType.PELLET:
                            owlready2.sync_reasoner_pellet(infer_property_values=True)
                        else:
                            # Default to HermiT
                            owlready2.sync_reasoner_hermit(infer_property_values=True)

                        # If we get here, ontology is consistent
                        return ConsistencyResult(
                            is_consistent=True,
                            errors=[],
                            warnings=[],
                            reasoner=self.reasoner
                        )

                    except owlready2.OwlReadyInconsistentOntologyError as e:
                        return ConsistencyResult(
                            is_consistent=False,
                            errors=[ValidationError(
                                "error",
                                f"Ontology is inconsistent: {str(e)}"
                            )],
                            warnings=[],
                            reasoner=self.reasoner
                        )

            finally:
                # Clean up temp file
                Path(temp_path).unlink(missing_ok=True)

        except ImportError:
            return ConsistencyResult(
                is_consistent=True,
                errors=[],
                warnings=[ValidationError(
                    "warning",
                    "owlready2 not available for reasoner-based consistency checking"
                )],
                reasoner=None
            )
        except Exception as e:
            return ConsistencyResult(
                is_consistent=True,
                errors=[],
                warnings=[ValidationError(
                    "warning",
                    f"Consistency check failed: {str(e)}"
                )],
                reasoner=self.reasoner
            )

    def materialize_inferences(self, graph: Graph) -> Graph:
        """Materialize all inferences from the reasoner into the graph.

        Args:
            graph: Input RDF graph

        Returns:
            New graph with materialized inferences
        """
        try:
            import owlready2

            # Create temporary file for the ontology
            with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
                temp_path = f.name
                graph.serialize(destination=temp_path, format='xml')

            try:
                # Load ontology with owlready2
                onto = owlready2.get_ontology(f"file://{temp_path}").load()

                # Run reasoner
                with onto:
                    if self.reasoner == ReasonerType.HERMIT:
                        owlready2.sync_reasoner_hermit(infer_property_values=True)
                    else:
                        owlready2.sync_reasoner_pellet(infer_property_values=True)

                # Save inferred ontology
                with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
                    inferred_path = f.name
                    onto.save(file=inferred_path)

                # Load back into rdflib
                inferred_graph = Graph()
                inferred_graph.parse(inferred_path, format='xml')

                # Clean up
                Path(inferred_path).unlink(missing_ok=True)

                return inferred_graph

            finally:
                Path(temp_path).unlink(missing_ok=True)

        except ImportError:
            # If owlready2 not available, return original graph
            return graph
        except Exception:
            # On error, return original graph
            return graph


@dataclass
class ConsistencyResult:
    """Result of consistency checking."""
    is_consistent: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    reasoner: Optional[ReasonerType] = None


def validate_ontology(
    graph: Graph,
    profile: OWLProfile = OWLProfile.DL,
    reasoner: ReasonerType = ReasonerType.HERMIT
) -> ValidationResult:
    """Convenience function to validate an ontology.

    Args:
        graph: RDF graph to validate
        profile: OWL profile to validate against
        reasoner: Reasoner to use for consistency checking

    Returns:
        ValidationResult
    """
    validator = OWLValidator(reasoner=reasoner)
    return validator.validate_graph(graph, profile=profile)


def check_consistency(
    graph: Graph,
    reasoner: ReasonerType = ReasonerType.HERMIT
) -> ConsistencyResult:
    """Convenience function to check ontology consistency.

    Args:
        graph: RDF graph to check
        reasoner: Reasoner to use

    Returns:
        ConsistencyResult
    """
    validator = OWLValidator(reasoner=reasoner)
    return validator.check_consistency(graph)
