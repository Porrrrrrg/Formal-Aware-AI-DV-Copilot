"""Evaluation metrics for JasperLoop-DV."""

from __future__ import annotations


def accuracy(rows: list[dict[str, object]], pred_key: str, gold_key: str) -> float:
    if not rows:
        return 0.0
    correct = sum(1 for row in rows if row.get(pred_key) == row.get(gold_key))
    return correct / len(rows)


def valid_json_rate(total: int, valid: int) -> float:
    return valid / total if total else 0.0
