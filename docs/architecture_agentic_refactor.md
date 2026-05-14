# Agentic Formal Verification Architecture

This refactor moves JasperLoop-DV toward an evidence-centric formal agent. The
LLM remains a proposal engine. JasperGold, parser outputs, replay manifests, and
human review remain the evidence boundary.

## Package Boundaries

| Layer | Owns | Must Not Own |
| --- | --- | --- |
| `tools/` | CLI-compatible Jasper runners, report parsers, trace parsers, packet builders | Prompt policy or agent decisions |
| `copilot/backends/` | Typed formal backend interface and JasperGold facade | LLM prompts or benchmark scoring |
| `copilot/retrieval/` | RTL index, module interfaces, assigns, always blocks, hierarchy, signal lookup | Gold labels or answer-bearing case metadata |
| `copilot/agents/` | Prompt construction, deterministic fallbacks, output normalization | Tool execution semantics |
| `evaluation/` | Metrics, provenance separation, scaffold-vs-LLM reporting | Formal proof claims without backend evidence |
| `app/models/agent.py` | Typed Task, EvidencePacket, BackendResult, RepairAttempt, AgentRunManifest, EvaluationResult | Replacement of committed public JSON schemas |

## Evidence Flow

```text
RTL/spec/SVA/assumptions/coverage
        |
        v
JasperGold or replay backend
        |
        v
BackendResult
  - syntax_result
  - proof_result
  - vacuity_result
  - counterexample paths
  - raw report/log paths
  - structured parser/tool errors
        |
        v
EvidencePacket + RTL retrieval index
        |
        v
SVA generation, SVA repair, triage, coverage closure
        |
        v
EvaluationResult with source_counts and output_family_counts
```

## ProofLoop-Style Context

`copilot/retrieval` adds a lightweight AST-like RTL index that works without
commercial dependencies. It extracts module interfaces, declarations,
continuous assigns, always blocks, simple instances, signal drivers, signal
uses, hierarchy, and clock/reset candidates. The fallback parser is regex-based
and records source ranges so future agents can cite RTL evidence.

Example:

```python
from pathlib import Path
from copilot.retrieval import build_rtl_index, get_signal_logic

index = build_rtl_index([Path("benchmarks/rv_buffer/rtl/rv_buffer_correct.sv")])
logic = get_signal_logic(index, "in_ready", module_name="rv_buffer")
```

For `rv_buffer`, `in_ready` resolves to the continuous assignment
`!full || out_ready`. For `arbiter_rr2`, `turn` resolves to the sequential
update block. This is retrieval infrastructure only; it is not a ProofLoop
performance claim.

## Migration Path

1. Keep existing CLI tools stable. `tools/check_generated_sva.py` and
   `tools/run_jasper.py` remain runnable as before.
2. Use `copilot/backends.JasperBackend` for new code that needs typed formal
   evidence instead of flat dictionaries.
3. Continue validating public packets and agent outputs against
   `copilot/schemas/*.schema.json`; typed Python models are internal companions.
4. Store generated RTL indexes under run artifacts, not as committed caches.
5. Report real LLM results only when `source_counts`, fallback/error rates, and
   hallucinated-signal rates show that the model path actually ran.

## Claim Boundary

Scaffold success, deterministic fallback output, replay output, dry-run
manifests, and local-compatible subset completion must not be described as real
LLM quality, JasperGold proof, or production readiness. Real LLM results require
recorded backend/source/error/fallback fields. Real formal claims require
JasperGold summaries tied to checked harnesses, assumptions, properties, and
tool versions.
