# PR Review Summary: Local Pending Diff

- Repository: `https://github.com/Porrrrrrg/Formal-Aware-AI-DV-Copilot`
- Local branch: `codex/orchestrator/init-task-graph`
- HEAD: `3bb6821e687db39d384abd7f6fcb00cee6f7c6c1`
- Review timestamp UTC: `20260510T215546Z`
- PR id: `local-unopened`
- Decision: `REQUEST_CHANGES`

## Scope

No open GitHub PR exists, so comments and labels were not posted through GitHub.
This review covers the current local pending diff, including typed IR,
adapter skeletons, local DV retrieval benchmark assets, tests, audit artifacts,
local LLM docs/scripts, and GitHub workflow files.

Recommended labels when a PR is opened:

- `review/request-changes`
- `blocked/schema`
- `blocked/ci`
- `needs-owner`

Do not apply `MERGE_READY`.

## Blocking Findings

### 1. Typed IR and adapter API are split into two incompatible contracts

Status: `FAIL`

Evidence:

- `app/models/core.py` defines the canonical Pydantic v1 IR. `Candidate`
  requires `candidate_id`, `run_id`, `problem_id`, and `attempt_id`; `VerifierOutcome`
  requires `outcome_id`, `run_id`, `problem_id`, `candidate_id`, and `attempt_id`.
- `schemas/v1/core.schema.json` is generated from that Pydantic contract.
- The new adapters import `core.schemas` dataclasses instead:
  `adapters/smt/common.py:24`, `adapters/lean/adapter.py:22`.
- `core/schemas.py` defines a second `Candidate` without `candidate_id` or
  `problem_id`, and a second `VerifierOutcome` with `manifest_ref` and
  `raw_status`, which are not allowed by the committed schema.

Reproduction:

```text
python - <<'PY'
import json, jsonschema
from pathlib import Path
from adapters.smt.z3 import Z3Adapter
from core.schemas import ProblemSpec, Candidate
schema = json.loads(Path("schemas/v1/core.schema.json").read_text())
outcome = Z3Adapter(executable="definitely_missing_z3").verify(
    ProblemSpec(problem_id="z3_smoke", tool="z3", language="smt2", statement="(check-sat)"),
    Candidate(run_id="run_z3_smoke", attempt_id="attempt_0001", producer="review", content="(check-sat)"),
)
jsonschema.Draft202012Validator(schema).validate(
    outcome.to_dict(), {"$ref": "#/$defs/VerifierOutcome"}
)
PY
```

Observed result:

```text
VALIDATION_FAILED
Additional properties are not allowed ('manifest_ref', 'raw_status' were unexpected)
payload_keys=artifact_refs,diagnostics,elapsed_ms,exit_code,manifest_ref,metadata,ok,raw_status,status,stderr_ref,stdout_ref,tool
```

Required fix:

- Remove or demote `core/schemas.py` so there is one authoritative runtime model.
- Make Lean/Z3/cvc5 adapters accept and return `app.models.core` objects, or add
  an explicit conversion layer that validates adapter outputs against
  `schemas/v1/core.schema.json`.
- Add a regression test that validates every adapter `VerifierOutcome` against
  `#/$defs/VerifierOutcome`.

### 2. New adapters do not implement the declared adapter protocol

Status: `FAIL`

Evidence:

- `app/core/protocols.py:82` declares `ToolAdapter` with `probe()` and
  `supports()`.
- `app/core/protocols.py:95` declares `VerifierAdapter.verify(..., artifacts=...)`.
- `Z3Adapter` and `LeanAdapter` expose only the legacy `verify(problem, candidate, work_dir=None)`
  shape.

Reproduction:

```text
from adapters.smt.z3 import Z3Adapter
from adapters.lean import LeanAdapter
from app.core.protocols import VerifierAdapter
print(isinstance(Z3Adapter(), VerifierAdapter))
print(isinstance(LeanAdapter(), VerifierAdapter))
```

Observed result:

```text
z3_protocol= False
lean_protocol= False
```

Required fix:

- Implement `probe()` and `supports()` on each adapter.
- Align `verify()` with the declared protocol, including the `ArtifactWriter`
  boundary, or change the protocol and tests to match the intentionally supported
  adapter API.

### 3. CI will not install the project dependencies before pytest

Status: `FAIL`

Evidence:

- `pyproject.toml` now declares runtime dependencies `jsonschema` and `pydantic`
  and dev dependency `pytest`.
- `.github/workflows/ci.yml:112` installs only `ruff pytest jsonschema`.
- `.github/workflows/release-attest.yml:50` installs only `ruff pytest jsonschema`.
- Tests import `app.core.artifacts`, which imports `pydantic`.

Reproduction of the CI install shape:

```text
python -m venv .review-ci-venv
.review-ci-venv/Scripts/python.exe -m pip install -q ruff pytest jsonschema
.review-ci-venv/Scripts/python.exe -m pytest tests/core/test_schemas.py -q
```

Observed result:

```text
ModuleNotFoundError: No module named 'pydantic'
```

Required fix:

- In CI and release workflows, install the package with dev extras:
  `python -m pip install -e ".[dev]" ruff`
- Or install runtime dependencies explicitly before `pytest`.
- Apply the same rule to any workflow job that imports `app.*`.

### 4. PR metadata and branch gate are not satisfied

Status: `FAIL`

Evidence:

- Current branch: `codex/orchestrator/init-task-graph`
- Required pattern: `codex/<agent>/<issue-id>-<slug>`
- No open PR exists and no PR owner metadata can be verified.

Required fix:

- Open a PR with title `[codex][<agent>] <summary>`.
- Declare subsystem owner, issue id, benchmark impact, run id, and validation
  artifacts in the PR template.

## Checklist

| Area | Status | Evidence |
| --- | --- | --- |
| Modularity | NEEDS EVIDENCE | Multiple subsystems changed in one pending diff: typed IR, adapters, retrieval, benchmark registry, workflows, local LLM, reports. Split ownership is not visible in a PR. |
| Typed IR | FAIL | Canonical `app.models.core`/`schemas/v1/core.schema.json` exists, but adapters return incompatible `core.schemas` dataclasses. |
| Adapter API | FAIL | Lean/Z3/cvc5 adapters do not implement `app.core.protocols.VerifierAdapter`. |
| Tests | PASS locally, FAIL in CI | `python -m pytest` passes after `python -m pip install -e ".[dev]"`; the committed workflow install command would miss `pydantic`. |
| Reproducibility | NEEDS EVIDENCE | Manifests and reports are present, but adapter manifests use the non-canonical dataclass schema. Need canonical `RunManifest` validation. |
| Security | NEEDS EVIDENCE | Workflows add CodeQL, secret scanning, least-privilege permissions, and attestations. Existing `copilot/llm_client.py:shell=True` remains a tracked risk but was not changed in this diff. |
| GitHub Automation | FAIL | Workflows are present but CI/release dependency install is incomplete. Local `actionlint` is unavailable. |
| Benchmark Integrity | PASS | `local_dv` split is by design family and excludes answer-bearing case JSON files from the retrieval corpus; tests cover overlap and contamination evidence. |

## Validation Run

Commands run locally:

```text
python -m pip install -e ".[dev]"
python -m pytest
python -m compileall app copilot tools evaluation scripts
python -m app.models.core --write-schema artifacts/tmp_core_schema_review.json
python -m app.retrieval.benchmark_registry
python -m app.retrieval.evaluate --benchmark local_dv --split test --top-k 5 --out-root artifacts/tmp_review_eval
ssh moore "tcsh -fc 'cd ~/Formal-Aware-AI-DV-Copilot; source /vol/eecs391/cadence.env; setenv JASPER_BIN /vol/cadence2018/XCELIUM1809/tools.lnx86/jasper/bin/jg; python3.11 tools/run_jasper.py --design arbiter_rr2 --variant correct --mode prove --dry-run'"
```

Results:

- `pytest`: 20 passed, 6 warnings.
- `compileall`: pass.
- `app.models.core --write-schema`: pass, with a Python `runpy` warning due module pre-import.
- `benchmark_registry`: 30 items, 39 documents, train/dev/test split files.
- `retrieval evaluate`: test split query success rate 1.0, mean recall@5 0.430909, mean MRR 1.0, zero failure buckets, Qdrant unspecified.
- `moore` Jasper dry-run: pass; returned `/home/esf2634/Formal-Aware-AI-DV-Copilot/jasper/reports/arbiter_rr2_correct_prove`.
- CI-shape venv simulation: fail with `ModuleNotFoundError: No module named 'pydantic'`.

Temporary local review artifacts under `artifacts/tmp_*` and the editable-install
`jasperloop_dv.egg-info` directory were removed after verification.

## Generated Review Comments

Comment 1:

`REQUEST_CHANGES: adapters/smt/common.py and adapters/lean/adapter.py return core.schemas.VerifierOutcome, but schemas/v1/core.schema.json defines app.models.core.VerifierOutcome. The adapter payload is not schema-valid and includes manifest_ref/raw_status while omitting outcome_id/run_id/problem_id/candidate_id/attempt_id. Please make adapters use the canonical Pydantic IR or add a schema-validated conversion layer and regression tests.`

Comment 2:

`REQUEST_CHANGES: app/core/protocols.py declares probe(), supports(), and verify(..., artifacts=...), but Lean/Z3/cvc5 adapters do not satisfy the runtime-checkable VerifierAdapter protocol. Align the implementations or the protocol before merging adapter work.`

Comment 3:

`REQUEST_CHANGES: .github/workflows/ci.yml and release-attest.yml install ruff/pytest/jsonschema but not the package runtime dependency pydantic. A clean CI-shaped venv fails collecting tests/core/test_schemas.py with ModuleNotFoundError: pydantic. Install with python -m pip install -e ".[dev]" ruff or install runtime deps explicitly.`

## Orchestrator Message

`REVIEW_FINDING: local pending diff is not MERGE_READY. Blocking issues: adapter outputs are incompatible with schemas/v1 core IR, adapters do not implement app.core.protocols.VerifierAdapter, and CI/release workflows omit project runtime dependency installation. Apply labels review/request-changes, blocked/schema, blocked/ci, needs-owner.`
