"""Lean CLI verifier adapter."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

from adapters.common import (
    ROOT,
    canonical_input_error,
    command_display,
    default_artifact_writer,
    detect_version,
    elapsed_ms_since,
    error_record,
    fallback_diagnostic,
    make_verifier_outcome,
    verifier_artifact_key,
    verifier_local_dir,
    verifier_stderr_key,
    verifier_stdout_key,
    write_local_text,
    write_text_artifact,
)
from app.core.protocols import ArtifactWriter, ToolProbe
from app.models.core import (
    ArtifactKind,
    Candidate,
    Diagnostic,
    DiagnosticLevel,
    ErrorKind,
    ErrorRecord,
    Language,
    ProblemSpec,
    ToolName,
    VerificationStatus,
    VerifierOutcome,
)

LEAN_DIAG_RE = re.compile(
    r"^(?P<path>.*?):(?P<line>\d+):(?P<column>\d+):\s*"
    r"(?P<level>error|warning|information|info):\s*(?P<message>.*)$",
    re.IGNORECASE,
)


class LeanAdapter:
    tool = ToolName.LEAN

    def __init__(
        self,
        artifact_root: Path | None = None,
        lean_executable: str = "lean",
        lake_executable: str = "lake",
        timeout_s: int = 30,
        use_lake: bool | None = None,
    ) -> None:
        self.artifact_root = artifact_root
        self.lean_executable = lean_executable
        self.lake_executable = lake_executable
        self.timeout_s = timeout_s
        self.use_lake = use_lake

    def probe(self) -> ToolProbe:
        resolved = shutil.which(self.lean_executable)
        if resolved is None:
            return ToolProbe(
                tool=self.tool,
                available=False,
                executable=None,
                error=f"{self.lean_executable} executable not found on PATH.",
            )
        return ToolProbe(
            tool=self.tool,
            available=True,
            version=detect_version(self.lean_executable, ["--version"]),
            executable=resolved,
        )

    def supports(self, problem: ProblemSpec) -> bool:
        return problem.tool == self.tool and problem.language == Language.LEAN

    def verify(
        self,
        problem: ProblemSpec,
        candidate: Candidate,
        artifacts: ArtifactWriter | None = None,
    ) -> VerifierOutcome:
        input_error = canonical_input_error(
            problem,
            candidate,
            tool=self.tool,
            artifact_root=self.artifact_root,
        )
        if input_error is not None:
            return input_error
        if not self.supports(problem):
            raise ValueError(f"LeanAdapter only accepts Lean problems, got {problem.language}")
        if problem.problem_id != candidate.problem_id:
            raise ValueError("candidate.problem_id must match problem.problem_id")

        started = time.monotonic()
        writer = artifacts or default_artifact_writer(self.artifact_root)
        out_dir = verifier_local_dir(
            self.artifact_root,
            candidate.run_id,
            candidate.attempt_id,
            self.tool,
        )
        input_path = out_dir / f"{candidate.attempt_id}_{self.tool.value}.candidate.lean"
        input_text = render_lean_input(problem, candidate)
        write_local_text(input_path, input_text)
        input_ref = write_text_artifact(
            writer,
            verifier_artifact_key(candidate.run_id, candidate.attempt_id, self.tool, "candidate.lean"),
            input_text,
            kind=ArtifactKind.PROOF_SCRIPT,
            producer=self.tool.value,
        )

        cmd, missing = self._build_command(input_path)
        command_ref = write_text_artifact(
            writer,
            verifier_artifact_key(candidate.run_id, candidate.attempt_id, self.tool, "run_command.txt"),
            command_display(cmd) + "\n" if cmd else "",
            kind=ArtifactKind.LOG,
            producer=self.tool.value,
            metadata={"argv": cmd},
        )
        artifact_refs = [input_ref, command_ref]
        toolchain = {
            "lean": detect_version(self.lean_executable, ["--version"]),
            "lake": detect_version(self.lake_executable, ["--version"]),
        }

        if missing:
            stdout = ""
            stderr = missing + "\n"
            stdout_ref = write_text_artifact(
                writer,
                verifier_stdout_key(candidate.run_id, candidate.attempt_id, self.tool),
                stdout,
                kind=ArtifactKind.STDOUT,
                producer=self.tool.value,
            )
            stderr_ref = write_text_artifact(
                writer,
                verifier_stderr_key(candidate.run_id, candidate.attempt_id, self.tool),
                stderr,
                kind=ArtifactKind.STDERR,
                producer=self.tool.value,
            )
            elapsed_ms = elapsed_ms_since(started)
            return self._outcome(
                problem=problem,
                candidate=candidate,
                status=VerificationStatus.BLOCKED,
                exit_code=-1,
                elapsed_ms=elapsed_ms,
                stdout=stdout,
                stderr=stderr,
                stdout_ref=stdout_ref,
                stderr_ref=stderr_ref,
                diagnostics=[Diagnostic(level=DiagnosticLevel.ERROR, message=missing)],
                artifact_refs=[*artifact_refs, stdout_ref, stderr_ref],
                error=error_record(
                    ErrorKind.TOOL_NOT_FOUND,
                    missing,
                    details={"lean_executable": self.lean_executable, "lake_executable": self.lake_executable},
                ),
                metadata={"reason": "tool_unavailable", "toolchain": toolchain},
            )

        timed_out = False
        try:
            completed = subprocess.run(
                cmd,
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=self.timeout_s,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            stderr += f"\nLean timed out after {self.timeout_s} seconds.\n"
            exit_code = 124
            timed_out = True

        stdout_ref = write_text_artifact(
            writer,
            verifier_stdout_key(candidate.run_id, candidate.attempt_id, self.tool),
            stdout,
            kind=ArtifactKind.STDOUT,
            producer=self.tool.value,
        )
        stderr_ref = write_text_artifact(
            writer,
            verifier_stderr_key(candidate.run_id, candidate.attempt_id, self.tool),
            stderr,
            kind=ArtifactKind.STDERR,
            producer=self.tool.value,
        )
        artifact_refs.extend([stdout_ref, stderr_ref])
        elapsed_ms = elapsed_ms_since(started)
        output = "\n".join(part for part in [stderr, stdout] if part)
        diagnostics = parse_lean_diagnostics(output)
        if timed_out:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    message=f"Lean timed out after {self.timeout_s} seconds.",
                )
            )
        elif exit_code != 0 and not diagnostics:
            diagnostics = [
                fallback_diagnostic(
                    "error",
                    f"Lean exited with code {exit_code}.",
                    output,
                )
            ]

        has_error = any(item.level == DiagnosticLevel.ERROR for item in diagnostics)
        if timed_out:
            status = VerificationStatus.TIMEOUT
            outcome_error = error_record(
                ErrorKind.TOOL_TIMEOUT,
                f"Lean timed out after {self.timeout_s} seconds.",
                retryable=True,
                details={"timeout_s": self.timeout_s},
            )
        elif exit_code == 0 and not has_error:
            status = VerificationStatus.PASSED
            outcome_error = None
        else:
            status = VerificationStatus.FAILED
            outcome_error = None

        return self._outcome(
            problem=problem,
            candidate=candidate,
            status=status,
            exit_code=exit_code,
            elapsed_ms=elapsed_ms,
            stdout=stdout,
            stderr=stderr,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            diagnostics=diagnostics,
            artifact_refs=artifact_refs,
            error=outcome_error,
            metadata={"toolchain": toolchain},
            timed_out=timed_out,
        )

    def _build_command(self, input_path: Path) -> tuple[list[str], str | None]:
        lake_project = (ROOT / "lakefile.lean").exists() or (ROOT / "lakefile.toml").exists()
        lake_path = shutil.which(self.lake_executable)
        lean_path = shutil.which(self.lean_executable)
        should_use_lake = self.use_lake is True or (
            self.use_lake is None and lake_project and lake_path is not None
        )
        if should_use_lake:
            if lake_path is None:
                return [self.lake_executable, "env", "lean", str(input_path)], (
                    "Lean toolchain blocked: lake executable not found on PATH."
                )
            return [lake_path, "env", "lean", str(input_path)], None
        if lean_path is None:
            return [self.lean_executable, str(input_path)], (
                "Lean toolchain blocked: lean executable not found on PATH."
            )
        return [lean_path, str(input_path)], None

    def _outcome(
        self,
        *,
        problem: ProblemSpec,
        candidate: Candidate,
        status: VerificationStatus,
        exit_code: int,
        elapsed_ms: int,
        stdout: str,
        stderr: str,
        stdout_ref: str,
        stderr_ref: str,
        diagnostics: list[Diagnostic],
        artifact_refs: list[str],
        error: ErrorRecord | None = None,
        metadata: dict[str, object] | None = None,
        timed_out: bool = False,
    ) -> VerifierOutcome:
        return make_verifier_outcome(
            problem=problem,
            candidate=candidate,
            tool=self.tool,
            status=status,
            exit_code=exit_code,
            elapsed_ms=elapsed_ms,
            stdout=stdout,
            stderr=stderr,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            diagnostics=diagnostics,
            artifact_refs=artifact_refs,
            error=error,
            metadata=metadata,
            timed_out=timed_out,
        )


def render_lean_input(problem: ProblemSpec, candidate: Candidate) -> str:
    content = candidate.content.strip() or problem.statement.strip()
    return content + "\n"


def parse_lean_diagnostics(output: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lines = output.splitlines()
    for index, line in enumerate(lines):
        match = LEAN_DIAG_RE.match(line.strip())
        if not match:
            continue
        level = match.group("level").lower()
        if level in {"information", "info"}:
            normalized_level = DiagnosticLevel.INFO
        elif level == "warning":
            normalized_level = DiagnosticLevel.WARNING
        else:
            normalized_level = DiagnosticLevel.ERROR
        message_parts = [match.group("message").strip()]
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].startswith((" ", "\t")):
            continuation = lines[cursor].strip()
            if continuation:
                message_parts.append(continuation)
            cursor += 1
        diagnostics.append(
            Diagnostic(
                level=normalized_level,
                message="\n".join(part for part in message_parts if part),
                line=int(match.group("line")),
                column=int(match.group("column")),
                code="lean",
            )
        )
    return diagnostics
