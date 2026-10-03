# TASK 151B — remote history

## 2026-10-01 — start
TASK151A and KT-1 were independently rechecked after connection recovery and remain DONE. TASK151B starts from canonical doc20 Evidence Freshness requirements and current task_planner/server implementation.

Initial code finding:
current non-persistence evidence matching uses stage_id + OK/executed + tool + arguments_sha256. It does not yet require run_id, plan_version or repair generation. execution_defect reopens stages while retaining the same evidence list, and install() can preserve SATISFIED unchanged stages across plan versions. This is the first freshness gap to close.

## 2026-10-01 — TASK151B closure / KT-2 DONE

Evidence freshness/revision binding is implemented and verified. Evidence applicability now includes task/run/plan/stage/generation/requirement/tool+args/dependency-state/execution/source identity. Replan/repair/state drift cannot silently reuse old PASS; unknown identity fails closed. Final Audit PASS binds a concrete evidence snapshot and is rechecked before SUCCESS.

Local evidence: focused 74 OK, expanded 95 OK, identity/storage 46 OK, full suite 320 OK, explicit freshness matrix 150 OK, py_compile/UI smoke/diff-check PASS.

Fresh live profiles all succeeded: B1 20261001_154859_053216 (42,528 tokens), B2 20261001_154927_e54fa7 (61,092), B3 20261001_155015_f999db (37,485); all Final Audit PASS with final_audit_evidence_snapshot_bound.

KT-2 FRESHNESS is closed. Next canonical stage is TASK151C Compact Final Audit Packet + Task-scoped Git Evidence / KT-3, not yet started.
