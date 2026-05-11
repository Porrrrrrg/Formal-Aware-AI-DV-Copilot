from __future__ import annotations

from pathlib import Path

from copilot.agents.coverage_closure_agent import build_prompt as build_coverage_prompt
from copilot.agents.dv_triage_agent import build_prompt as build_triage_prompt


ROOT = Path(__file__).resolve().parents[1]


def test_prompt_templates_reference_playbook_guidance_without_raw_skill_text() -> None:
    prompt_paths = [
        ROOT / "copilot" / "prompts" / "sva_repair_prompt.md",
        ROOT / "copilot" / "prompts" / "sva_repair_cex_prompt.md",
        ROOT / "copilot" / "prompts" / "triage_prompt.md",
        ROOT / "copilot" / "prompts" / "coverage_closure_prompt.md",
    ]

    for prompt_path in prompt_paths:
        text = prompt_path.read_text(encoding="utf-8")
        assert "copilot/playbooks/" in text
        assert "do not copy playbook prose" in text


def test_triage_and_coverage_prompt_render_playbook_references() -> None:
    packet = {
        "case_id": "case_demo",
        "task_type": "coverage_closure",
        "coverage_context": {"coverage_goal": "cov_demo", "expected_reachable": True},
    }

    triage_prompt = build_triage_prompt(packet)
    coverage_prompt = build_coverage_prompt(packet)

    assert "copilot/playbooks/assumption_vacuity_playbook.md#review-flow" in triage_prompt
    assert (
        "copilot/playbooks/coverage_closure_playbook.md#closure-flow"
        in coverage_prompt
    )
    assert "gold_label" not in triage_prompt
    assert "gold_label" not in coverage_prompt
