#!/usr/bin/env python3
"""JSON-only healthcheck for an OpenAI-compatible local Qwen server.

The check is intentionally local-first and local-only by default. It writes a
reproducible manifest even when the server is down, recording
``local_unavailable`` instead of falling through to any cloud provider.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "local-qwen-health/v1"
DEFAULT_PROMPT_VERSION = "qwen-health-json-v1"
DEFAULT_REPORTS_DIR = Path("reports/local_llm")
REQUIRED_MODEL_JSON_FIELDS = [
    "model_name",
    "quantization",
    "backend",
    "gpu_name",
    "vram_gb",
    "max_model_len",
    "gpu_memory_utilization",
    "max_num_seqs",
    "LOCAL_ONLY",
    "cloud_fallback_allowed",
    "git_sha",
    "prompt_version",
    "schema_version",
]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if not value:
        return default
    return float(value)


@dataclass(frozen=True)
class QwenProfile:
    name: str
    model_name: str
    quantization: str
    role: str
    notes: str


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    api_key: str
    model: str

    @property
    def chat_url(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"


def qwen_profiles() -> dict[str, QwenProfile]:
    return {
        "safe_profile": QwenProfile(
            name="safe_profile",
            model_name=os.environ.get("QWEN_SAFE_PROFILE_MODEL", "Qwen/Qwen3-14B-AWQ"),
            quantization=os.environ.get("QWEN_SAFE_PROFILE_QUANTIZATION", "AWQ"),
            role="default_safe",
            notes="Default single RTX 3090 Ti local profile.",
        ),
        "big_profile": QwenProfile(
            name="big_profile",
            model_name=os.environ.get(
                "QWEN_BIG_PROFILE_MODEL",
                "Qwen/Qwen3-30B-A3B-Instruct-2507",
            ),
            quantization=os.environ.get(
                "QWEN_BIG_PROFILE_QUANTIZATION",
                "native_or_local_quantized",
            ),
            role="larger_moe_candidate",
            notes="Use only after confirming the exact local snapshot fits the 24 GB target.",
        ),
        "experimental_dense_profile": QwenProfile(
            name="experimental_dense_profile",
            model_name=os.environ.get(
                "QWEN_EXPERIMENTAL_DENSE_PROFILE_MODEL",
                "Qwen/Qwen3-32B-AWQ",
            ),
            quantization=os.environ.get("QWEN_EXPERIMENTAL_DENSE_PROFILE_QUANTIZATION", "AWQ"),
            role="experimental_dense_only",
            notes="Qwen3-32B-AWQ is not a safe or big default for this host.",
        ),
    }


def infer_quantization(model_name: str, fallback: str) -> str:
    lowered = model_name.lower()
    if "awq" in lowered:
        return "AWQ"
    if "gptq" in lowered:
        return "GPTQ"
    if "gguf" in lowered:
        return "GGUF"
    if "fp8" in lowered:
        return "FP8"
    if "int4" in lowered or "4bit" in lowered or "w4a16" in lowered:
        return "INT4"
    if "int8" in lowered or "8bit" in lowered or "w8a8" in lowered:
        return "INT8"
    return fallback


def request_json(url: str, api_key: str, payload: dict[str, Any], timeout_s: int) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: dict[str, Any] = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        return exc.code, parsed
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        return 0, {"error": repr(exc)}


def gpu_snapshot() -> dict[str, Any]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=timestamp,name,driver_version,cuda_version,utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}
    if completed.returncode != 0:
        return {"available": False, "error": completed.stderr.strip()}

    first = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    parts = [part.strip() for part in first.split(",")]
    if len(parts) < 7:
        return {"available": False, "error": f"unexpected nvidia-smi output: {first}"}
    used_mb = int(parts[5])
    total_mb = int(parts[6])
    return {
        "available": True,
        "timestamp": parts[0],
        "name": parts[1],
        "driver_version": parts[2],
        "cuda_version": parts[3],
        "gpu_util_percent": int(parts[4]),
        "memory_used_mb": used_mb,
        "memory_total_mb": total_mb,
        "memory_total_gb": round(total_mb / 1024.0, 2),
        "memory_used_fraction": round(used_mb / total_mb, 4) if total_mb else None,
    }


def count_ooms(log_file: str) -> int:
    if not log_file:
        return 0
    path = Path(log_file)
    if not path.exists():
        return 0
    needles = ("out of memory", "cuda oom", "torch.cuda.outofmemoryerror", "cuda error: out of memory")
    count = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                lowered = line.lower()
                if any(needle in lowered for needle in needles):
                    count += 1
    except OSError:
        return 0
    return count


def git_sha(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def cloud_fallback_allowed(local_only: bool) -> bool:
    if local_only:
        return False
    return bool(os.environ.get("CLOUD_OPENAI_API_KEY") and os.environ.get("CLOUD_OPENAI_MODEL"))


def fallback_reasons(local_status: str, http_status: int, oom_delta: int) -> list[str]:
    reasons: list[str] = []
    if local_status == "local_unavailable" and env_bool("CLOUD_FALLBACK_ON_UNAVAILABLE", True):
        reasons.append("local_unavailable")
    if http_status >= 500 and env_bool("CLOUD_FALLBACK_ON_LOCAL_5XX", True):
        reasons.append("local_5xx")
    if oom_delta > 0 and env_bool("CLOUD_FALLBACK_ON_OOM", True):
        reasons.append("local_oom")
    return reasons


def extract_json_object(text: str) -> tuple[dict[str, Any] | None, str | None]:
    stripped = text.strip()
    if not stripped:
        return None, "empty_response"
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            return None, "no_json_object_found"
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            return None, f"json_decode_error: {exc}"
    if not isinstance(parsed, dict):
        return None, "json_value_is_not_object"
    return parsed, None


def validate_model_json(data: dict[str, Any] | None, manifest_fields: dict[str, Any]) -> list[str]:
    if data is None:
        return ["missing_model_json"]
    errors: list[str] = []
    for field in REQUIRED_MODEL_JSON_FIELDS:
        if field not in data:
            errors.append(f"missing:{field}")
    for field, expected in manifest_fields.items():
        if field not in data:
            continue
        if data[field] != expected:
            errors.append(f"mismatch:{field}")
    return errors


def build_health_prompt(manifest_fields: dict[str, Any]) -> str:
    return (
        "Return exactly one JSON object and no prose. "
        "The JSON object must contain these exact keys and values:\n"
        f"{json.dumps(manifest_fields, indent=2, sort_keys=True)}"
    )


def chat_once(
    endpoint: Endpoint,
    prompt: str,
    timeout_s: int,
    max_tokens: int,
    temperature: float,
    use_response_format: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": endpoint.model,
        "messages": [
            {
                "role": "system",
                "content": "You are a local runtime healthcheck. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if use_response_format:
        payload["response_format"] = {"type": "json_object"}

    started = time.perf_counter()
    status, body = request_json(endpoint.chat_url, endpoint.api_key, payload, timeout_s)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    content = ""
    try:
        content = body["choices"][0]["message"].get("content", "")
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    return {
        "http_status": status,
        "latency_ms": round(elapsed_ms, 2),
        "content": content,
        "error": body.get("error") if isinstance(body, dict) else None,
    }


def selected_profile(args: argparse.Namespace, profiles: dict[str, QwenProfile]) -> QwenProfile:
    profile_name = args.profile or os.environ.get("QWEN_PROFILE", "safe_profile")
    if profile_name not in profiles:
        known = ", ".join(sorted(profiles))
        raise SystemExit(f"unknown Qwen profile {profile_name!r}; known profiles: {known}")
    return profiles[profile_name]


def resolved_model(args: argparse.Namespace, profile: QwenProfile) -> str:
    return (
        args.model
        or os.environ.get("SERVED_MODEL_NAME")
        or os.environ.get("QWEN_MODEL")
        or profile.model_name
    )


def enforce_profile_bounds(model_name: str, profile: QwenProfile) -> None:
    if "Qwen3-32B-AWQ" in model_name and profile.name != "experimental_dense_profile":
        raise SystemExit("Qwen3-32B-AWQ is allowed only through experimental_dense_profile.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=None, help="Qwen profile name, defaults to QWEN_PROFILE or safe_profile.")
    parser.add_argument("--base-url", default=os.environ.get("LOCAL_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--api-key", default=os.environ.get("LOCAL_API_KEY", "EMPTY"))
    parser.add_argument("--model", default=None, help="Override served model name for this check.")
    parser.add_argument("--backend", default=os.environ.get("SERVING_BACKEND", "vllm"))
    parser.add_argument("--reports-dir", default=os.environ.get("QWEN_HEALTH_REPORTS_DIR", str(DEFAULT_REPORTS_DIR)))
    parser.add_argument("--output-jsonl", default=os.environ.get("HEALTHCHECK_LOG", "reports/local_llm/qwen_health.jsonl"))
    parser.add_argument("--timeout-s", type=int, default=env_int("BENCH_TIMEOUT_S", 120))
    parser.add_argument("--max-tokens", type=int, default=env_int("BENCH_MAX_TOKENS", 512))
    parser.add_argument("--temperature", type=float, default=env_float("BENCH_TEMPERATURE", 0.0))
    parser.add_argument("--max-model-len", type=int, default=env_int("MAX_MODEL_LEN", 24576))
    parser.add_argument("--gpu-memory-utilization", type=float, default=env_float("GPU_MEMORY_UTILIZATION", 0.82))
    parser.add_argument("--max-num-seqs", type=int, default=env_int("MAX_NUM_SEQS", 1))
    parser.add_argument("--service-log-file", default=os.environ.get("SERVICE_LOG_FILE", "/var/log/local-llm/vllm.log"))
    parser.add_argument("--prompt-version", default=os.environ.get("QWEN_HEALTH_PROMPT_VERSION", DEFAULT_PROMPT_VERSION))
    parser.add_argument("--schema-version", default=os.environ.get("QWEN_HEALTH_SCHEMA_VERSION", SCHEMA_VERSION))
    parser.add_argument("--requests", type=int, default=1, help="Deprecated compatibility flag; JSON healthcheck sends one local request.")
    parser.add_argument("--check-cloud-fallback", action="store_true", help="Audit fallback eligibility only; does not call cloud.")
    parser.add_argument("--no-response-format", action="store_true", help="Do not send OpenAI JSON response_format.")
    parser.add_argument("--strict-exit", action="store_true", help="Return non-zero when local health is not ok.")
    return parser


def append_jsonl(path: str, record: dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = build_arg_parser().parse_args()
    repo_root = repo_root_from_script()
    profiles = qwen_profiles()
    profile = selected_profile(args, profiles)
    model_name = resolved_model(args, profile)
    enforce_profile_bounds(model_name, profile)
    quantization = infer_quantization(model_name, profile.quantization)
    local_only = env_bool("LOCAL_ONLY", True)
    cloud_allowed = cloud_fallback_allowed(local_only)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = f"qwen_health_{timestamp}"

    gpu_before = gpu_snapshot()
    gpu_name = str(gpu_before.get("name") or os.environ.get("GPU_NAME") or "unknown")
    vram_gb = gpu_before.get("memory_total_gb")
    if vram_gb is None:
        vram_gb = env_float("VRAM_GB", 24.0)

    manifest_fields = {
        "model_name": model_name,
        "quantization": quantization,
        "backend": args.backend,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "max_num_seqs": args.max_num_seqs,
        "LOCAL_ONLY": local_only,
        "cloud_fallback_allowed": cloud_allowed,
        "git_sha": git_sha(repo_root),
        "prompt_version": args.prompt_version,
        "schema_version": args.schema_version,
    }

    oom_before = count_ooms(args.service_log_file)
    endpoint = Endpoint(base_url=args.base_url, api_key=args.api_key, model=model_name)
    prompt = build_health_prompt(manifest_fields)
    chat = chat_once(
        endpoint=endpoint,
        prompt=prompt,
        timeout_s=args.timeout_s,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        use_response_format=not args.no_response_format,
    )
    oom_after = count_ooms(args.service_log_file)
    oom_delta = max(0, oom_after - oom_before)

    model_json, json_error = extract_json_object(chat["content"])
    schema_errors = validate_model_json(model_json, manifest_fields)
    http_status = int(chat["http_status"] or 0)
    if http_status == 0:
        local_status = "local_unavailable"
    elif 200 <= http_status < 300 and not schema_errors:
        local_status = "ok"
    elif 200 <= http_status < 300:
        local_status = "invalid_json"
    elif http_status >= 500:
        local_status = "local_server_error"
    else:
        local_status = "local_request_failed"

    reasons = fallback_reasons(local_status, http_status, oom_delta)
    fallback_policy = {
        "LOCAL_ONLY": local_only,
        "cloud_fallback_allowed": cloud_allowed,
        "fallback_reasons": [] if local_only else reasons,
        "cloud_not_called": True,
        "note": "healthcheck records local manifest state only; it never executes cloud fallback",
    }

    reports_dir = Path(args.reports_dir)
    health_path = reports_dir / f"{run_id}.json"
    run_manifest_path = reports_dir / "run_manifest.json"
    record: dict[str, Any] = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_profile": profile.name,
        "profiles": {name: asdict(item) for name, item in profiles.items()},
        **manifest_fields,
        "healthcheck_prompt": prompt,
        "response_format_requested": not args.no_response_format,
        "local": {
            "status": local_status,
            "base_url": args.base_url,
            "http_status": http_status,
            "latency_ms": chat["latency_ms"],
            "json_valid": model_json is not None and not schema_errors,
            "json_error": json_error,
            "schema_errors": schema_errors,
            "model_json": model_json,
            "error": chat["error"],
        },
        "gpu_before": gpu_before,
        "gpu_after": gpu_snapshot(),
        "oom_before": oom_before,
        "oom_after": oom_after,
        "oom_delta": oom_delta,
        "fallback_policy": fallback_policy,
        "healthcheck_path": str(health_path),
        "run_manifest_path": str(run_manifest_path),
    }

    write_json(health_path, record)
    write_json(run_manifest_path, record)
    append_jsonl(args.output_jsonl, record)
    print(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True))

    if args.strict_exit and local_status != "ok":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
