# Self-Check SVA Repair Prompt

Repair exactly one SystemVerilog Assertion, then internally self-check the final candidate before returning JSON.

Before finalizing, verify:

1. Every non-keyword identifier appears in `allowed_signal_whitelist` or is the supplied `property_id`.
2. The assertion has balanced parentheses and a terminating semicolon.
3. The clock/reset form is consistent with `reset_clock_semantics`.
4. The repaired SVA addresses the property intent rather than merely weakening the assertion.
5. The explanation names the repair class without claiming JasperGold proof.

Return only the final JSON object matching `sva_repair_output.schema.json` with `property_id`, `sva`, and `explanation`. Do not include the self-check transcript.
