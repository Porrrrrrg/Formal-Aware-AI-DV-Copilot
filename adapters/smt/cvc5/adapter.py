"""cvc5 CLI adapter."""

from __future__ import annotations

from pathlib import Path

from adapters.smt.common import SmtCliAdapter


class CVC5Adapter(SmtCliAdapter):
    def __init__(
        self,
        artifact_root: Path | None = None,
        executable: str = "cvc5",
        timeout_s: int = 30,
    ) -> None:
        super().__init__(
            tool="cvc5",
            executable=executable,
            solver_args=["--lang", "smt2"],
            artifact_root=artifact_root,
            timeout_s=timeout_s,
        )
