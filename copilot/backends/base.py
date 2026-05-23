"""Backend-neutral formal tool interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.models.agent import BackendResult


class FormalBackend(ABC):
    """Stable boundary between prompt/agent code and formal tool execution."""

    name: str

    @abstractmethod
    def check_generated_sva(
        self,
        case: dict[str, Any],
        prediction: dict[str, Any],
        system: str,
        out_root: Path | None = None,
        dry_run: bool = False,
    ) -> BackendResult:
        """Check a generated SVA candidate and return structured formal evidence."""

    @abstractmethod
    def run_benchmark(
        self,
        design: str,
        variant: str = "correct",
        mode: str = "prove",
        dry_run: bool = False,
    ) -> BackendResult:
        """Run a design/variant benchmark through the backend."""

    @abstractmethod
    def parse_report_dir(
        self,
        report_dir: Path,
        property_id: str | None = None,
        returncode: int | None = None,
        dry_run: bool = False,
    ) -> BackendResult:
        """Normalize an existing backend report directory."""
