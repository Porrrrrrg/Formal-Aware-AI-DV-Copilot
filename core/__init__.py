"""Core typed contracts for JasperLoop verifier integrations."""

from core.schemas import Candidate, Diagnostic, ProblemSpec, RunManifest, VerifierOutcome
from core.tool_adapter import ToolAdapter

__all__ = [
    "Candidate",
    "Diagnostic",
    "ProblemSpec",
    "RunManifest",
    "ToolAdapter",
    "VerifierOutcome",
]
