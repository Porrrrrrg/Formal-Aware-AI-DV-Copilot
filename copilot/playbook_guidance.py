"""Expected playbook guidance references for prompt and workflow dry-runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaybookGuidanceRef:
    title: str
    path: str
    section: str
    applies_to: tuple[str, ...]

    @property
    def anchor(self) -> str:
        return self.section.lower().replace("/", "").replace(" ", "-")

    def markdown_ref(self) -> str:
        return f"`{self.path}#{self.anchor}` - {self.section}"


PLAYBOOK_GUIDANCE_REFS = (
    PlaybookGuidanceRef(
        title="CEX debug checklist",
        path="copilot/playbooks/cex_debug_playbook.md",
        section="CEX Review Checklist",
        applies_to=("repair", "triage", "demo"),
    ),
    PlaybookGuidanceRef(
        title="assumption/vacuity review checklist",
        path="copilot/playbooks/assumption_vacuity_playbook.md",
        section="Review Flow",
        applies_to=("repair", "triage", "demo"),
    ),
    PlaybookGuidanceRef(
        title="coverage closure decision checklist",
        path="copilot/playbooks/coverage_closure_playbook.md",
        section="Closure Flow",
        applies_to=("coverage", "demo"),
    ),
    PlaybookGuidanceRef(
        title="intent alignment review note",
        path="copilot/playbooks/formal_review_checklist.md",
        section="Checklist",
        applies_to=("repair", "triage", "coverage", "demo"),
    ),
)


def guidance_for_workflow(workflow_type: str) -> list[PlaybookGuidanceRef]:
    return [ref for ref in PLAYBOOK_GUIDANCE_REFS if workflow_type in ref.applies_to]


def prompt_guidance_refs(*titles: str) -> str:
    wanted = set(titles)
    refs = [ref.markdown_ref() for ref in PLAYBOOK_GUIDANCE_REFS if ref.title in wanted]
    return "\n".join(f"- {ref}" for ref in refs)
