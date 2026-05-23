"""Typed model exports for the core verification IR."""

__all__ = [
    "ArtifactEncoding",
    "ArtifactKind",
    "ArtifactManifest",
    "ArtifactRecord",
    "AgentRunManifest",
    "Candidate",
    "BackendError",
    "BackendResult",
    "BackendStatus",
    "CheckResult",
    "CheckStatus",
    "Diagnostic",
    "DiagnosticLevel",
    "ErrorKind",
    "ErrorRecord",
    "EvaluationResult",
    "EvidencePacket",
    "Language",
    "ProblemSpec",
    "RepairAttempt",
    "RunManifest",
    "RunStatus",
    "Task",
    "ToolName",
    "ToolchainVersions",
    "VerifierOutcome",
    "VerificationStatus",
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(name)
    if name in {
        "AgentRunManifest",
        "BackendError",
        "BackendResult",
        "BackendStatus",
        "CheckResult",
        "CheckStatus",
        "EvaluationResult",
        "EvidencePacket",
        "RepairAttempt",
        "Task",
    }:
        from app.models import agent

        return getattr(agent, name)

    from app.models import core

    return getattr(core, name)
