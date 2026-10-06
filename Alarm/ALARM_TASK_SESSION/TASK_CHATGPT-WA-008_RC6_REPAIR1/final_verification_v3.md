# RC-6 Repair #1 — Final Verification V3

Date: 2026-10-06
Baseline HEAD: 26111c9e39f8b9de90f1b91b6a75b74bd0412e6d

This file supersedes the earlier intermediate final_regression* evidence for the executor's final factual state.

## Repair-specific
- test_web_alarm_recovery_coordinator_repair1.py: 21/21 PASS.
- compileall: PASS.
- git diff --check: PASS.

## Core focused
Modules:
- test_web_alarm_recovery_coordinator
- test_web_alarm_recovery_coordinator_concurrency
- test_web_alarm_recovery_coordinator_adversarial
- test_web_alarm_recovery_coordinator_repair1
- test_web_alarm_projection
- test_web_alarm_projection_concurrency
- test_web_alarm_resolver
- test_web_alarm_resolver_concurrency
- test_web_alarm_rollback
- test_web_alarm_rollback_concurrency

Result: 176/176 PASS.

## Public-entry focused
Modules:
- test_web_alarm_server
- test_web_alarm_cli
- test_web_alarm_recovery_coordinator
- test_web_alarm_recovery_coordinator_repair1

Result: 55/55 PASS.

## Original independent verifier probes
Unmodified scripts from TASK_CLAUDE-RC6-VERIFY:
- rc6_probes.py: exit 0.
- rc6_probe_interrupted.py: exit 0.

Observed repaired behavior includes:
- completed ADOPT no longer steals later microtask focus;
- corrupt restore point never READY;
- foreign ownership after RETRY re-arm blocks final READY;
- historical-operation RETRY/ABORT do not use later microtask status;
- no half ABORT settlement;
- rollback VERIFIED release-pending is release-only;
- interrupted rollback resumes safely after RESTORED and T_APPLYING landed/not-landed.

## Executor adversarial additions
Additional permanent regressions prove:
- APPLYING + persisted T_DRIFTED + crash before RC-4 finalize is routed back through RC-4, not stale cleanup;
- same persisted-drift crash followed by ABORT finalizes the already-persisted outcome only, then preserves ownership as RECOVERY_BLOCKED;
- PARTIAL/FAILED is never auto-closed/released;
- VERIFIED + claims_released=false + newer ABORT completes release only before ABORT settlement.

## Final full Web Alarm suite
Command family: explicit unittest over every test_web_alarm_*.py module.

Result:
- Ran 439 tests.
- OK.
- skipped=1.
- UNIT_EXIT=0.

Post-suite:
- python -B -m compileall -q web_alarm: PASS.
- git diff --check: PASS.

## Live storage read-only proof
Root derived from web_alarm.workspace_registry.default_storage_root():
C:\Users\REX\AppData\Local\WebAlarmWorkspace

BEFORE full suite:
- FILES=136
- DIRS=41
- SHA256=a9cf87815774d5abdfb8a433af8aca13002d292a2866aa2b27a8901f24c9bff3

AFTER full suite + compile/diff:
- FILES=136
- DIRS=41
- SHA256=a9cf87815774d5abdfb8a433af8aca13002d292a2866aa2b27a8901f24c9bff3

Live storage changed by executor verification: NO.

Status:
RESULT READY / AWAITING RE-VERIFICATION.
WA4-E NOT STARTED.
