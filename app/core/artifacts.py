"""Artifact naming, hashing, and local store helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.models.core import (
    ARTIFACT_KEY_PATTERN,
    ATTEMPT_ID_PATTERN,
    CANDIDATE_ID_PATTERN,
    OUTCOME_ID_PATTERN,
    PROBLEM_ID_PATTERN,
    RUN_ID_PATTERN,
    ArtifactEncoding,
    ArtifactKind,
    ArtifactRecord,
    Candidate,
    ProblemSpec,
    RunManifest,
    ToolName,
    VerifierOutcome,
)

_ARTIFACT_KEY_RE = re.compile(ARTIFACT_KEY_PATTERN)
_RUN_ID_RE = re.compile(RUN_ID_PATTERN)
_PROBLEM_ID_RE = re.compile(PROBLEM_ID_PATTERN)
_ATTEMPT_ID_RE = re.compile(ATTEMPT_ID_PATTERN)
_CANDIDATE_ID_RE = re.compile(CANDIDATE_ID_PATTERN)
_OUTCOME_ID_RE = re.compile(OUTCOME_ID_PATTERN)
_SLUG_RE = re.compile(r"[^a-z0-9_-]+")


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize JSON in a stable form for hashing and replay."""

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    """Return a lowercase sha256 digest for bytes."""

    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    """Return a lowercase sha256 digest for UTF-8 text."""

    return sha256_bytes(payload.encode("utf-8"))


def short_hash(payload: bytes | str, length: int = 12) -> str:
    """Return the leading digest characters used in stable IDs."""

    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return sha256_bytes(data)[:length]


def slugify(value: str, max_length: int = 32) -> str:
    """Normalize a producer or model name for use in IDs."""

    slug = _SLUG_RE.sub("_", value.strip().lower()).strip("_-")
    slug = re.sub(r"[_-]{2,}", "_", slug)
    if not slug:
        slug = "unknown"
    return slug[:max_length]


def make_run_id(git_sha: str, *, now: datetime | None = None, nonce: str | None = None) -> str:
    """Create run_<UTC ts>_<short git sha>_<nonce>."""

    if not re.fullmatch(r"[A-Fa-f0-9]{7,64}", git_sha):
        raise ValueError("git_sha must be 7 to 64 hex characters")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nonce_value = nonce or short_hash(f"{timestamp}:{git_sha}:{datetime.now(timezone.utc).isoformat()}", 6)
    nonce_value = slugify(nonce_value, max_length=6)
    if not re.fullmatch(r"[a-z0-9]{6}", nonce_value):
        raise ValueError("nonce must normalize to exactly 6 lowercase alphanumeric characters")
    return f"run_{timestamp}_{git_sha.lower()[:12]}_{nonce_value}"


def make_problem_id(tool: ToolName | str, statement: str) -> str:
    """Create problem_<tool>_<content hash>."""

    tool_value = tool.value if isinstance(tool, ToolName) else tool
    if tool_value not in {item.value for item in ToolName}:
        raise ValueError(f"unsupported tool: {tool_value}")
    return f"problem_{tool_value}_{short_hash(statement)}"


def make_attempt_id(attempt_number: int) -> str:
    """Create attempt_0001 style attempt IDs."""

    if attempt_number < 0 or attempt_number > 9999:
        raise ValueError("attempt_number must be in range 0..9999")
    return f"attempt_{attempt_number:04d}"


def make_candidate_id(attempt_id: str, producer: str, content: str) -> str:
    """Create cand_<attempt>_<producer>_<content hash>."""

    if not _ATTEMPT_ID_RE.match(attempt_id):
        raise ValueError(f"invalid attempt_id: {attempt_id}")
    attempt = attempt_id.removeprefix("attempt_")
    return f"cand_{attempt}_{slugify(producer, max_length=24)}_{short_hash(content)}"


def make_outcome_id(attempt_id: str, tool: ToolName | str, payload: bytes | str) -> str:
    """Create verify_<attempt>_<tool>_<payload hash>."""

    if not _ATTEMPT_ID_RE.match(attempt_id):
        raise ValueError(f"invalid attempt_id: {attempt_id}")
    tool_value = tool.value if isinstance(tool, ToolName) else tool
    if tool_value not in {item.value for item in ToolName}:
        raise ValueError(f"unsupported tool: {tool_value}")
    attempt = attempt_id.removeprefix("attempt_")
    return f"verify_{attempt}_{tool_value}_{short_hash(payload)}"


def run_date_from_id(run_id: str) -> str:
    """Extract YYYYMMDD from a canonical run ID."""

    if not _RUN_ID_RE.match(run_id):
        raise ValueError(f"invalid run_id: {run_id}")
    return run_id.split("_", 2)[1][:8]


def normalize_artifact_key(key: str) -> str:
    """Validate a POSIX-like relative artifact key."""

    normalized = key.replace("\\", "/")
    if normalized.startswith("/") or "/../" in normalized or normalized.startswith("../"):
        raise ValueError(f"artifact key must stay under artifact root: {key!r}")
    if "." in normalized.split("/"):
        raise ValueError(f"artifact key must not contain current-directory segments: {key!r}")
    if not _ARTIFACT_KEY_RE.match(normalized):
        raise ValueError(f"invalid artifact key: {key!r}")
    return normalized


def run_manifest_key(run_id: str) -> str:
    """Return the canonical RunManifest artifact key."""

    date = run_date_from_id(run_id)
    return f"runs/{date}/{run_id}/manifest.json"


def problem_spec_key(problem_id: str) -> str:
    """Return the canonical ProblemSpec artifact key."""

    if not _PROBLEM_ID_RE.match(problem_id):
        raise ValueError(f"invalid problem_id: {problem_id}")
    return f"problems/{problem_id}.json"


def candidate_key(run_id: str, candidate_id: str) -> str:
    """Return the canonical Candidate artifact key."""

    if not _CANDIDATE_ID_RE.match(candidate_id):
        raise ValueError(f"invalid candidate_id: {candidate_id}")
    date = run_date_from_id(run_id)
    return f"runs/{date}/{run_id}/candidates/{candidate_id}.json"


def verifier_outcome_key(run_id: str, outcome_id: str) -> str:
    """Return the canonical VerifierOutcome artifact key."""

    if not _OUTCOME_ID_RE.match(outcome_id):
        raise ValueError(f"invalid outcome_id: {outcome_id}")
    date = run_date_from_id(run_id)
    return f"runs/{date}/{run_id}/verifier/{outcome_id}.json"


def verifier_stream_key(run_id: str, attempt_id: str, tool: ToolName | str, stream: str) -> str:
    """Return the canonical stdout/stderr text artifact key for verifier output."""

    if not _ATTEMPT_ID_RE.match(attempt_id):
        raise ValueError(f"invalid attempt_id: {attempt_id}")
    if stream not in {"stdout", "stderr"}:
        raise ValueError("stream must be stdout or stderr")
    tool_value = tool.value if isinstance(tool, ToolName) else tool
    if tool_value not in {item.value for item in ToolName}:
        raise ValueError(f"unsupported tool: {tool_value}")
    date = run_date_from_id(run_id)
    return f"runs/{date}/{run_id}/verifier/{attempt_id}_{tool_value}.{stream}.txt"


def artifact_manifest_key(run_id: str) -> str:
    """Return the canonical ArtifactManifest artifact key."""

    date = run_date_from_id(run_id)
    return f"runs/{date}/{run_id}/artifacts.json"


def core_model_key(model: BaseModel) -> str:
    """Return the canonical artifact key for a supported core model."""

    if isinstance(model, RunManifest):
        return run_manifest_key(model.run_id)
    if isinstance(model, ProblemSpec):
        return problem_spec_key(model.problem_id)
    if isinstance(model, Candidate):
        return candidate_key(model.run_id, model.candidate_id)
    if isinstance(model, VerifierOutcome):
        return verifier_outcome_key(model.run_id, model.outcome_id)
    raise TypeError(f"unsupported core model: {type(model).__name__}")


def core_model_kind(model: BaseModel) -> ArtifactKind:
    """Return the ArtifactKind for a supported core model."""

    if isinstance(model, RunManifest):
        return ArtifactKind.RUN_MANIFEST
    if isinstance(model, ProblemSpec):
        return ArtifactKind.PROBLEM_SPEC
    if isinstance(model, Candidate):
        return ArtifactKind.CANDIDATE
    if isinstance(model, VerifierOutcome):
        return ArtifactKind.VERIFIER_OUTCOME
    raise TypeError(f"unsupported core model: {type(model).__name__}")


class ArtifactStore:
    """Filesystem-backed artifact store rooted at one directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def resolve(self, key: str) -> Path:
        """Resolve a normalized key under the artifact root."""

        normalized = normalize_artifact_key(key)
        path = (self.root / normalized).resolve()
        root = self.root.resolve()
        if root != path and root not in path.parents:
            raise ValueError(f"artifact key escapes root: {key!r}")
        return path

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
        """Write bytes and return a content-addressed record."""

        normalized = normalize_artifact_key(key)
        path = self.resolve(normalized)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return ArtifactRecord(
            key=normalized,
            path=normalized,
            kind=kind,
            sha256=sha256_bytes(payload),
            size_bytes=len(payload),
            media_type=media_type,
            encoding=encoding,
            created_at=datetime.now(timezone.utc),
            producer=producer,
            metadata=metadata or {},
        )

    def write_text(
        self,
        key: str,
        payload: str,
        *,
        kind: ArtifactKind,
        media_type: str = "text/plain",
        producer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        """Write UTF-8 text and return a content-addressed record."""

        return self.write_bytes(
            key,
            payload.encode("utf-8"),
            kind=kind,
            media_type=media_type,
            encoding=ArtifactEncoding.TEXT,
            producer=producer,
            metadata=metadata,
        )

    def write_json(
        self,
        key: str,
        payload: Any,
        *,
        kind: ArtifactKind,
        producer: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        """Write canonical JSON and return a content-addressed record."""

        return self.write_bytes(
            key,
            canonical_json_bytes(payload),
            kind=kind,
            media_type="application/json",
            encoding=ArtifactEncoding.JSON,
            producer=producer,
            metadata=metadata,
        )

    def write_model(self, model: BaseModel, *, producer: str | None = None) -> ArtifactRecord:
        """Write a supported Pydantic core model to its canonical key."""

        return self.write_json(
            core_model_key(model),
            model.model_dump(mode="json"),
            kind=core_model_kind(model),
            producer=producer,
        )

    def read_bytes(self, key: str) -> bytes:
        """Read bytes by normalized key."""

        return self.resolve(key).read_bytes()

    def read_text(self, key: str) -> str:
        """Read UTF-8 text by normalized key."""

        return self.read_bytes(key).decode("utf-8")

    def read_json(self, key: str) -> Any:
        """Read JSON by normalized key."""

        return json.loads(self.read_text(key))

    def verify_record(self, record: ArtifactRecord) -> bool:
        """Check that the stored payload still matches its sha256 and size."""

        payload = self.read_bytes(record.key)
        return sha256_bytes(payload) == record.sha256 and len(payload) == record.size_bytes

