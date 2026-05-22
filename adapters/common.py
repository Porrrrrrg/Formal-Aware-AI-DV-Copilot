"""Shared helper functions for canonical verifier adapters."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from app.core.artifacts import (
    ArtifactStore,
    make_attempt_id,
    make_candidate_id,
    make_outcome_id,
    make_problem_id,
    make_run_id,
    run_date_from_id,
    sha256_text,
    verifier_stream_key,
)
from app.core.protocols import ArtifactWriter
from app.models.core import (
    ArtifactEncoding,
    ArtifactKind,
    Candidate,
    Diagnostic,
    ErrorKind,
    ErrorRecord,
    Language,
    ProblemSpec,
    ToolName,
    VerificationStatus,
    VerifierOutcome,
)

ROOT = Path(__file__).resolve().parents[1]
ZERO_GIT_SHA = "0" * 12


def default_artifact_root() -> Path:
    return ROOT / "artifacts"


def default_artifact_writer(artifact_root: Path | None) -> ArtifactStore:
    """Return the filesystem artifact writer used when no writer is supplied."""

    return ArtifactStore(artifact_root or default_artifact_root())


def tool_value(tool: ToolName | str) -> str:
    return tool.value if isinstance(tool, ToolName) else tool


def verifier_local_dir(
    artifact_root: Path | None,
    run_id: str,
    attempt_id: str,
    tool: ToolName | str,
) -> Path:
    root = artifact_root or default_artifact_root()
    return root / "runs" / run_date_from_id(run_id) / run_id / "verifier"


def verifier_artifact_key(
    run_id: str,
    attempt_id: str,
    tool: ToolName | str,
    suffix: str,
) -> str:
    """Return a canonical verifier artifact key for non-stream files."""

    return f"runs/{run_date_from_id(run_id)}/{run_id}/verifier/{attempt_id}_{tool_value(tool)}.{suffix}"


def verifier_stdout_key(run_id: str, attempt_id: str, tool: ToolName | str) -> str:
    return verifier_stream_key(run_id, attempt_id, tool, "stdout")


def verifier_stderr_key(run_id: str, attempt_id: str, tool: ToolName | str) -> str:
    return verifier_stream_key(run_id, attempt_id, tool, "stderr")


def write_local_text(path: Path, text: str) -> None:
    """Write a local execution file used by subprocess-based tools."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_text_artifact(
    artifacts: ArtifactWriter,
    key: str,
    text: str,
    *,
    kind: ArtifactKind,
    producer: str | None = None,
    media_type: str = "text/plain",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Persist text through the canonical artifact writer and return its key."""

    record = artifacts.write_bytes(
        key,
        text.encode("utf-8"),
        kind=kind,
        media_type=media_type,
        encoding=ArtifactEncoding.TEXT,
        producer=producer,
        metadata=metadata,
    )
    return record.key


def git_sha() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return "0" * 12
    sha = completed.stdout.strip().lower()
    return sha if sha else "0" * 12


def canonical_git_sha() -> str:
    sha = git_sha()
    if re.fullmatch(r"[a-f0-9]{7,64}", sha):
        return sha
    return ZERO_GIT_SHA


def detect_version(executable: str, args: list[str]) -> str | None:
    resolved = shutil.which(executable)
    if resolved is None:
        return None
    try:
        completed = subprocess.run(
            [resolved, *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (completed.stdout or completed.stderr).strip()
    return text.splitlines()[0] if text else None


def command_display(cmd: list[str]) -> str:
    return " ".join(cmd)


def elapsed_ms_since(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def parse_line_column(text: str) -> tuple[int | None, int | None]:
    patterns = [
        re.compile(r"\bline\s+(?P<line>\d+)\s+column\s+(?P<column>\d+)\b", re.IGNORECASE),
        re.compile(r"\bline\s+(?P<line>\d+),\s*column\s+(?P<column>\d+)\b", re.IGNORECASE),
        re.compile(r":(?P<line>\d+)\.(?P<column>\d+):"),
        re.compile(r":(?P<line>\d+):(?P<column>\d+):"),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return int(match.group("line")), int(match.group("column"))
    return None, None


def fallback_diagnostic(level: str, message: str, output: str = "") -> Diagnostic:
    line, column = parse_line_column(output)
    cleaned = message.strip()
    if not cleaned and output.strip():
        cleaned = first_interesting_line(output)
    if not cleaned:
        cleaned = "Verifier did not provide a diagnostic message."
    return Diagnostic(level=level, message=cleaned, line=line, column=column)


def error_record(
    kind: ErrorKind,
    message: str,
    *,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> ErrorRecord:
    return ErrorRecord(kind=kind, message=message, retryable=retryable, details=details or {})


def first_interesting_line(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line:
            return line
    return ""


def language_for_tool(tool: ToolName) -> Language:
    return {
        ToolName.LEAN: Language.LEAN,
        ToolName.ROCQ: Language.ROCQ,
        ToolName.ISABELLE: Language.ISABELLE,
        ToolName.Z3: Language.SMT2,
        ToolName.CVC5: Language.SMT2,
    }[tool]


def canonical_input_error(
    problem: object,
    candidate: object,
    *,
    tool: ToolName | str,
    artifact_root: Path | None,
) -> VerifierOutcome | None:
    if isinstance(problem, ProblemSpec) and isinstance(candidate, Candidate):
        return None
    return schema_drift_outcome(
        problem,
        candidate,
        tool=tool,
        artifact_root=artifact_root,
        message=(
            "Adapter received legacy or non-canonical input. "
            "Use app.models.core.ProblemSpec and app.models.core.Candidate."
        ),
    )


def schema_drift_outcome(
    problem: object,
    candidate: object,
    *,
    tool: ToolName | str,
    artifact_root: Path | None,
    message: str,
) -> VerifierOutcome:
    tool_name = ToolName(tool)
    statement = str(getattr(candidate, "content", "") or getattr(problem, "statement", "") or message)
    attempt_id = make_attempt_id(0)
    run_id = make_run_id(canonical_git_sha())
    problem_id = make_problem_id(tool_name, statement)
    candidate_id = make_candidate_id(attempt_id, "legacy_adapter", statement)
    canonical_problem = ProblemSpec(
        problem_id=problem_id,
        tool=tool_name,
        language=language_for_tool(tool_name),
        statement=statement,
        metadata={"legacy_problem_type": type(problem).__name__},
    )
    canonical_candidate = Candidate(
        candidate_id=candidate_id,
        run_id=run_id,
        problem_id=problem_id,
        attempt_id=attempt_id,
        producer="legacy_adapter",
        content=statement,
        metadata={"legacy_candidate_type": type(candidate).__name__},
    )
    writer = default_artifact_writer(artifact_root)
    stdout_ref = write_text_artifact(
        writer,
        verifier_stdout_key(run_id, attempt_id, tool_name),
        "",
        kind=ArtifactKind.STDOUT,
        producer=tool_name.value,
    )
    stderr_ref = write_text_artifact(
        writer,
        verifier_stderr_key(run_id, attempt_id, tool_name),
        message + "\n",
        kind=ArtifactKind.STDERR,
        producer=tool_name.value,
    )
    diagnostic = Diagnostic(level="error", message=message, code=ErrorKind.SCHEMA_DRIFT.value)
    return make_verifier_outcome(
        problem=canonical_problem,
        candidate=canonical_candidate,
        tool=tool_name,
        status=VerificationStatus.ERROR,
        exit_code=-1,
        stdout="",
        stderr=message + "\n",
        stdout_ref=stdout_ref,
        stderr_ref=stderr_ref,
        diagnostics=[diagnostic],
        artifact_refs=[stdout_ref, stderr_ref],
        error=error_record(ErrorKind.SCHEMA_DRIFT, message),
        metadata={
            "reason": "legacy_adapter_contract",
            "legacy_problem_type": type(problem).__name__,
            "legacy_candidate_type": type(candidate).__name__,
        },
    )


def make_verifier_outcome(
    *,
    problem: ProblemSpec,
    candidate: Candidate,
    tool: ToolName | str,
    status: VerificationStatus,
    exit_code: int,
    stdout: str,
    stderr: str,
    stdout_ref: str,
    stderr_ref: str,
    diagnostics: list[Diagnostic],
    artifact_refs: list[str],
    elapsed_ms: int | None = None,
    error: ErrorRecord | None = None,
    metadata: dict[str, object] | None = None,
    timed_out: bool = False,
) -> VerifierOutcome:
    tool_name = ToolName(tool)
    payload = json.dumps(
        {
            "candidate_id": candidate.candidate_id,
            "exit_code": exit_code,
            "status": status.value,
            "stderr_sha256": sha256_text(stderr),
            "stdout_sha256": sha256_text(stdout),
            "tool": tool_name.value,
        },
        sort_keys=True,
    )
    return VerifierOutcome(
        outcome_id=make_outcome_id(candidate.attempt_id, tool_name, payload),
        run_id=candidate.run_id,
        problem_id=problem.problem_id,
        candidate_id=candidate.candidate_id,
        attempt_id=candidate.attempt_id,
        ok=status == VerificationStatus.PASSED,
        tool=tool_name,
        status=status,
        exit_code=exit_code,
        elapsed_ms=elapsed_ms,
        timed_out=timed_out,
        stdout_ref=stdout_ref,
        stderr_ref=stderr_ref,
        diagnostics=diagnostics,
        artifact_refs=artifact_refs,
        error=error,
        metadata=metadata or {},
    )
