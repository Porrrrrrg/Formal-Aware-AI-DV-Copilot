"""Lean CLI verifier adapter."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path

from adapters.common import (
    ROOT,
    artifact_ref,
    command_display,
    detect_version,
    elapsed_ms_since,
    fallback_diagnostic,
    verifier_artifact_dir,
    write_manifest,
    write_text,
)
from core.schemas import Candidate, Diagnostic, ProblemSpec, VerifierOutcome

LEAN_DIAG_RE = re.compile(
    r"^(?P<path>.*?):(?P<line>\d+):(?P<column>\d+):\s*"
    r"(?P<level>error|warning|information|info):\s*(?P<message>.*)$",
    re.IGNORECASE,
)


class LeanAdapter:
    tool = "lean"

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

    def verify(
        self,
        problem: ProblemSpec,
        candidate: Candidate,
        work_dir: Path | None = None,
    ) -> VerifierOutcome:
        if problem.language != "lean":
            raise ValueError(f"LeanAdapter only accepts Lean problems, got {problem.language}")

        started = time.monotonic()
        out_dir = work_dir or verifier_artifact_dir(
            self.artifact_root,
            candidate.run_id,
            candidate.attempt_id,
            self.tool,
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        input_path = out_dir / "candidate.lean"
        write_text(input_path, render_lean_input(problem, candidate))

        cmd, missing = self._build_command(input_path)
        write_text(out_dir / "run_command.txt", command_display(cmd) + "\n" if cmd else "")
        toolchain = {
            "lean": detect_version(self.lean_executable, ["--version"]),
            "lake": detect_version(self.lake_executable, ["--version"]),
        }

        if missing:
            stdout_ref = write_text(out_dir / "stdout.txt", "")
            stderr_text = missing + "\n"
            stderr_ref = write_text(out_dir / "stderr.txt", stderr_text)
            elapsed_ms = elapsed_ms_since(started)
            diagnostic = Diagnostic(level="error", message=missing, line=None, column=None)
            manifest_ref = write_manifest(
                out_dir / "manifest.json",
                run_id=candidate.run_id,
                status="blocked",
                toolchain=toolchain,
                artifacts_key=artifact_ref(out_dir),
                command=cmd,
                exit_code=-1,
                elapsed_ms=elapsed_ms,
            )
            return VerifierOutcome(
                ok=False,
                tool=self.tool,
                status="blocked",
                exit_code=-1,
                stdout_ref=stdout_ref,
                stderr_ref=stderr_ref,
                diagnostics=[diagnostic],
                artifact_refs=[artifact_ref(input_path), artifact_ref(out_dir / "run_command.txt")],
                manifest_ref=manifest_ref,
                elapsed_ms=elapsed_ms,
                metadata={"reason": "tool_unavailable"},
            )

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

        stdout_ref = write_text(out_dir / "stdout.txt", stdout)
        stderr_ref = write_text(out_dir / "stderr.txt", stderr)
        elapsed_ms = elapsed_ms_since(started)
        output = "\n".join(part for part in [stderr, stdout] if part)
        diagnostics = parse_lean_diagnostics(output)
        if exit_code != 0 and not diagnostics:
            diagnostics = [
                fallback_diagnostic(
                    "error",
                    f"Lean exited with code {exit_code}.",
                    output,
                )
            ]
        ok = exit_code == 0 and not any(item.level == "error" for item in diagnostics)
        status = "passed" if ok else "failed"
        manifest_ref = write_manifest(
            out_dir / "manifest.json",
            run_id=candidate.run_id,
            status=status,
            toolchain=toolchain,
            artifacts_key=artifact_ref(out_dir),
            command=cmd,
            exit_code=exit_code,
            elapsed_ms=elapsed_ms,
        )
        return VerifierOutcome(
            ok=ok,
            tool=self.tool,
            status=status,
            exit_code=exit_code,
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            diagnostics=diagnostics,
            artifact_refs=[artifact_ref(input_path), artifact_ref(out_dir / "run_command.txt")],
            manifest_ref=manifest_ref,
            elapsed_ms=elapsed_ms,
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
            normalized_level = "info"
        elif level == "warning":
            normalized_level = "warning"
        else:
            normalized_level = "error"
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
                source="lean",
            )
        )
    return diagnostics
