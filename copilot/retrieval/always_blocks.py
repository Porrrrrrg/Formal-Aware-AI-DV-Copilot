"""Always-block extraction helpers."""

from __future__ import annotations

from typing import Any


def extract_always_blocks(index: dict[str, Any], module_name: str | None = None) -> list[dict[str, Any]]:
    modules = index.get("modules", {})
    selected = [modules[module_name]] if module_name and module_name in modules else modules.values()
    blocks = []
    for module in selected:
        for block in module.get("always_blocks", []):
            blocks.append({"module": module.get("name"), **block})
    return blocks


__all__ = ["extract_always_blocks"]
