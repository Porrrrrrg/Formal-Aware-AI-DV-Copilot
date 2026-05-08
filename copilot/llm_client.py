"""Model-agnostic LLM backend for JasperLoop-DV.

The default backend is command-based: set `JASPERLOOP_LLM_CMD` to any local
command that reads a prompt from stdin and writes a JSON object to stdout.
This keeps the repo independent from one hosted API while allowing GPT, Claude,
Gemini, llama.cpp, vLLM, or a class wrapper script to be plugged in.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from copilot.json_utils import extract_json_object


@dataclass
class LLMResponse:
    raw_text: str
    json_object: dict[str, object]


def llm_configured(command: str | None = None) -> bool:
    return bool(command or os.environ.get("JASPERLOOP_LLM_CMD"))


def call_llm_json(prompt: str, command: str | None = None, timeout_s: int = 120) -> LLMResponse:
    command = command or os.environ.get("JASPERLOOP_LLM_CMD")
    if not command:
        raise RuntimeError("No LLM backend configured. Set JASPERLOOP_LLM_CMD.")

    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        shell=True,
        timeout=timeout_s,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "LLM command failed with exit code "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )
    raw_text = completed.stdout.strip()
    return LLMResponse(raw_text=raw_text, json_object=extract_json_object(raw_text))
