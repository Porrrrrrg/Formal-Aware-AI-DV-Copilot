"""Small manifest readers used by JasperLoop tools.

The project keeps YAML manifests deliberately simple so the core tooling can run
on lab machines without requiring PyYAML.
"""

from __future__ import annotations

from pathlib import Path


def infer_signal_role_map_path(case_path: Path) -> Path | None:
    """Infer `benchmarks/<design>/manifests/signal_role_map.yaml` from a case path."""
    parts = list(case_path.parts)
    if "cases" not in parts:
        return None
    case_index = parts.index("cases")
    design_dir = Path(*parts[:case_index])
    candidate = design_dir / "manifests" / "signal_role_map.yaml"
    return candidate if candidate.exists() else None


def load_signal_role_map(path: Path | None) -> dict[str, str]:
    """Load the simple `signals: name: role` manifest format."""
    if path is None or not path.exists():
        return {}

    roles: dict[str, str] = {}
    in_signals = False
    for raw_line in path.read_text().splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "signals:":
            in_signals = True
            continue
        if not in_signals:
            continue
        if not raw_line.startswith((" ", "\t")):
            break
        if ":" not in stripped:
            continue
        signal, role = stripped.split(":", 1)
        signal = signal.strip().strip("'\"")
        role = role.strip().strip("'\"")
        if signal and role:
            roles[signal] = role
    return roles
