#!/usr/bin/env python3
"""Diagnose JasperLoop-DV noninteractive LLM backend availability."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TINY_PROMPT = 'Return exactly this JSON object: {"ok": true, "message": "healthcheck"}'
STATUS_OK = "ok"
STATUS_MISSING_EXECUTABLE = "missing_executable"
STATUS_PERMISSION_DENIED = "permission_denied"
STATUS_COMMAND_TIMEOUT = "command_timeout"
STATUS_NONZERO_EXIT = "nonzero_exit"
STATUS_INVALID_JSON = "invalid_json"
STATUS_EMPTY_STDOUT = "empty_stdout"
STATUS_INTERACTIVE_ONLY = "interactive_only"
STATUS_UNKNOWN_ERROR = "unknown_error"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Write machine-readable JSON only.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    result = diagnose_backend(timeout_s=args.timeout)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_human_summary(result)
    if result["backend_available"]:
        return 0
    if result["configured"]:
        return 1
    return 2


def diagnose_backend(
    env: dict[str, str] | None = None,
    timeout_s: int = 20,
    cwd: Path = ROOT,
) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    candidates = collect_codex_candidates(env)
    candidate_reports = [inspect_executable(candidate["label"], candidate["path"], timeout_s) for candidate in candidates]
    configured = bool(env.get("JASPERLOOP_LLM_CMD") or env.get("CODEX_BIN") or candidates)
    selected_backend = select_backend(env, candidates)
    contract = run_backend_contract(selected_backend, env, timeout_s, cwd) if configured else no_backend_contract()
    return {
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "cwd": str(cwd),
        "env": {
            "CODEX_BIN": env.get("CODEX_BIN", ""),
            "CODEX_BIN_SET": bool(env.get("CODEX_BIN")),
            "JASPERLOOP_LLM_CMD_SET": bool(env.get("JASPERLOOP_LLM_CMD")),
        },
        "path_lookup": {
            "codex": which_with_env("codex", env),
            "codex.exe": which_with_env("codex.exe", env),
        },
        "candidates": candidate_reports,
        "configured": configured,
        "selected_backend": selected_backend,
        "contract": contract,
        "backend_available": contract.get("status") == STATUS_OK,
    }


def collect_codex_candidates(env: dict[str, str]) -> list[dict[str, str]]:
    raw_candidates: list[dict[str, str]] = []
    if env.get("CODEX_BIN"):
        raw_candidates.append({"label": "CODEX_BIN", "path": str(env["CODEX_BIN"])})
    for name in ("codex.exe", "codex"):
        found = which_with_env(name, env)
        if found:
            raw_candidates.append({"label": f"PATH:{name}", "path": found})

    seen: set[str] = set()
    candidates = []
    for item in raw_candidates:
        key = item["path"].lower() if sys.platform == "win32" else item["path"]
        if key not in seen:
            seen.add(key)
            candidates.append(item)
    return candidates


def which_with_env(name: str, env: dict[str, str]) -> str | None:
    return shutil.which(name, path=env.get("PATH"))


def inspect_executable(label: str, executable: str, timeout_s: int = 10) -> dict[str, Any]:
    path = Path(executable)
    exists = path.exists()
    is_file = path.is_file()
    access = os.access(path, os.X_OK) if exists else False
    report: dict[str, Any] = {
        "label": label,
        "path": executable,
        "exists": exists,
        "is_file": is_file,
        "executable_access": access,
        "parent_listing": parent_listing(path),
    }
    if not exists:
        report["short_command_test"] = {"status": STATUS_MISSING_EXECUTABLE}
        return report
    if not is_file:
        report["short_command_test"] = {"status": STATUS_MISSING_EXECUTABLE, "error": "not a file"}
        return report
    report["short_command_test"] = run_command([executable, "--version"], timeout_s=timeout_s)
    return report


def parent_listing(path: Path, limit: int = 20) -> dict[str, Any]:
    parent = path.parent
    try:
        if not parent.exists():
            return {"available": False, "error": "parent_missing"}
        entries = [child.name for child in parent.iterdir()]
        return {"available": True, "path": str(parent), "entries": sorted(entries)[:limit]}
    except OSError as exc:
        return {"available": False, "path": str(parent), "error": short_error(exc)}


def select_backend(env: dict[str, str], candidates: list[dict[str, str]]) -> dict[str, str] | None:
    if env.get("JASPERLOOP_LLM_CMD"):
        return {"route": "generic_command", "command": env["JASPERLOOP_LLM_CMD"]}
    if env.get("CODEX_BIN"):
        return {"route": "codex_cli", "executable": env["CODEX_BIN"], "source": "CODEX_BIN"}
    if candidates:
        return {"route": "codex_cli", "executable": candidates[0]["path"], "source": candidates[0]["label"]}
    return None


def no_backend_contract() -> dict[str, Any]:
    return {
        "status": STATUS_MISSING_EXECUTABLE,
        "route": "none",
        "summary": "No JASPERLOOP_LLM_CMD, CODEX_BIN, codex, or codex.exe backend was found.",
    }


def run_backend_contract(
    backend: dict[str, str] | None,
    env: dict[str, str],
    timeout_s: int,
    cwd: Path,
) -> dict[str, Any]:
    if backend is None:
        return no_backend_contract()
    if backend["route"] == "generic_command":
        result = run_command(
            backend["command"],
            input_text=TINY_PROMPT,
            timeout_s=timeout_s,
            cwd=cwd,
            shell=True,
        )
        result["route"] = "generic_command"
        return validate_json_contract(result)

    codex_env = dict(env)
    codex_env["CODEX_BIN"] = backend["executable"]
    cmd = [
        sys.executable,
        str(ROOT / "copilot" / "llm_adapters" / "codex_json.py"),
        "--cd",
        str(cwd),
        "--timeout",
        str(timeout_s),
    ]
    result = run_command(cmd, input_text=TINY_PROMPT, timeout_s=timeout_s + 5, cwd=cwd, env=codex_env)
    result["route"] = "codex_cli"
    result["executable"] = backend["executable"]
    return validate_json_contract(result)


def run_command(
    command: list[str] | str,
    input_text: str = "",
    timeout_s: int = 10,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    shell: bool = False,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_s,
            cwd=cwd,
            env=env,
            shell=shell,
        )
    except subprocess.TimeoutExpired as exc:
        return {"status": STATUS_COMMAND_TIMEOUT, "error": short_error(exc), "returncode": 124}
    except PermissionError as exc:
        return {"status": STATUS_PERMISSION_DENIED, "error": short_error(exc), "returncode": 127}
    except FileNotFoundError as exc:
        return {"status": STATUS_MISSING_EXECUTABLE, "error": short_error(exc), "returncode": 127}
    except OSError as exc:
        status = STATUS_PERMISSION_DENIED if getattr(exc, "winerror", None) == 5 else STATUS_UNKNOWN_ERROR
        return {"status": status, "error": short_error(exc), "returncode": 127}

    status = classify_completed_process(completed)
    return {
        "status": status,
        "returncode": completed.returncode,
        "stdout_preview": preview(completed.stdout),
        "stderr_preview": preview(completed.stderr),
    }


def classify_completed_process(completed: subprocess.CompletedProcess[str]) -> str:
    stderr = (completed.stderr or "").lower()
    stdout = completed.stdout or ""
    if completed.returncode != 0:
        if "access is denied" in stderr or "permission denied" in stderr:
            return STATUS_PERMISSION_DENIED
        if "tty" in stderr or "interactive" in stderr or "terminal" in stderr:
            return STATUS_INTERACTIVE_ONLY
        return STATUS_NONZERO_EXIT
    if not stdout.strip():
        return STATUS_EMPTY_STDOUT
    return STATUS_OK


def validate_json_contract(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") != STATUS_OK:
        result["json_valid"] = False
        return result
    stdout = str(result.get("stdout_preview", "")).strip()
    if not stdout:
        result["status"] = STATUS_EMPTY_STDOUT
        result["json_valid"] = False
        return result
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        result["status"] = STATUS_INVALID_JSON
        result["json_valid"] = False
        result["json_error"] = short_error(exc)
        return result
    result["json_valid"] = isinstance(payload, dict)
    result["json_object"] = payload if isinstance(payload, dict) else None
    if not isinstance(payload, dict):
        result["status"] = STATUS_INVALID_JSON
    elif payload.get("ok") is not True:
        result["status"] = STATUS_INVALID_JSON
        result["json_error"] = "JSON object did not contain ok=true."
    return result


def short_error(exc: BaseException, max_chars: int = 300) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return text[:max_chars]


def preview(text: str | None, max_chars: int = 1200) -> str:
    if not text:
        return ""
    text = text.strip()
    return text[:max_chars]


def print_human_summary(result: dict[str, Any]) -> None:
    print("LLM backend doctor")
    print(f"  python: {result['python_executable']}")
    print(f"  platform: {result['platform']}")
    print(f"  cwd: {result['cwd']}")
    print(f"  CODEX_BIN set: {result['env']['CODEX_BIN_SET']}")
    if result["env"]["CODEX_BIN_SET"]:
        print(f"  CODEX_BIN: {result['env']['CODEX_BIN']}")
    print(f"  JASPERLOOP_LLM_CMD set: {result['env']['JASPERLOOP_LLM_CMD_SET']}")
    print(f"  PATH codex: {result['path_lookup']['codex']}")
    print(f"  PATH codex.exe: {result['path_lookup']['codex.exe']}")
    print("  candidates:")
    for candidate in result["candidates"]:
        short = candidate.get("short_command_test", {})
        print(
            "    - "
            f"{candidate['label']}: exists={candidate['exists']} "
            f"is_file={candidate['is_file']} executable={candidate['executable_access']} "
            f"short_status={short.get('status')}"
        )
        if short.get("error"):
            print(f"      error: {short['error']}")
        if short.get("stderr_preview"):
            print(f"      stderr: {short['stderr_preview']}")
    backend = result.get("selected_backend")
    print(f"  selected backend: {backend if backend else 'none'}")
    contract = result["contract"]
    print(f"  contract status: {contract.get('status')}")
    if contract.get("error"):
        print(f"  error: {contract['error']}")
    if contract.get("stderr_preview"):
        print(f"  stderr: {contract['stderr_preview']}")
    print(f"  backend available: {result['backend_available']}")


if __name__ == "__main__":
    raise SystemExit(main())
