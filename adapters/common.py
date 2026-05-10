"""Shared helper functions for canonical verifier adapters."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from app.core.artifacts import (
    ArtifactStore,
    run_date_from_id,
    verifier_stream_key,
)
from app.core.protocols import ArtifactWriter
from app.models.core import (
    ArtifactEncoding,
    ArtifactKind,
    Diagnostic,
    ErrorKind,
    ErrorRecord,
    ToolName,
)

ROOT = Path(__file__).resolve().parents[1]


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
