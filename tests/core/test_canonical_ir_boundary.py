from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_core_schemas_module_is_not_runtime_importable() -> None:
    assert not (ROOT / "core" / "schemas.py").exists()


def test_adapters_do_not_import_legacy_core_schemas() -> None:
    offenders = []
    for path in sorted((ROOT / "adapters").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "core.schemas" in text:
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []
