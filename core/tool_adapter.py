"""Verifier adapter protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from core.schemas import Candidate, ProblemSpec, ToolName, VerifierOutcome


class ToolAdapter(Protocol):
    """Protocol implemented by Lean, Z3, cvc5, and future verifier adapters."""

    tool: ToolName

    def verify(
        self,
        problem: ProblemSpec,
        candidate: Candidate,
        work_dir: Path | None = None,
    ) -> VerifierOutcome:
        """Check a candidate and return normalized verifier feedback."""
