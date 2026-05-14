"""Typed objects for JasperLoop agent runs and formal backend evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AGENT_SCHEMA_VERSION = "v1"


class AgentModel(BaseModel):
    """Base model for agent-facing objects.

    These models intentionally allow extension fields. The committed
    `copilot/schemas/*.schema.json` files remain the public compatibility
    contracts for prompts and evidence packets.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class BackendStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SYNTAX_FAILED = "syntax_failed"
    VACUOUS = "vacuous"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    ERROR = "error"
    DRY_RUN = "dry_run"
    UNKNOWN = "unknown"


class CheckStatus(str, Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    PROVEN = "proven"
    FALSIFIED = "falsified"
    COVERED = "covered"
    UNCOVERED = "uncovered"
    UNREACHABLE = "unreachable"
    VACUOUS = "vacuous"
    NOT_FLAGGED_VACUOUS = "not_flagged_vacuous"
    UNDETERMINED = "undetermined"
    SYNTAX_ERROR = "syntax_error"
    ERROR = "error"


class Task(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    task_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    design_id: str | None = None
    case_id: str | None = None
    property_id: str | None = None
    intent: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClockResetSpec(AgentModel):
    clock: str = Field(min_length=1)
    reset: str | None = None
    clock_edge: Literal["posedge", "negedge"] = "posedge"
    reset_polarity: Literal["active_high", "active_low", "unknown"] = "unknown"


class HelperCodePolicy(AgentModel):
    allowed: bool = False
    allowed_kinds: list[str] = Field(default_factory=list)
    max_lines: int = Field(default=0, ge=0)
    rationale: str = ""


class Design2SVAEvaluationMetadata(AgentModel):
    benchmark: str = "local_design2sva"
    split: str = "local"
    expected_result: str = "syntax_or_proof_check"
    reference_available: bool = False
    reference_sva: str | None = None
    expected_proof_status: str = "not_run"
    notes: str = ""


class Design2SVATask(Task):
    task_type: Literal["design2sva"] = "design2sva"
    design_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    property_id: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    module_name: str | None = None
    design_rtl_path: str = Field(min_length=1)
    harness_header_path: str = Field(min_length=1)
    visible_signals: list[str] = Field(min_length=1)
    clock_reset: ClockResetSpec
    helper_code_policy: HelperCodePolicy = Field(default_factory=HelperCodePolicy)
    evaluation_metadata: Design2SVAEvaluationMetadata = Field(
        default_factory=Design2SVAEvaluationMetadata
    )

    @field_validator("visible_signals")
    @classmethod
    def require_nonempty_visible_signals(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("visible_signals must not be empty")
        return value


class Design2SVACandidate(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    property_id: str = Field(min_length=1)
    sva: str = Field(min_length=1)
    helper_code: str = ""
    referenced_signals: list[str] = Field(default_factory=list)
    intent_summary: str = ""
    source: str = "unknown"
    repair_metadata: dict[str, Any] = Field(default_factory=dict)
    proof_metadata: dict[str, Any] = Field(default_factory=dict)


class BackendError(AgentModel):
    kind: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
    source: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class CheckResult(AgentModel):
    status: CheckStatus = CheckStatus.NOT_RUN
    properties: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    report_path: str | None = None
    error_path: str | None = None


class BackendResult(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    backend: str = "jaspergold"
    status: BackendStatus = BackendStatus.UNKNOWN
    syntax_result: CheckResult = Field(default_factory=CheckResult)
    proof_result: CheckResult = Field(default_factory=CheckResult)
    vacuity_result: CheckResult = Field(default_factory=CheckResult)
    counterexample_paths: list[str] = Field(default_factory=list)
    parsed_counterexamples: list[dict[str, Any]] = Field(default_factory=list)
    raw_log_paths: list[str] = Field(default_factory=list)
    report_dir: str | None = None
    raw_report_paths: dict[str, str | None] = Field(default_factory=dict)
    command: list[str] = Field(default_factory=list)
    returncode: int | None = None
    elapsed_ms: int | None = Field(default=None, ge=0)
    structured_errors: list[BackendError] = Field(default_factory=list)
    feedback: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_legacy_check_dict(self) -> dict[str, Any]:
        """Return the flat shape consumed by existing evaluation scripts."""

        syntax_pass: bool | None
        if self.status == BackendStatus.DRY_RUN:
            syntax_pass = None
        elif self.syntax_result.status in {
            CheckStatus.PASSED,
            CheckStatus.PROVEN,
            CheckStatus.COVERED,
            CheckStatus.NOT_FLAGGED_VACUOUS,
        }:
            syntax_pass = True
        elif self.syntax_result.status in {
            CheckStatus.FAILED,
            CheckStatus.SYNTAX_ERROR,
            CheckStatus.ERROR,
        }:
            syntax_pass = False
        else:
            syntax_pass = None

        return {
            "syntax_pass": syntax_pass,
            "jasper_returncode": self.returncode,
            "proof_status": first_property_status(self.proof_result),
            "vacuity_status": first_property_status(self.vacuity_result),
            "feedback": self.feedback,
            "report_dir": self.report_dir,
            "properties_report": self.raw_report_paths.get("properties"),
            "vacuity_report": self.raw_report_paths.get("vacuity"),
            "log": self.raw_log_paths[0] if self.raw_log_paths else None,
            "backend_status": self.status.value,
            "structured_errors": [error.to_dict() for error in self.structured_errors],
            "counterexample_paths": self.counterexample_paths,
        }


class EvidencePacket(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    case_id: str
    design_id: str
    task_type: str
    variant: str | None = None
    design_intent: list[str] = Field(default_factory=list)
    failing_property: dict[str, Any] = Field(default_factory=dict)
    active_assumptions: list[dict[str, Any]] = Field(default_factory=list)
    jasper_result: dict[str, Any] = Field(default_factory=dict)
    counterexample_summary: dict[str, Any] = Field(default_factory=dict)
    trace_summaries: list[dict[str, Any]] = Field(default_factory=list)
    signal_role_map: dict[str, str] = Field(default_factory=dict)
    coverage_context: dict[str, Any] = Field(default_factory=dict)
    coverage_evidence: dict[str, Any] = Field(default_factory=dict)
    vacuity_context: dict[str, Any] = Field(default_factory=dict)
    rtl_context: dict[str, Any] = Field(default_factory=dict)
    allowed_issue_types: list[str] = Field(default_factory=list)
    allowed_next_actions: list[str] = Field(default_factory=list)


class RepairAttempt(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    attempt_id: str = Field(min_length=1)
    round_index: int = Field(ge=0)
    property_id: str
    input_sva: str
    output_sva: str | None = None
    feedback: str = ""
    backend_result: BackendResult | None = None
    source: str = "unknown"
    llm_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunManifest(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    manifest_type: str = "AgentRunManifest"
    run_id: str = Field(min_length=1)
    created_at: datetime
    task: Task
    evidence_packet_path: str | None = None
    backend_results: list[BackendResult] = Field(default_factory=list)
    repair_attempts: list[RepairAttempt] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    status: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class EvaluationResult(AgentModel):
    schema_version: Literal["v1"] = AGENT_SCHEMA_VERSION
    evaluation_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    num_cases: int = Field(ge=0)
    metrics: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    source_counts: dict[str, int] = Field(default_factory=dict)
    output_family_counts: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def first_property_status(result: CheckResult) -> str | None:
    if result.status not in {CheckStatus.NOT_RUN, CheckStatus.PASSED, CheckStatus.FAILED}:
        return result.status.value
    for row in result.properties:
        if row.get("status"):
            return str(row["status"])
    return None
