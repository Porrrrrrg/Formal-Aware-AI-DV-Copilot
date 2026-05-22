"""Typed model exports for the core verification IR."""

__all__ = [
    "ArtifactEncoding",
    "ArtifactKind",
    "ArtifactManifest",
    "ArtifactRecord",
    "Candidate",
    "Diagnostic",
    "DiagnosticLevel",
    "ErrorKind",
    "ErrorRecord",
    "Language",
    "ProblemSpec",
    "RunManifest",
    "RunStatus",
    "ToolName",
    "ToolchainVersions",
    "VerifierOutcome",
    "VerificationStatus",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(name)
    from app.models import core

    return getattr(core, name)
