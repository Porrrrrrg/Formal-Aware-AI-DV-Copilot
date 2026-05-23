#!/usr/bin/env python3
"""Test the JasperLoop-DV JSON backend contract without running benchmarks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TINY_PROMPT = 'Return exactly this JSON object: {"ok": true, "message": "healthcheck"}'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", help="Backend command. Defaults to JASPERLOOP_LLM_CMD or codex_json.py.")
    parser.add_argument("--schema", type=Path, help="Optional schema argument passed to codex_json.py route.")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    command, shell = resolve_command(args)
    result = run_contract(command, shell=shell, timeout_s=args.timeout)
    if result["ok"]:
        print("backend_contract: ok")
        return 0
    print("backend_contract: failed")
    print(f"classification: {result['classification']}")
    if result.get("error"):
        print(f"error: {result['error']}")
    if result.get("stderr"):
        print(f"stderr: {result['stderr']}")
    if result.get("stdout"):
        print(f"stdout: {result['stdout']}")
    print("suggestion: set CODEX_BIN or JASPERLOOP_LLM_CMD to a noninteractive command that reads stdin and writes one JSON object to stdout.")
    return 1


def resolve_command(args: argparse.Namespace) -> tuple[list[str] | str, bool]:
    if args.cmd:
        return args.cmd, True
    env_cmd = os.environ.get("JASPERLOOP_LLM_CMD")
    if env_cmd:
        return env_cmd, True
    command = [
        sys.executable,
        str(ROOT / "copilot" / "llm_adapters" / "codex_json.py"),
        "--cd",
        str(ROOT),
        "--timeout",
        str(args.timeout),
    ]
    if args.schema:
        command.extend(["--schema", str(args.schema)])
    return command, False


def run_contract(command: list[str] | str, shell: bool = False, timeout_s: int = 30) -> dict[str, object]:
    try:
        completed = subprocess.run(
            command,
            input=TINY_PROMPT,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
            cwd=ROOT,
            shell=shell,
        )
    except subprocess.TimeoutExpired as exc:
        return failure("command_timeout", error=str(exc))
    except PermissionError as exc:
        return failure("permission_denied", error=str(exc))
    except FileNotFoundError as exc:
        return failure("missing_executable", error=str(exc))
    except OSError as exc:
        classification = "permission_denied" if getattr(exc, "winerror", None) == 5 else "unknown_error"
        return failure(classification, error=str(exc))

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        classification = "permission_denied" if "access is denied" in stderr.lower() else "nonzero_exit"
        return failure(classification, stdout=stdout, stderr=stderr, returncode=completed.returncode)
    if not stdout:
        return failure("empty_stdout", stderr=stderr, returncode=completed.returncode)
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return failure("invalid_json", stdout=stdout, stderr=stderr, error=str(exc), returncode=completed.returncode)
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return failure(
            "invalid_json",
            stdout=stdout,
            stderr=stderr,
            error="backend JSON did not contain ok=true",
            returncode=completed.returncode,
        )
    return {"ok": True, "classification": "ok", "json": payload, "returncode": completed.returncode}


def failure(
    classification: str,
    error: str = "",
    stdout: str = "",
    stderr: str = "",
    returncode: int | None = None,
) -> dict[str, object]:
    return {
        "ok": False,
        "classification": classification,
        "error": error[:500],
        "stdout": stdout[:500],
        "stderr": stderr[:500],
        "returncode": returncode,
    }


if __name__ == "__main__":
    raise SystemExit(main())
