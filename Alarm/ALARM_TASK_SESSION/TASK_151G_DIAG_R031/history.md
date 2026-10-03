# TASK 151G-DIAG-R031 — history

2026-10-01: User reported wild token consumption in R-031 and requested both canonical documentation and a whole-code analysis focused on the problem.

Live evidence recovered from `.ultra/audit/.../20261001_182057_e90f93`: 668,898 total tokens, of which 665,505 were Executor. Planner consumed 3,393; Dredd was never called.

Provider accounting showed deterministic amplification: request context ~27k chars initially, ~319k after first full `read_file(ultra_ui.py)`, and ~604k after a second full read. The two serialized tool-result blocks are ~279,325 chars each.

Static audit covered server.py message assembly/tool dispatch/stage reset/read limits/Guard P1/tool reserve; task_planner.py stage context/persistence/tool reserve; audit_storage.py/run_store.py diagnostic delta storage; provider_accounting.py measurement; relevant tests. Runtime code remains unchanged.
2026-10-01: Diagnostic closed. Canonical docs 000/01/03/05/06/13/20/21 were updated and independently checked. Targeted git diff --check PASS. No runtime code mutation was performed. Canonical NEXT remains 151C; R-027 and R-031 are retained as mandatory future 151G stress regressions.
