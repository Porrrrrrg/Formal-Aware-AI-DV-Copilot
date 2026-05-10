"""Authoritative typed IR for replayable formal verification runs."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "v1"
CORE_SCHEMA_ID = "schemas/v1/core.schema.json"

TOOL_VALUES = ("lean", "rocq", "isabelle", "z3", "cvc5")
LANGUAGE_VALUES = ("lean", "rocq", "isabelle", "smt2")

RUN_ID_PATTERN = r"^run_[0-9]{8}T[0-9]{6}Z_[a-f0-9]{12}_[a-z0-9]{6}$"
PROBLEM_ID_PATTERN = r"^problem_(lean|rocq|isabelle|z3|cvc5)_[a-f0-9]{12}$"
ATTEMPT_ID_PATTERN = r"^attempt_[0-9]{4}$"
CANDIDATE_ID_PATTERN = r"^cand_[0-9]{4}_[a-z0-9][a-z0-9_-]{0,31}_[a-f0-9]{12}$"
OUTCOME_ID_PATTERN = r"^verify_[0-9]{4}_(lean|rocq|isabelle|z3|cvc5)_[a-f0-9]{12}$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"
ARTIFACT_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._=-]*(/[A-Za-z0-9][A-Za-z0-9._=-]*)*$"

_RUN_ID_RE = re.compile(RUN_ID_PATTERN)
_PROBLEM_ID_RE = re.compile(PROBLEM_ID_PATTERN)
_ATTEMPT_ID_RE = re.compile(ATTEMPT_ID_PATTERN)
_CANDIDATE_ID_RE = re.compile(CANDIDATE_ID_PATTERN)
_OUTCOME_ID_RE = re.compile(OUTCOME_ID_PATTERN)
_ARTIFACT_KEY_RE = re.compile(ARTIFACT_KEY_PATTERN)

MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ToolName(str, Enum):
    """Verifier tools supported by the core adapter contract."""

    LEAN = "lean"
    ROCQ = "rocq"
    ISABELLE = "isabelle"
    Z3 = "z3"
    CVC5 = "cvc5"


class Language(str, Enum):
    """Source languages accepted by ProblemSpec."""

    LEAN = "lean"
    ROCQ = "rocq"
    ISABELLE = "isabelle"
    SMT2 = "smt2"


class RunStatus(str, Enum):
    """Lifecycle states for a run."""

    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEW = "review"
    PASSED = "passed"
    FAILED = "failed"
    CANCELED = "canceled"


class VerificationStatus(str, Enum):
    """Tool-normalized verification result."""

    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    ERROR = "error"


class DiagnosticLevel(str, Enum):
    """Severity for tool diagnostics."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ErrorKind(str, Enum):
    """Stable error taxonomy shared by adapters and orchestration."""

    INVALID_INPUT = "invalid_input"
    SCHEMA_DRIFT = "schema_drift"
    UNSUPPORTED_TOOL = "unsupported_tool"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_CRASH = "tool_crash"
    ADAPTER_ERROR = "adapter_error"
    ARTIFACT_MISSING = "artifact_missing"
    ARTIFACT_INTEGRITY = "artifact_integrity"
    INTERNAL_ERROR = "internal_error"


class ArtifactKind(str, Enum):
    """Artifact roles stored outside the typed objects."""

    RUN_MANIFEST = "run_manifest"
    PROBLEM_SPEC = "problem_spec"
    CANDIDATE = "candidate"
    VERIFIER_OUTCOME = "verifier_outcome"
    ARTIFACT_MANIFEST = "artifact_manifest"
    STDOUT = "stdout"
    STDERR = "stderr"
    PROOF_SCRIPT = "proof_script"
    SMT2 = "smt2"
    PROOF_OBJECT = "proof_object"
    TRACE = "trace"
    LOG = "log"
    REPORT = "report"
    SCHEMA = "schema"
    OTHER = "other"


class ArtifactEncoding(str, Enum):
    """Payload encoding for an artifact."""

    JSON = "json"
    TEXT = "text"
    BINARY = "binary"


class CoreModel(BaseModel):
    """Base class for all core Pydantic models."""

    model_config = MODEL_CONFIG

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for legacy callers."""

        return self.model_dump(mode="json")


class ToolchainVersions(CoreModel):
    """Version snapshot for target tools."""

    lean: str | None = None
    rocq: str | None = None
    isabelle: str | None = None
    z3: str | None = None
    cvc5: str | None = None


class Diagnostic(CoreModel):
    """A normalized verifier diagnostic."""

    level: DiagnosticLevel
    message: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    code: str | None = Field(default=None, min_length=1)
    artifact_ref: str | None = Field(default=None, pattern=ARTIFACT_KEY_PATTERN)


class ErrorRecord(CoreModel):
    """Machine-readable error payload for recoverable core failures."""

    kind: ErrorKind
    message: str = Field(min_length=1)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class RunManifest(CoreModel):
    """Ledger for one replayable run or experiment iteration."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    run_id: str = Field(pattern=RUN_ID_PATTERN)
    created_at: datetime
    git_sha: str = Field(min_length=7, max_length=64, pattern=r"^[A-Fa-f0-9]+$")
    dataset_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    model_snapshot: str = Field(min_length=1)
    toolchain: ToolchainVersions
    problem_id: str | None = Field(default=None, pattern=PROBLEM_ID_PATTERN)
    artifacts_key: str | None = Field(default=None, pattern=ARTIFACT_KEY_PATTERN)
    status: RunStatus = RunStatus.QUEUED
    random_seed: int | None = Field(default=None, ge=0)
    container_image: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class ProblemSpec(CoreModel):
    """Tool-neutral statement plus context references for a verification task."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    problem_id: str = Field(pattern=PROBLEM_ID_PATTERN)
    tool: ToolName
    language: Language
    statement: str = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    source_url: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("assumptions", "context_refs")
    @classmethod
    def reject_empty_list_items(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("list items must be non-empty strings")
        return value

    @field_validator("context_refs")
    @classmethod
    def validate_context_refs(cls, value: list[str]) -> list[str]:
        invalid = [item for item in value if not _ARTIFACT_KEY_RE.match(item)]
        if invalid:
            raise ValueError(f"invalid artifact refs: {invalid}")
        return value

    @model_validator(mode="after")
    def validate_tool_language_pair(self) -> "ProblemSpec":
        allowed = {
            ToolName.LEAN: Language.LEAN,
            ToolName.ROCQ: Language.ROCQ,
            ToolName.ISABELLE: Language.ISABELLE,
            ToolName.Z3: Language.SMT2,
            ToolName.CVC5: Language.SMT2,
        }
        if allowed[self.tool] != self.language:
            raise ValueError(f"{self.tool.value} problems must use {allowed[self.tool].value}")
        return self


class Candidate(CoreModel):
    """Generated candidate proof, query, or repair payload."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    candidate_id: str = Field(pattern=CANDIDATE_ID_PATTERN)
    run_id: str = Field(pattern=RUN_ID_PATTERN)
    problem_id: str = Field(pattern=PROBLEM_ID_PATTERN)
    attempt_id: str = Field(pattern=ATTEMPT_ID_PATTERN)
    producer: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_type: str = Field(default="text/plain", min_length=1)
    model: str | None = Field(default=None, min_length=1)
    tokens_in: int = Field(default=0, ge=0)
    tokens_out: int = Field(default=0, ge=0)
    artifact_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_refs")
    @classmethod
    def validate_artifact_refs(cls, value: list[str]) -> list[str]:
        invalid = [item for item in value if not _ARTIFACT_KEY_RE.match(item)]
        if invalid:
            raise ValueError(f"invalid artifact refs: {invalid}")
        return value

    @model_validator(mode="after")
    def validate_candidate_attempt_id(self) -> "Candidate":
        attempt = self.attempt_id.removeprefix("attempt_")
        if not self.candidate_id.startswith(f"cand_{attempt}_"):
            raise ValueError("candidate_id attempt prefix must match attempt_id")
        return self


class VerifierOutcome(CoreModel):
    """Normalized result returned by every verifier adapter."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    outcome_id: str = Field(pattern=OUTCOME_ID_PATTERN)
    run_id: str = Field(pattern=RUN_ID_PATTERN)
    problem_id: str = Field(pattern=PROBLEM_ID_PATTERN)
    candidate_id: str = Field(pattern=CANDIDATE_ID_PATTERN)
    attempt_id: str = Field(pattern=ATTEMPT_ID_PATTERN)
    ok: bool
    status: VerificationStatus
    tool: ToolName
    exit_code: int
    elapsed_ms: int | None = Field(default=None, ge=0)
    timed_out: bool = False
    stdout_ref: str | None = Field(default=None, pattern=ARTIFACT_KEY_PATTERN)
    stderr_ref: str | None = Field(default=None, pattern=ARTIFACT_KEY_PATTERN)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    error: ErrorRecord | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_refs")
    @classmethod
    def validate_artifact_refs(cls, value: list[str]) -> list[str]:
        invalid = [item for item in value if not _ARTIFACT_KEY_RE.match(item)]
        if invalid:
            raise ValueError(f"invalid artifact refs: {invalid}")
        return value

    @model_validator(mode="after")
    def validate_verifier_consistency(self) -> "VerifierOutcome":
        attempt = self.attempt_id.removeprefix("attempt_")
        if not self.outcome_id.startswith(f"verify_{attempt}_{self.tool.value}_"):
            raise ValueError("outcome_id attempt/tool prefix must match attempt_id and tool")
        if self.ok != (self.status == VerificationStatus.PASSED):
            raise ValueError("ok must be true exactly when status is passed")
        if self.timed_out and self.status != VerificationStatus.TIMEOUT:
            raise ValueError("timed_out requires status=timeout")
        return self


class ArtifactRecord(CoreModel):
    """Single content-addressed artifact entry."""

    key: str = Field(pattern=ARTIFACT_KEY_PATTERN)
    path: str = Field(pattern=ARTIFACT_KEY_PATTERN)
    kind: ArtifactKind
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=0)
    media_type: str = Field(min_length=1)
    encoding: ArtifactEncoding
    created_at: datetime
    producer: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_path_matches_key(self) -> "ArtifactRecord":
        if self.path != self.key:
            raise ValueError("artifact path must equal normalized artifact key")
        return self


class ArtifactManifest(CoreModel):
    """Index of artifacts produced by one run."""

    schema_version: Literal["v1"] = SCHEMA_VERSION
    manifest_id: str = Field(pattern=RUN_ID_PATTERN)
    run_id: str = Field(pattern=RUN_ID_PATTERN)
    generated_at: datetime
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("generated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_manifest_id(self) -> "ArtifactManifest":
        if self.manifest_id != self.run_id:
            raise ValueError("manifest_id must match run_id")
        keys = [artifact.key for artifact in self.artifacts]
        if len(keys) != len(set(keys)):
            raise ValueError("artifact keys must be unique")
        return self


CORE_OBJECT_MODELS: tuple[type[CoreModel], ...] = (
    RunManifest,
    ProblemSpec,
    Candidate,
    VerifierOutcome,
    ArtifactManifest,
)

CORE_DEF_MODELS: tuple[type[CoreModel], ...] = (
    RunManifest,
    ProblemSpec,
    Candidate,
    VerifierOutcome,
    ArtifactManifest,
    ArtifactRecord,
    Diagnostic,
    ErrorRecord,
    ToolchainVersions,
)

RUN_STATUS_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.BLOCKED, RunStatus.CANCELED}),
    RunStatus.RUNNING: frozenset(
        {RunStatus.PASSED, RunStatus.FAILED, RunStatus.BLOCKED, RunStatus.REVIEW, RunStatus.CANCELED}
    ),
    RunStatus.BLOCKED: frozenset({RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELED}),
    RunStatus.REVIEW: frozenset({RunStatus.RUNNING, RunStatus.PASSED, RunStatus.FAILED}),
    RunStatus.PASSED: frozenset(),
    RunStatus.FAILED: frozenset({RunStatus.REVIEW}),
    RunStatus.CANCELED: frozenset(),
}


def can_transition_run_status(current: RunStatus, next_status: RunStatus) -> bool:
    """Return whether a run state transition is allowed."""

    return next_status in RUN_STATUS_TRANSITIONS[current]


def advance_run_status(manifest: RunManifest, next_status: RunStatus) -> RunManifest:
    """Return a copy of the manifest with an allowed next status."""

    if not can_transition_run_status(manifest.status, next_status):
        raise ValueError(f"invalid run status transition: {manifest.status.value} -> {next_status.value}")
    return manifest.model_copy(update={"status": next_status})


def core_schema_document() -> dict[str, Any]:
    """Return the committed JSON Schema document generated from Pydantic models."""

    definitions: dict[str, Any] = {}
    for model in CORE_DEF_MODELS:
        model_schema = model.model_json_schema(ref_template="#/$defs/{model}")
        nested_defs = model_schema.pop("$defs", {})
        definitions.update(nested_defs)
        definitions[model.__name__] = model_schema

    return {
        "$id": CORE_SCHEMA_ID,
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Formal Agent Core Schemas",
        "oneOf": [{"$ref": f"#/$defs/{model.__name__}"} for model in CORE_OBJECT_MODELS],
        "$defs": dict(sorted(definitions.items())),
    }


def load_core_schema(path: Path | None = None) -> dict[str, Any]:
    """Load the checked-in core schema."""

    schema_path = path or Path(__file__).resolve().parents[2] / "schemas" / "v1" / "core.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_artifact_key(key: str) -> str:
    """Validate and return a normalized artifact key."""

    if not _ARTIFACT_KEY_RE.match(key):
        raise ValueError(f"invalid artifact key: {key!r}")
    return key


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-schema", type=Path)
    args = parser.parse_args()

    schema = core_schema_document()
    text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    if args.write_schema:
        args.write_schema.parent.mkdir(parents=True, exist_ok=True)
        args.write_schema.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
