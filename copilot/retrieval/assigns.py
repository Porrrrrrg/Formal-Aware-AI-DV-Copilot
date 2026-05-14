"""Continuous assignment extraction helpers."""

from __future__ import annotations

from typing import Any


def extract_assigns(index: dict[str, Any], module_name: str | None = None) -> list[dict[str, Any]]:
    modules = index.get("modules", {})
    selected = [modules[module_name]] if module_name and module_name in modules else modules.values()
    assigns = []
    for module in selected:
        for assign in module.get("assigns", []):
            assigns.append({"module": module.get("name"), **assign})
    return assigns


__all__ = ["extract_assigns"]
