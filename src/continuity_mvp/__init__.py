"""OASSE Continuity MVP: one governed cognitive lineage across replaceable model substrates."""

from .contracts import ContinuityState, ContinuityTransition
from .kernel import ContinuityKernel, FailClosedAuthority, invariant_report

__all__ = ["ContinuityState", "ContinuityTransition", "ContinuityKernel", "FailClosedAuthority", "invariant_report"]
