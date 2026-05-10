"""Compatibility exports for the canonical core IR.

New runtime code should import from ``app.models.core`` and ``app.core.protocols``
directly. This package exists only for callers that import top-level ``core``.
"""

from app.core.protocols import ArtifactWriter, ToolAdapter, ToolProbe, VerifierAdapter
from app.models.core import (
    ArtifactManifest,
    ArtifactRecord,
    Candidate,
    Diagnostic,
    ProblemSpec,
    RunManifest,
    ToolName,
    VerifierOutcome,
)

__all__ = [
    "ArtifactManifest",
    "ArtifactRecord",
    "ArtifactWriter",
    "Candidate",
    "Diagnostic",
    "ProblemSpec",
    "RunManifest",
    "ToolName",
    "ToolAdapter",
    "ToolProbe",
    "VerifierAdapter",
    "VerifierOutcome",
]
