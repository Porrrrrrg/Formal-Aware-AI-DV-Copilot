"""Lightweight schema objects shared by verifier adapters.

The repository intentionally avoids runtime dependencies for the base tooling, so
these contracts use dataclasses instead of Pydantic. They mirror the typed IR
described in the project research notes and provide JSON-friendly serialization
for smoke tests and CLI entry points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ToolName = Literal["lean", "rocq", "isabelle", "z3", "cvc5"]
LanguageName = Literal["lean", "rocq", "isabelle", "smt2"]
OutcomeStatus = Literal["passed", "failed", "blocked", "skipped"]
DiagnosticLevel = Literal["info", "warning", "error"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ProblemSpec:
    problem_id: str
    tool: ToolName
    language: LanguageName
    statement: str
    assumptions: list[str] = field(default_factory=list)
    context_refs: list[str] = field(default_factory=list)
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "tool": self.tool,
            "language": self.language,
            "statement": self.statement,
            "assumptions": list(self.assumptions),
            "context_refs": list(self.context_refs),
            "source_url": self.source_url,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Candidate:
    run_id: str
    attempt_id: str
    producer: str
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "producer": self.producer,
            "content": self.content,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "model": self.model,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Diagnostic:
    level: DiagnosticLevel
    message: str
    line: int | None = None
    column: int | None = None
    code: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "source": self.source,
        }


@dataclass(frozen=True)
class VerifierOutcome:
    ok: bool
    tool: ToolName
    status: OutcomeStatus
    exit_code: int
    stdout_ref: str | None
    stderr_ref: str | None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    manifest_ref: str | None = None
    elapsed_ms: int | None = None
    raw_status: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout_ref": self.stdout_ref,
            "stderr_ref": self.stderr_ref,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "artifact_refs": list(self.artifact_refs),
            "manifest_ref": self.manifest_ref,
            "elapsed_ms": self.elapsed_ms,
            "raw_status": self.raw_status,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    created_at: str
    git_sha: str
    dataset_version: str
    prompt_version: str
    model_snapshot: str
    toolchain: dict[str, str | None]
    artifacts_key: str | None = None
    status: str = "queued"
    command: list[str] = field(default_factory=list)
    exit_code: int | None = None
    elapsed_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "git_sha": self.git_sha,
            "dataset_version": self.dataset_version,
            "prompt_version": self.prompt_version,
            "model_snapshot": self.model_snapshot,
            "toolchain": dict(self.toolchain),
            "artifacts_key": self.artifacts_key,
            "status": self.status,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "elapsed_ms": self.elapsed_ms,
        }
