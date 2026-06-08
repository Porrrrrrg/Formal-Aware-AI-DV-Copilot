# Codex Local Configs

The tracked `.codex/` files are optional local orchestration configs used during repository cleanup and review workflows. They are not required by JasperLoop-DV runtime code, evaluation runners, RTL2Repair, or JasperGold flows.

These files should not contain secrets, credentials, API keys, model endpoints, or raw artifact paths. Local runs and generated Codex outputs belong under ignored directories such as `artifacts/` or `.codex/runs/`.

If the project is packaged without Codex orchestration support, these configs can be omitted without changing the formal-aware DV workflow.
