# TASK 151G-DIAG-R031 — Executor Context / Token Explosion Audit

STATUS: DONE — diagnostic/documentation audit closed; runtime code was not modified.
PRIMARY PROFILE: 03_Чаты, проекты и контекст.md
SECONDARY PROFILE: 13_Архитектура оперативной верификации и контроля выполнения задач.md
ARCH CLASS: Quality Transition / Executor Context Composition / Runtime Efficiency

## Goal
Разобрать R-031 целиком по runtime evidence и коду, зафиксировать root causes дикой token/context amplification и отразить проблему в canonical documentation. Эта diagnostic TASK не меняет runtime и не закрывает/не запускает 151C/151G implementation.

## Confirmed live evidence
- T-031 / R-031 = run 20261001_182057_e90f93, status BLOCKED, Final Audit PENDING.
- TOTAL usage 668,898 tokens; Executor 665,505; Planner 3,393; Dredd 0.
- 15 Executor provider calls, 14 physical tool calls.
- Request context grew ~27k chars at API #1 → ~319k at #8 after full read_file(ultra_ui.py) → ~604k at #13 after a second full read_file(ultra_ui.py).
- Each full ultra_ui.py tool-result block contributes ~279,325 serialized chars to subsequent Executor requests.
- Run remained in stage_1 throughout; stage reset therefore never occurred before BLOCKED.

## Code audit findings to verify/document
- server.py appends every assistant function_call and full function result to the live `messages` transcript; full `read_file` content is not compacted before re-send.
- `read_file` permits logical text up to MAX_AGENT_FILE_BYTES = 2 MiB; unlike read_file_range, it has no per-result model-context cap.
- stage_context(reset=True) removes accumulated function transcript only after stage transition/replan/final repair; no bounded compiler exists inside a long-running stage.
- stage tool visibility is capability-scoped, not target-scoped: READ+WRITE stage can read unrelated/future-stage files within READ scope.
- Guard P1 catches only a narrow repeat pattern and did not stop separated duplicate full reads of ultra_ui.py.
- Audit storage context delta is storage optimization only; provider remains stateless and receives rebuilt full messages each API call.
- Tool reserve protects mandatory remaining calls but does not prevent context amplification before reserve activation.

## Test setup defects in R-031
- B2_live_01 was reused and b2_logic.py already contained STATUS_PREFIX = "READY" before the run.
- RAW TASK used short file names rather than the full fixture-relative paths; Planner contract therefore used root-relative b2_logic.py/b2_contract_test.py/ultra_ui.py semantics inconsistent with intended isolated fixture.
- Planner chose verify_file_content(kind=equals, value='STATUS_PREFIX = "READY"') although the requirement was presence/contains, so later exact verification would have been semantically wrong even if stage_1 completed.

## Closure
Static code audit and canonical documentation updates are complete. Markers were verified in 000/01/03/05/06/13/20/21; targeted git diff --check passed. Canonical NEXT remains TASK 151C. Future TASK 151G remains PLANNED and must use R-027 + R-031 as mandatory stress/negative regressions.

## Post-close cleanup
Ordinary TASK151G_DIAG_R031 safety backups under Alarm were removed after verified closure; remaining count = 0. Permanent continuity evidence remains in ALARM_TASK_SESSION/TASK_151G_DIAG_R031; live R-031 evidence remains untouched in .ultra/audit.