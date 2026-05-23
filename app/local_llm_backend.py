"""LOCAL_ONLY OpenAI-compatible backend for JasperLoop workflow commands."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator, ValidationError

from copilot.agents.coverage_closure_agent import normalize_recommendation
from copilot.agents.dv_triage_agent import normalize_diagnosis
from copilot.agents.sva_repair_agent import normalize_repair

BackendType = Literal["vllm", "sglang", "ollama", "unknown"]
TaskType = Literal["repair", "triage", "coverage"]

DEFAULT_LOCAL_ENDPOINT = "http://127.0.0.1:8000/v1"
DEFAULT_LOCAL_MODEL = "Qwen/Qwen3-14B-AWQ"
LOCAL_WORKFLOW_CLAIM_BOUNDARY = (
    "Stage 5E local backend evidence is LOCAL_ONLY workflow integration evidence. "
    "It records local endpoint behavior and strict JSON/schema handling only; it is "
    "not a full benchmark, not a JasperGold/Moore run, and not a Qwen-vs-Codex comparison."
)


@dataclass(frozen=True)
class LocalBackendConfig:
    endpoint_url: str
    model_id: str
    backend_type: BackendType
    api_key: str
    timeout_s: int
    max_tokens: int
    temperature: float
    max_model_len: int | None
    use_response_format: bool

    @property
    def chat_url(self) -> str:
        return self.endpoint_url.rstrip("/") + "/chat/completions"


@dataclass(frozen=True)
class LocalBackendResult:
    status: Literal["ok", "local_unavailable", "invalid_json", "schema_invalid", "local_error"]
    output: dict[str, Any] | None
    valid_json: bool
    fallback_count: int
    llm_error_count: int
    latency_ms: float | None
    http_status: int | None
    error: str | None

    @property
    def blocked(self) -> bool:
        return self.status == "local_unavailable"


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


def local_backend_config(args: Any) -> LocalBackendConfig:
    endpoint_url = (
        getattr(args, "local_base_url", None)
        or os.environ.get("LOCAL_BASE_URL")
        or os.environ.get("QWEN_BASE_URL")
        or DEFAULT_LOCAL_ENDPOINT
    )
    model_id = (
        getattr(args, "local_model", None)
        or os.environ.get("SERVED_MODEL_NAME")
        or os.environ.get("QWEN_MODEL")
        or DEFAULT_LOCAL_MODEL
    )
    backend_type = infer_backend_type(
        getattr(args, "local_backend_type", None)
        or os.environ.get("SERVING_BACKEND")
        or os.environ.get("LOCAL_BACKEND_TYPE")
        or endpoint_url
    )
    return LocalBackendConfig(
        endpoint_url=endpoint_url,
        model_id=model_id,
        backend_type=backend_type,
        api_key=getattr(args, "local_api_key", None) or os.environ.get("LOCAL_API_KEY", "EMPTY"),
        timeout_s=int(getattr(args, "local_timeout_s", None) or env_int("LOCAL_TIMEOUT_S", 60)),
        max_tokens=int(getattr(args, "local_max_tokens", None) or env_int("LOCAL_MAX_TOKENS", 1024)),
        temperature=float(getattr(args, "local_temperature", None) or env_float("LOCAL_TEMPERATURE", 0.0)),
        max_model_len=optional_int(getattr(args, "local_max_model_len", None) or os.environ.get("MAX_MODEL_LEN")),
        use_response_format=not bool(getattr(args, "local_no_response_format", False)),
    )


def infer_backend_type(value: str | None) -> BackendType:
    lowered = (value or "").lower()
    if "sglang" in lowered:
        return "sglang"
    if "ollama" in lowered:
        return "ollama"
    if "vllm" in lowered:
        return "vllm"
    return "unknown"


def optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def local_only_effective(args: Any) -> bool:
    if getattr(args, "backend", None) == "local" and getattr(args, "dry_run", False):
        return True
    return bool(getattr(args, "local_only", False) or env_bool("LOCAL_ONLY", False))


def local_execution_requested(args: Any) -> bool:
    return bool(getattr(args, "run_local_model", False) or getattr(args, "run_local_subset", False))


def local_execution_blocker(args: Any) -> str | None:
    if getattr(args, "backend", None) != "local" or not local_execution_requested(args):
        return None
    if not getattr(args, "local_only", False):
        return "backend=local executable runs require --local-only"
    if not env_bool("LOCAL_ONLY", False):
        return "backend=local executable runs require LOCAL_ONLY=true in the environment"
    if not getattr(args, "acknowledge_local_model_run", False):
        return "backend=local executable runs require --acknowledge-local-model-run"
    return None


def gpu_snapshot() -> dict[str, Any]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": str(exc)}
    if completed.returncode != 0:
        return {"available": False, "error": completed.stderr.strip()}
    first = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    parts = [part.strip() for part in first.split(",")]
    if len(parts) < 2:
        return {"available": False, "error": f"unexpected nvidia-smi output: {first}"}
    total_mb = int(parts[1])
    return {
        "available": True,
        "name": parts[0],
        "memory_total_mb": total_mb,
        "memory_total_gb": round(total_mb / 1024.0, 2),
    }


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


def chat_once(config: LocalBackendConfig, prompt: str) -> tuple[int, float, str, str | None]:
    payload: dict[str, Any] = {
        "model": config.model_id,
        "messages": [
            {
                "role": "system",
                "content": "Return only one valid JSON object matching the requested schema.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    if config.use_response_format:
        payload["response_format"] = {"type": "json_object"}
    started = time.perf_counter()
    status, body = request_json(config.chat_url, config.api_key, payload, config.timeout_s)
    latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
    content = ""
    try:
        content = str(body["choices"][0]["message"].get("content", ""))
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    error = body.get("error") if isinstance(body, dict) else None
    return status, latency_ms, content, str(error) if error is not None else None


def call_local_task(
    *,
    config: LocalBackendConfig,
    task_type: TaskType,
    prompt: str,
    context: dict[str, Any],
    schema_path: Path,
) -> LocalBackendResult:
    status, latency_ms, content, error = chat_once(config, prompt)
    if status == 0:
        return LocalBackendResult(
            status="local_unavailable",
            output=None,
            valid_json=False,
            fallback_count=0,
            llm_error_count=1,
            latency_ms=latency_ms,
            http_status=None,
            error=error or "local endpoint unavailable",
        )
    if not (200 <= status < 300):
        return LocalBackendResult(
            status="local_error",
            output=None,
            valid_json=False,
            fallback_count=0,
            llm_error_count=1,
            latency_ms=latency_ms,
            http_status=status,
            error=error or f"local endpoint returned HTTP {status}",
        )

    parsed, json_error = extract_json_object(content)
    if parsed is None:
        return LocalBackendResult(
            status="invalid_json",
            output=None,
            valid_json=False,
            fallback_count=1,
            llm_error_count=1,
            latency_ms=latency_ms,
            http_status=status,
            error=json_error,
        )

    normalized = normalize_task_output(task_type, context, parsed)
    candidate = strip_extra(normalized, schema_path)
    try:
        validate_against_schema(candidate, schema_path)
    except ValidationError as exc:
        return LocalBackendResult(
            status="schema_invalid",
            output=None,
            valid_json=True,
            fallback_count=1,
            llm_error_count=1,
            latency_ms=latency_ms,
            http_status=status,
            error=exc.message,
        )

    return LocalBackendResult(
        status="ok",
        output=candidate,
        valid_json=True,
        fallback_count=0,
        llm_error_count=0,
        latency_ms=latency_ms,
        http_status=status,
        error=None,
    )


def normalize_task_output(task_type: TaskType, context: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    if task_type == "repair":
        return normalize_repair(context, output)
    if task_type == "triage":
        return normalize_diagnosis(context, output)
    return normalize_recommendation(context, output)


def strip_extra(payload: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return payload
    return {key: payload[key] for key in properties if key in payload}


def validate_against_schema(payload: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    Draft202012Validator(schema).validate(payload)
