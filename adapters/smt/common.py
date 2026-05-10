"""Shared SMT-LIB CLI adapter logic."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from adapters.common import (
    ROOT,
    command_display,
    default_artifact_writer,
    detect_version,
    elapsed_ms_since,
    error_record,
    fallback_diagnostic,
    first_interesting_line,
    parse_line_column,
    tool_value,
    verifier_artifact_key,
    verifier_local_dir,
    verifier_stderr_key,
    verifier_stdout_key,
    write_local_text,
    write_text_artifact,
)
from app.core.artifacts import make_outcome_id, sha256_text
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
    VerifierOutcome,
    VerificationStatus,
)

SMT_STATUS_RE = re.compile(r"^(sat|unsat|unknown)\s*$", re.IGNORECASE)
ERROR_RE = re.compile(r"\b(error|parse error|syntax error|unsupported)\b", re.IGNORECASE)


class SmtCliAdapter:
    tool: ToolName

    def __init__(
        self,
        *,
        tool: ToolName | str,
        executable: str,
        solver_args: list[str],
        artifact_root: Path | None = None,
        timeout_s: int = 30,
    ) -> None:
        self.tool = ToolName(tool)
        self.executable = executable
        self.solver_args = list(solver_args)
        self.artifact_root = artifact_root
        self.timeout_s = timeout_s

    def probe(self) -> ToolProbe:
        resolved = shutil.which(self.executable)
        if resolved is None:
            return ToolProbe(
                tool=self.tool,
                available=False,
                executable=None,
                error=f"{self.executable} executable not found on PATH.",
            )
        return ToolProbe(
            tool=self.tool,
            available=True,
            version=detect_version(self.executable, ["--version"]),
            executable=resolved,
        )

    def supports(self, problem: ProblemSpec) -> bool:
        return problem.tool == self.tool and problem.language == Language.SMT2

    def verify(
        self,
        problem: ProblemSpec,
        candidate: Candidate,
        artifacts: ArtifactWriter | None = None,
    ) -> VerifierOutcome:
        if not self.supports(problem):
            raise ValueError(f"{self.tool} adapter only accepts SMT2 problems, got {problem.language}")
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
        input_name = f"{candidate.attempt_id}_{self.tool.value}.candidate.smt2"
        input_path = out_dir / input_name
        input_text = render_smt_input(problem, candidate)
        write_local_text(input_path, input_text)
        input_ref = write_text_artifact(
            writer,
            verifier_artifact_key(candidate.run_id, candidate.attempt_id, self.tool, "candidate.smt2"),
            input_text,
            kind=ArtifactKind.SMT2,
            producer=self.tool.value,
        )

        resolved = shutil.which(self.executable)
        cmd = [resolved or self.executable, *self.solver_args, str(input_path)]
        command_ref = write_text_artifact(
            writer,
            verifier_artifact_key(candidate.run_id, candidate.attempt_id, self.tool, "run_command.txt"),
            command_display(cmd) + "\n",
            kind=ArtifactKind.LOG,
            producer=self.tool.value,
            metadata={"argv": cmd},
        )
        version = detect_version(self.executable, ["--version"])
        artifact_refs = [input_ref, command_ref]

        if resolved is None:
            message = (
                f"{self.tool.value} solver blocked: {self.executable} executable not found on PATH."
            )
            stdout = ""
            stderr = message + "\n"
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
                diagnostics=[Diagnostic(level=DiagnosticLevel.ERROR, message=message)],
                artifact_refs=[*artifact_refs, stdout_ref, stderr_ref],
                error=error_record(ErrorKind.TOOL_NOT_FOUND, message, details={"executable": self.executable}),
                metadata={"reason": "tool_unavailable", "version": version},
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
            stderr += f"\n{self.tool.value} timed out after {self.timeout_s} seconds.\n"
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
        smt_status = parse_smt_status(stdout)
        diagnostics = parse_smt_diagnostics(stdout, stderr, self.tool)
        expected = expected_smt_status(problem)

        if timed_out:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    message=f"{self.tool.value} timed out after {self.timeout_s} seconds.",
                )
            )
        elif exit_code != 0 and not diagnostics:
            output = "\n".join(part for part in [stderr, stdout] if part)
            diagnostics = [
                fallback_diagnostic(
                    "error",
                    f"{self.tool} exited with code {exit_code}.",
                    output,
                )
            ]

        if expected and smt_status and smt_status != expected:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    message=f"Expected SMT result {expected} but solver returned {smt_status}.",
                )
            )

        has_error = bool(diagnostics) and any(item.level == DiagnosticLevel.ERROR for item in diagnostics)
        no_result_error = exit_code == 0 and smt_status is None and has_error_like_output(stdout, stderr)
        ok = exit_code == 0 and not has_error and not no_result_error and (
            smt_status is not None or expected is None
        )
        if exit_code == 0 and smt_status is None and not diagnostics:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    message="Solver completed without a sat/unsat/unknown result.",
                )
            )
            ok = False

        if timed_out:
            status = VerificationStatus.TIMEOUT
            outcome_error = error_record(
                ErrorKind.TOOL_TIMEOUT,
                f"{self.tool.value} timed out after {self.timeout_s} seconds.",
                retryable=True,
                details={"timeout_s": self.timeout_s},
            )
        elif ok:
            status = VerificationStatus.PASSED
            outcome_error = None
        elif smt_status == "unknown" and not has_error:
            status = VerificationStatus.UNKNOWN
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
            metadata={"expected": expected, "smt_status": smt_status, "version": version},
            timed_out=timed_out,
        )

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
        payload = json.dumps(
            {
                "candidate_id": candidate.candidate_id,
                "exit_code": exit_code,
                "status": status.value,
                "stderr_sha256": sha256_text(stderr),
                "stdout_sha256": sha256_text(stdout),
                "tool": self.tool.value,
            },
            sort_keys=True,
        )
        return VerifierOutcome(
            outcome_id=make_outcome_id(candidate.attempt_id, self.tool, payload),
            run_id=candidate.run_id,
            problem_id=problem.problem_id,
            candidate_id=candidate.candidate_id,
            attempt_id=candidate.attempt_id,
            ok=status == VerificationStatus.PASSED,
            tool=self.tool,
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


def render_smt_input(problem: ProblemSpec, candidate: Candidate) -> str:
    content = candidate.content.strip() or problem.statement.strip()
    return content + "\n"


def expected_smt_status(problem: ProblemSpec) -> str | None:
    for key in ("expect", "expected", "smt_status"):
        value = problem.metadata.get(key)
        if isinstance(value, str) and value.lower() in {"sat", "unsat", "unknown"}:
            return value.lower()
    return None


def parse_smt_status(stdout: str) -> str | None:
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        match = SMT_STATUS_RE.match(line)
        if match:
            return match.group(1).lower()
    return None


def parse_smt_diagnostics(stdout: str, stderr: str, tool: ToolName | str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for stream_name, text in [("stderr", stderr), ("stdout", stdout)]:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or not ERROR_RE.search(line):
                continue
            line_no, column = parse_line_column(line)
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    message=clean_smt_message(line),
                    line=line_no,
                    column=column,
                    code=f"{tool_value(tool)}:{stream_name}",
                )
            )
    if diagnostics:
        return diagnostics
    combined = "\n".join(part for part in [stderr, stdout] if part)
    if has_error_like_output(stdout, stderr):
        line_no, column = parse_line_column(combined)
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                message=first_interesting_line(combined) or "SMT solver reported an error.",
                line=line_no,
                column=column,
                code=tool_value(tool),
            )
        )
    return diagnostics


def has_error_like_output(stdout: str, stderr: str) -> bool:
    return ERROR_RE.search(stdout) is not None or ERROR_RE.search(stderr) is not None


def clean_smt_message(message: str) -> str:
    if message.startswith("(error "):
        return message.removeprefix("(error ").rstrip(")").strip().strip('"')
    return message
