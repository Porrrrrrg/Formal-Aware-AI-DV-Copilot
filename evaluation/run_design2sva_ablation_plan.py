#!/usr/bin/env python3
"""Build a dry-run/replay Design2SVA ablation plan artifact.

The Stage 14 ablation runner is intentionally local-only. It reuses committed
fixture metadata and existing replay/native-oracle plumbing, but it never sends
new model prompts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.run_design2sva_eval import load_cases, run_case, summarize  # noqa: E402
from evaluation.run_design2sva_native_oracle import (  # noqa: E402
    build_payload as build_native_oracle_payload,
)

DEFAULT_CASES = Path("benchmarks/design2sva_cases.json")
DEFAULT_OUT = Path("evaluation/results/design2sva_ablation_replay_local.json")
DEFAULT_PLAN = Path("artifacts/design2sva/design2sva_ablation_plan.md")

REQUIRED_METRICS = [
    "syntax@1",
    "syntax@k",
    "proven@1",
    "proven@k",
    "non_vacuous@k",
    "proven_non_vacuous@k",
    "antecedent_reachable@k",
    "valid_json_rate",
    "fallback_rate",
    "hallucinated_signal_rate",
    "average_rounds",
    "wrapper_parity_pass_rate",
]

ABLATION_VARIANTS: dict[str, dict[str, Any]] = {
    "direct_prompt": {
        "objective": "Natural-language intent plus schema contract, without retrieval context.",
        "runner_mode": "local_dry_run",
        "context_budget": 0,
        "reference_oracle": False,
        "max_repair_rounds": 0,
    },
    "retrieval_context": {
        "objective": "Add bounded RTL/harness retrieval context.",
        "runner_mode": "local_dry_run",
        "context_budget": 24,
        "reference_oracle": False,
        "max_repair_rounds": 0,
    },
    "retrieval_plus_reachability_guidance": {
        "objective": "Add reachable-trigger guidance on top of retrieval context.",
        "runner_mode": "local_dry_run",
        "context_budget": 24,
        "reference_oracle": False,
        "max_repair_rounds": 0,
    },
    "retrieval_plus_anti_vacuity_repair": {
        "objective": "Replay-safe placeholder for anti-vacuity repair rounds.",
        "runner_mode": "local_dry_run",
        "context_budget": 24,
        "reference_oracle": False,
        "max_repair_rounds": 1,
    },
    "reference_oracle": {
        "objective": "Evaluate fixture reference_sva through the Design2SVA wrapper path.",
        "runner_mode": "reference_oracle_local_dry_run",
        "context_budget": 24,
        "reference_oracle": True,
        "max_repair_rounds": 0,
    },
    "native_oracle": {
        "objective": "Validate fixture labels against the checked-in native benchmark flow.",
        "runner_mode": "native_oracle_mapping_dry_run",
        "context_budget": 0,
        "reference_oracle": False,
        "max_repair_rounds": 0,
    },
}


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def repo_relative(path: Path | str) -> str:
    resolved = resolve_repo_path(Path(path)).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def metric_subset(summary: dict[str, Any]) -> dict[str, Any]:
    return {metric: summary.get(metric, 0.0) for metric in REQUIRED_METRICS}


def run_local_variant(
    name: str,
    config: dict[str, Any],
    cases: list[dict[str, Any]],
    k: int,
) -> dict[str, Any]:
    results = [
        run_case(
            case=case,
            k=k,
            max_repair_rounds=int(config["max_repair_rounds"]),
            reference_oracle=bool(config["reference_oracle"]),
            use_llm=False,
            llm_command=None,
            replay_records=None,
            jasper_check=False,
            jasper_dry_run=True,
            jasper_replay_records=None,
            jasper_out_root=ROOT / "jasper" / "reports" / "design2sva_ablation_plan",
            context_budget=int(config["context_budget"]),
            native_oracle=None,
            run_harness_diagnostics=False,
        )
        for case in cases
    ]
    summary = summarize(
        results,
        k=k,
        jasper_check=False,
        jasper_dry_run=True,
        jasper_replay=False,
    )
    public_summary = {key: value for key, value in summary.items() if key != "rows"}
    return {
        "variant": name,
        "objective": config["objective"],
        "runner_mode": config["runner_mode"],
        "metrics": metric_subset(public_summary),
        "summary": public_summary,
        "case_count": len(cases),
        "llm_prompts_sent": False,
    }


def run_native_variant(
    name: str,
    config: dict[str, Any],
    cases: list[dict[str, Any]],
    cases_path: Path,
) -> dict[str, Any]:
    payload = build_native_oracle_payload(
        cases,
        cases_path=cases_path,
        variant="correct",
        dry_run=True,
    )
    summary = payload["summary"]
    return {
        "variant": name,
        "objective": config["objective"],
        "runner_mode": config["runner_mode"],
        "metrics": {metric: 0.0 for metric in REQUIRED_METRICS},
        "native_oracle_summary": summary,
        "case_count": len(cases),
        "llm_prompts_sent": False,
    }


def build_ablation_payload(cases_path: Path, limit: int | None, k: int) -> dict[str, Any]:
    cases = load_cases(cases_path)
    if limit is not None:
        cases = cases[:limit]

    variants = []
    for name, config in ABLATION_VARIANTS.items():
        if name == "native_oracle":
            variants.append(run_native_variant(name, config, cases, cases_path))
        else:
            variants.append(run_local_variant(name, config, cases, k=k))

    return {
        "schema_version": "stage14_design2sva_ablation_plan_v1",
        "mode": "dry_run_replay_plan",
        "cases_path": repo_relative(cases_path),
        "k": k,
        "llm_prompts_sent": False,
        "required_metrics": REQUIRED_METRICS,
        "summary": {
            "num_cases": len(cases),
            "k": k,
            "variant_count": len(variants),
            "formal_metrics_status": "not_run",
            "source_counts": {"ablation_plan": len(variants)},
            "fallback_rate": 0.0,
            "valid_json_rate": 1.0,
        },
        "variants": variants,
        "claim_boundary": {
            "supported": "This artifact defines and smoke-runs the ablation machinery locally.",
            "unsupported": (
                "It does not measure hosted-model performance or production signoff quality."
            ),
        },
    }


def render_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Design2SVA Ablation Plan",
        "",
        "This Stage 14 artifact is dry-run/replay-only. It sends no new external LLM prompts.",
        "",
        "## Variants",
        "",
        "| Variant | Runner mode | Cases | Metrics emitted | Objective |",
        "| --- | --- | ---: | --- | --- |",
    ]
    metrics = ", ".join(f"`{metric}`" for metric in payload["required_metrics"])
    for variant in payload["variants"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{variant['variant']}`",
                    f"`{variant['runner_mode']}`",
                    str(variant["case_count"]),
                    metrics,
                    str(variant["objective"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `direct_prompt`, `retrieval_context`, and reachability-guidance rows are local scaffold checks until real model outputs are supplied.",
            "- `retrieval_plus_anti_vacuity_repair` exercises the repair-loop shape without sending prompts.",
            "- `reference_oracle` and `native_oracle` are infrastructure controls, not model-performance rows.",
            "- JasperGold-measured claims require rerunning the same variants with the formal backend available and preserving the resulting JSON artifacts separately.",
            "",
            "## Claim Boundary",
            "",
            "- Supported: ablation configuration, metric schema, and local replay/dry-run plumbing.",
            "- Unsupported: production signoff, broad model quality, or semantic equivalence beyond measured local fixtures.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args(argv)

    payload = build_ablation_payload(args.cases, limit=args.limit, k=args.k)

    out = resolve_repo_path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    plan = resolve_repo_path(args.plan)
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(render_plan_markdown(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "mode": payload["mode"],
                "variant_count": len(payload["variants"]),
                "llm_prompts_sent": payload["llm_prompts_sent"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
