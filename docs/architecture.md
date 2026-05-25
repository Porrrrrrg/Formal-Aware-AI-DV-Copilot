# Architecture

JasperLoop-DV is repository-root based. The architecture is a formal-evidence loop, not a server-path-specific implementation.

```text
RTL + spec + SVA + assumptions + coverage goals
        |
        v
JasperGold/Cadence runner in a configured environment
        |
        v
report, trace, vacuity, and coverage parsers
        |
        v
schema-validated evidence packet
        |
        +--> SVA generation agent
        +--> SVA repair agent
        +--> failure triage agent
        +--> coverage closure agent
        |
        v
candidate output, recommendation, replay artifact, or JasperGold re-check
        |
        v
DV engineer review
```

The evidence packet is the boundary between tool evidence and model reasoning. It contains design identity, property or coverage intent, active assumptions, parser output, counterexample or witness summaries, signal-role maps, RTL excerpts, allowed labels, and allowed next actions.

JasperGold remains the oracle where a formal check is run. The agent layer proposes interpretations and edits; it does not establish correctness by itself.

## Components

- `tools/run_jasper.py`: stages benchmark JasperGold runs under ignored `jasper/reports/`.
- `tools/parse_jg_report.py`: parses conservative property and coverage status rows.
- `tools/parse_jg_trace.py`: parses text and VCD traces into cycle-indexed events.
- `tools/build_evidence_packet.py`: builds schema-valid packets from cases, reports, traces, manifests, and RTL excerpts.
- `copilot/agents/`: deterministic and LLM-enabled agent entrypoints.
- `copilot/prompts/`: JSON-only prompts with explicit allowed labels/actions/signals.
- `copilot/schemas/`: JSON schemas for candidate and evidence-packet contracts.
- `evaluation/`: scaffold, replay, and optional LLM/JasperGold runners.

Raw reports, traces, generated harnesses, logs, and run artifacts stay local by default.
