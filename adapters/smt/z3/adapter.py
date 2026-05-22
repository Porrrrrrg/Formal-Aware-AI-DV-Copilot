"""Z3 CLI adapter."""

from __future__ import annotations

from pathlib import Path

from adapters.smt.common import SmtCliAdapter


class Z3Adapter(SmtCliAdapter):
    def __init__(
        self,
        artifact_root: Path | None = None,
        executable: str = "z3",
        timeout_s: int = 30,
    ) -> None:
        super().__init__(
            tool="z3",
            executable=executable,
            solver_args=["-smt2"],
            artifact_root=artifact_root,
            timeout_s=timeout_s,
        )
