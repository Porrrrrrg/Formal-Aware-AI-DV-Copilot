#!/usr/bin/env python3
"""Build the Stage 17 Design2SVA ablation result package.

This runner is intentionally artifact-driven. It reads committed Stage 13-16
JSON results and emits a normalized ablation table without sending new LLM
prompts or launching JasperGold.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evaluation" / "results"

DEFAULT_SUMMARY = Path("evaluation/results/design2sva_ablation_summary.json")
DEFAULT_MARKDOWN = Path("artifacts/design2sva/design2sva_ablation_results.md")

METRIC_KEYS = [
    "cases",
    "k",
    "valid_json_rate",
    "fallback_rate",
    "hallucinated_signal_rate",
    "syntax@1",
    "syntax@k",
    "proven@1",
    "proven@k",
    "non_vacuous@k",
    "proven_non_vacuous@k",
    "antecedent_reachable@k",
    "wrapper_parity_pass_rate",
    "average_rounds",
    "source_counts",
    "formal_metrics_status",
]

FORMAL_METRICS = {
    "proven@1",
    "proven@k",
    "non_vacuous@k",
    "proven_non_vacuous@k",
    "antecedent_reachable@k",
    "wrapper_parity_pass_rate",
}

CLI_VARIANTS = [
    "reference_oracle",
    "current_codex_replay",
    "fixed_wrapper_rerun",
    "deterministic_scaffold",
    "replay",
    "direct_prompt_placeholder",
    "no_retrieval_placeholder",
    "no_antivacuity_placeholder",
]

ROW_IDS_FOR_VARIANT = {
    "reference_oracle": ["reference_oracle"],
    "current_codex_replay": ["codex_design2sva_current"],
    "fixed_wrapper_rerun": ["codex_fixed_wrapper_rerun"],
    "deterministic_scaffold": ["deterministic_scaffold"],
    "replay": ["replay_baseline"],
    "direct_prompt_placeholder": ["direct_prompt_placeholder"],
    "no_retrieval_placeholder": ["no_retrieval_placeholder"],
    "no_antivacuity_placeholder": ["no_antivacuity_placeholder"],
}

NOT_RUN = "not_run"
NOT_APPLICABLE = "not_applicable"
NOT_RECORDED = "not_recorded"


@dataclass(frozen=True)
class RowSpec:
    row_id: str
    artifact: str | None
    row_type: str
    description: str
    artifact_metric_mode: str = "standard"
    command_to_measure: str | None = None


ROW_SPECS = [
    RowSpec(
        row_id="reference_oracle",
        artifact="design2sva_reference_oracle_expanded_jasper.json",
        row_type="measured_control",
        description="Expanded fixture reference SVA evaluated through the repaired wrapper.",
        artifact_metric_mode="reference_oracle",
    ),
    RowSpec(
        row_id="native_oracle",
        artifact="design2sva_native_oracle_expanded_jasper.json",
        row_type="measured_control",
        description="Expanded fixture reference properties evaluated through native benchmark flows.",
        artifact_metric_mode="native_oracle",
    ),
    RowSpec(
        row_id="codex_design2sva_current",
        artifact="design2sva_eval_codex_expanded_jasper.json",
        row_type="jasper_measured_replay",
        description="Stage 16 real Codex k=3 candidates replayed with JasperGold evidence.",
    ),
    RowSpec(
        row_id="codex_fixed_wrapper_rerun",
        artifact="design2sva_eval_codex_fixed_wrapper_rerun.json",
        row_type="jasper_measured_replay",
        description="Stage 13 committed Codex candidates rerun through the fixed wrapper.",
    ),
    RowSpec(
        row_id="codex_antivacuity_current",
        artifact="design2sva_eval_antivacuity_codex_fixed_wrapper_rerun.json",
        row_type="jasper_measured_replay",
        description=(
            "Committed anti-vacuity Codex subset after the fixed-wrapper rerun; "
            "kept separate from the earlier pre-wrapper anti-vacuity failures."
        ),
    ),
    RowSpec(
        row_id="deterministic_scaffold",
        artifact="design2sva_eval_local.json",
        row_type="local_scaffold",
        description="Deterministic local scaffold row; no formal backend measurement.",
    ),
    RowSpec(
        row_id="replay_baseline",
        artifact="design2sva_codex_replay_expanded_local.json",
        row_type="local_replay",
        description="Stage 14 committed Codex replay baseline without JasperGold measurement.",
    ),
    RowSpec(
        row_id="direct_prompt_placeholder",
        artifact=None,
        row_type="placeholder",
        description="Direct prompt ablation row reserved for a gated future external LLM run.",
        command_to_measure=(
            "python scripts/run_codex_llm_eval.py --task design2sva --k 3 "
            "--context-budget 0 --acknowledge-external-send "
            "--out evaluation/results/design2sva_direct_prompt.json"
        ),
    ),
    RowSpec(
        row_id="no_retrieval_placeholder",
        artifact=None,
        row_type="placeholder",
        description="No-retrieval ablation row reserved for a gated future external LLM run.",
        command_to_measure=(
            "python scripts/run_codex_llm_eval.py --task design2sva --k 3 "
            "--context-budget 0 --acknowledge-external-send "
            "--out evaluation/results/design2sva_no_retrieval.json"
        ),
    ),
    RowSpec(
        row_id="no_antivacuity_placeholder",
        artifact=None,
        row_type="placeholder",
        description="No anti-vacuity repair ablation row reserved for a gated future LLM run.",
        command_to_measure=(
            "python scripts/run_codex_llm_eval.py --task design2sva --k 3 "
            "--max-repair-rounds 0 --acknowledge-external-send "
            "--out evaluation/results/design2sva_no_antivacuity.json"
        ),
    ),
]


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def repo_relative(path: Path | str | None) -> str | None:
    if path is None:
        return None
    resolved = resolve_repo_path(Path(path)).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{repo_relative(path)} must contain a JSON object")
    return data


def standard_metric(summary: dict[str, Any], key: str) -> Any:
    if key == "cases":
        return summary.get("num_cases", NOT_RECORDED)
    if key == "source_counts":
        return summary.get("source_counts", {})
    return summary.get(key, NOT_RECORDED)


def standard_metrics_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = {key: standard_metric(summary, key) for key in METRIC_KEYS}
    if str(summary.get("formal_metrics_status") or "").lower() == NOT_RUN:
        for key in FORMAL_METRICS:
            metrics[key] = NOT_RUN
    return metrics


def wrapper_reference_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for result in payload.get("results", []):
        if not isinstance(result, dict):
            continue
        wrapper = result.get("wrapper_reference", {})
        if isinstance(wrapper, dict):
            rows.append(wrapper)
    return rows


def rate(rows: list[dict[str, Any]], predicate_key: str) -> Any:
    if not rows:
        return NOT_RECORDED
    return sum(1 for row in rows if row.get(predicate_key) is True) / len(rows)


def reference_oracle_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload.get("summary", {}))
    rows = wrapper_reference_rows(payload)
    k = summary.get("k", 1)
    return {
        "cases": summary.get("num_cases", len(rows) or NOT_RECORDED),
        "k": k,
        "valid_json_rate": summary.get("valid_json_rate", 1.0 if rows else NOT_RECORDED),
        "fallback_rate": summary.get("fallback_rate", 0.0 if rows else NOT_RECORDED),
        "hallucinated_signal_rate": rate(rows, "has_hallucinated_signal")
        if rows
        else NOT_RECORDED,
        "syntax@1": rate(rows, "syntax_ok"),
        "syntax@k": rate(rows, "syntax_ok"),
        "proven@1": summary.get("reference_proven@1", NOT_RECORDED),
        "proven@k": summary.get("reference_proven@1", NOT_RECORDED),
        "non_vacuous@k": summary.get("reference_non_vacuous@1", NOT_RECORDED),
        "proven_non_vacuous@k": summary.get("reference_non_vacuous@1", NOT_RECORDED),
        "antecedent_reachable@k": summary.get(
            "reference_antecedent_reachable@1",
            NOT_RECORDED,
        ),
        "wrapper_parity_pass_rate": summary.get("wrapper_parity_pass_rate", NOT_RECORDED),
        "average_rounds": 0.0,
        "source_counts": summary.get("source_counts", {}),
        "formal_metrics_status": summary.get("formal_metrics_status", NOT_RECORDED),
    }


def native_oracle_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload.get("summary", {}))
    proof_status_counts = summary.get("native_proof_status_counts", {})
    vacuity_status_counts = summary.get("native_vacuity_status_counts", {})
    vacuity_was_run = isinstance(vacuity_status_counts, dict) and any(
        str(status).lower() not in {"not_run", "blocked"}
        for status in vacuity_status_counts
    )
    proven = summary.get("native_reference_proven_rate", NOT_RECORDED)
    return {
        "cases": summary.get("num_cases", NOT_RECORDED),
        "k": 1,
        "valid_json_rate": NOT_APPLICABLE,
        "fallback_rate": NOT_APPLICABLE,
        "hallucinated_signal_rate": NOT_APPLICABLE,
        "syntax@1": NOT_APPLICABLE,
        "syntax@k": NOT_APPLICABLE,
        "proven@1": proven,
        "proven@k": proven,
        "non_vacuous@k": summary.get("native_reference_non_vacuous_rate", NOT_RECORDED)
        if vacuity_was_run
        else NOT_RUN,
        "proven_non_vacuous@k": summary.get(
            "native_reference_non_vacuous_rate",
            NOT_RECORDED,
        )
        if vacuity_was_run
        else NOT_RUN,
        "antecedent_reachable@k": NOT_APPLICABLE,
        "wrapper_parity_pass_rate": NOT_APPLICABLE,
        "average_rounds": NOT_APPLICABLE,
        "source_counts": {"native_reference_oracle": summary.get("num_cases", 0)},
        "formal_metrics_status": summary.get("native_measurement_status", NOT_RECORDED),
    } | {
        "_native_proof_status_counts": proof_status_counts,
        "_native_vacuity_status_counts": vacuity_status_counts,
    }


def row_status(metrics: dict[str, Any], spec: RowSpec, artifact_exists: bool) -> str:
    if spec.artifact is None:
        return NOT_RUN
    if not artifact_exists:
        return "missing_artifact"
    formal_status = str(metrics.get("formal_metrics_status") or "").lower()
    if formal_status in {"measured", "replayed", "jasper", "partial"}:
        return "measured"
    if formal_status == NOT_RUN:
        return "local_only_formal_not_run"
    return "available"


def placeholder_metrics() -> dict[str, Any]:
    return {key: NOT_RUN for key in METRIC_KEYS}


def build_row(spec: RowSpec) -> dict[str, Any]:
    if spec.artifact is None:
        return {
            "row_id": spec.row_id,
            "variant": spec.row_id,
            "status": NOT_RUN,
            "row_type": spec.row_type,
            "artifact": None,
            "artifact_exists": False,
            "description": spec.description,
            "metrics": placeholder_metrics(),
            "source_counts": {},
            "formal_metrics_status": NOT_RUN,
            "llm_prompts_sent": False,
            "command_to_measure": spec.command_to_measure,
            "requires_external_llm": True,
        }

    artifact_path = RESULTS / spec.artifact
    artifact_exists = artifact_path.exists()
    if not artifact_exists:
        metrics = placeholder_metrics()
        status = row_status(metrics, spec, artifact_exists=False)
        payload: dict[str, Any] = {}
    else:
        payload = load_json(artifact_path)
        if spec.artifact_metric_mode == "reference_oracle":
            metrics = reference_oracle_metrics(payload)
        elif spec.artifact_metric_mode == "native_oracle":
            metrics = native_oracle_metrics(payload)
        else:
            summary = payload.get("summary", {})
            if not isinstance(summary, dict):
                summary = {}
            metrics = standard_metrics_from_summary(summary)
        status = row_status(metrics, spec, artifact_exists=True)

    formal_metrics_status_value = metrics.get("formal_metrics_status", NOT_RECORDED)
    public_metrics = {
        key: value for key, value in metrics.items() if not key.startswith("_")
    }
    return {
        "row_id": spec.row_id,
        "variant": spec.row_id,
        "status": status,
        "row_type": spec.row_type,
        "artifact": spec.artifact,
        "artifact_path": repo_relative(artifact_path),
        "artifact_exists": artifact_exists,
        "description": spec.description,
        "metrics": public_metrics,
        "source_counts": public_metrics.get("source_counts", {}),
        "formal_metrics_status": formal_metrics_status_value,
        "llm_prompts_sent": bool(payload.get("llm_prompts_sent", False)),
        "mode": payload.get("mode"),
        "formal_check_mode": payload.get("formal_check_mode"),
        "requires_external_llm": False,
        "command_to_measure": spec.command_to_measure,
    }


def selected_specs(variants: list[str] | None) -> list[RowSpec]:
    if not variants:
        return ROW_SPECS
    row_ids = []
    for variant in variants:
        row_ids.extend(ROW_IDS_FOR_VARIANT[variant])
    wanted = set(row_ids)
    return [spec for spec in ROW_SPECS if spec.row_id in wanted]


def build_payload(variants: list[str] | None = None) -> dict[str, Any]:
    rows = [build_row(spec) for spec in selected_specs(variants)]
    not_run_rows = [row["row_id"] for row in rows if row["status"] == NOT_RUN]
    measured_rows = [row["row_id"] for row in rows if row["status"] == "measured"]
    local_only_rows = [
        row["row_id"] for row in rows if row["status"] == "local_only_formal_not_run"
    ]
    return {
        "schema_version": "stage17_design2sva_ablation_v1",
        "mode": "stage17_design2sva_ablation",
        "artifact_policy": "existing_committed_artifacts_only",
        "llm_prompts_sent": False,
        "variants_requested": variants or ["all"],
        "metric_keys": METRIC_KEYS,
        "summary": {
            "num_rows": len(rows),
            "num_cases": max(
                (
                    int(row["metrics"]["cases"])
                    for row in rows
                    if isinstance(row.get("metrics"), dict)
                    and isinstance(row["metrics"].get("cases"), int)
                ),
                default=0,
            ),
            "k": "mixed",
            "measured_rows": measured_rows,
            "not_run_rows": not_run_rows,
            "local_only_rows": local_only_rows,
            "formal_metrics_status": "mixed",
            "source_counts": source_counts_union(rows),
            "valid_json_rate": "mixed",
            "fallback_rate": "mixed",
            "hallucinated_signal_rate": "mixed",
            "syntax@1": "mixed",
            "syntax@k": "mixed",
            "proven@1": "mixed",
            "proven@k": "mixed",
            "non_vacuous@k": "mixed",
            "proven_non_vacuous@k": "mixed",
            "antecedent_reachable@k": "mixed",
            "wrapper_parity_pass_rate": "mixed",
            "average_rounds": "mixed",
        },
        "rows": rows,
        "external_llm_commands": [
            {
                "variant": row["row_id"],
                "command": row["command_to_measure"],
                "gated": True,
                "status": NOT_RUN,
            }
            for row in rows
            if row.get("command_to_measure")
        ],
        "confidence_caveats": [
            "Local benchmark only.",
            "Small N: 12-case expanded Design2SVA benchmark plus smaller legacy controls.",
            "No production signoff.",
            "Not an official FVEval reproduction.",
            "Rows with formal_metrics_status=not_run must not be read as zero proof success.",
        ],
    }


def source_counts_union(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        source_counts = row.get("source_counts", {})
        if not isinstance(source_counts, dict):
            continue
        for key, value in source_counts.items():
            if isinstance(value, int):
                counts[str(key)] = counts.get(str(key), 0) + value
    return dict(sorted(counts.items()))


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, dict):
        if not value:
            return "{}"
        return ", ".join(f"{key}={val}" for key, val in sorted(value.items()))
    if value is None:
        return ""
    return str(value)


def render_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Design2SVA Stage 17 Ablation Summary",
        "",
        "This table is built from existing committed artifacts only. It sends no new external LLM prompts and does not invoke JasperGold.",
        "",
        "## Summary",
        "",
        "| Row | Status | Artifact | Cases | k | valid_json_rate | fallback_rate | hallucinated_signal_rate | syntax@1 | syntax@k | proven@1 | proven@k | non_vacuous@k | proven_non_vacuous@k | antecedent_reachable@k | wrapper_parity_pass_rate | average_rounds | source_counts | formal_metrics_status |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        metrics = row["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['row_id']}`",
                    f"`{row['status']}`",
                    f"`{row.get('artifact') or 'not_run'}`",
                    fmt(metrics["cases"]),
                    fmt(metrics["k"]),
                    fmt(metrics["valid_json_rate"]),
                    fmt(metrics["fallback_rate"]),
                    fmt(metrics["hallucinated_signal_rate"]),
                    fmt(metrics["syntax@1"]),
                    fmt(metrics["syntax@k"]),
                    fmt(metrics["proven@1"]),
                    fmt(metrics["proven@k"]),
                    fmt(metrics["non_vacuous@k"]),
                    fmt(metrics["proven_non_vacuous@k"]),
                    fmt(metrics["antecedent_reachable@k"]),
                    fmt(metrics["wrapper_parity_pass_rate"]),
                    fmt(metrics["average_rounds"]),
                    fmt(metrics["source_counts"]),
                    fmt(metrics["formal_metrics_status"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Row Notes",
            "",
        ]
    )
    for row in rows:
        lines.append(f"- `{row['row_id']}`: {row['description']}")
        if row.get("command_to_measure"):
            lines.append(
                f"  Gated command, not run by this artifact: `{row['command_to_measure']}`"
            )

    lines.extend(
        [
            "",
            "## Caveats",
            "",
        ]
    )
    for caveat in payload["confidence_caveats"]:
        lines.append(f"- {caveat}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        action="append",
        choices=CLI_VARIANTS,
        help="Emit one variant row. Repeat for multiple variants. Omit for all rows.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)

    payload = build_payload(args.variant)
    out = resolve_repo_path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    markdown = resolve_repo_path(args.markdown)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "mode": payload["mode"],
                "rows": [row["row_id"] for row in payload["rows"]],
                "llm_prompts_sent": payload["llm_prompts_sent"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
