"""Adapter protocols and core error types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.models.core import (
    ArtifactEncoding,
    ArtifactKind,
    ArtifactRecord,
    Candidate,
    ErrorKind,
    ProblemSpec,
    ToolName,
    VerifierOutcome,
)


class CoreError(Exception):
    """Base exception for typed kernel failures."""

    def __init__(
        self,
        kind: ErrorKind,
        message: str,
        *,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.retryable = retryable
        self.context = context or {}


class SchemaValidationError(CoreError):
    """Raised when data fails the committed core schema."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorKind.SCHEMA_DRIFT, message, retryable=False, context=context)


class ArtifactError(CoreError):
    """Raised for artifact path, integrity, and missing-file failures."""


class AdapterExecutionError(CoreError):
    """Raised when an adapter cannot normalize a verifier execution."""


@dataclass(frozen=True)
class ToolProbe:
    """Adapter availability and version probe result."""

    tool: ToolName
    available: bool
    version: str | None = None
    executable: str | None = None
    error: str | None = None


@runtime_checkable
class ArtifactWriter(Protocol):
    """Minimal writer surface exposed to adapters."""

    def write_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        kind: ArtifactKind,
        media_type: str = "application/octet-stream",
        encoding: ArtifactEncoding = ArtifactEncoding.BINARY,
        producer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        """Persist bytes and return an ArtifactRecord."""


@runtime_checkable
class ToolAdapter(Protocol):
    """Common contract for all tool adapters."""

    tool: ToolName

    def probe(self) -> ToolProbe:
        """Return current tool availability and version information."""

    def supports(self, problem: ProblemSpec) -> bool:
        """Return whether this adapter can process the problem."""


@runtime_checkable
class VerifierAdapter(ToolAdapter, Protocol):
    """Verifier adapter contract used by Lean, Rocq, Isabelle, Z3, and cvc5."""

    def verify(
        self,
        problem: ProblemSpec,
        candidate: Candidate,
        artifacts: ArtifactWriter | None = None,
    ) -> VerifierOutcome:
        """Run the verifier and return a normalized outcome."""

