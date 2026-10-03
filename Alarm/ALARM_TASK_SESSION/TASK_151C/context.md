# TASK 151C — Compact Final Audit Packet + Task-scoped Git Evidence / КТ-3

STATUS: ACTIVE — documentation activation first; runtime mutation has not started.
ARCH CLASS: Quality Transition / Final Audit / Evidence Packaging / Runtime Efficiency
PRIMARY PROFILE: 13_Архитектура оперативной верификации и контроля выполнения задач.md
SECONDARY PROFILES: 01, 03, 20, 21

## Goal
Сделать Final Audit / Dredd packet полным по смыслу, task-scoped и компактным; убрать workspace-wide Git diff как default payload без потери authoritative Server facts, requirements, negative/conflicting evidence, freshness identity и reproducibility.

## Safety / execution order
1. Сначала записать активную TASK в блок 1 `000_Задачи для агента.md`; блок 2 должен оставаться последней закрытой TASK 151G-DIAG-R031.
2. Затем выполнить code audit фактической Final Audit / Git evidence реализации.
3. Сформировать минимальный design, только затем менять runtime.
4. После изменений: targeted → expanded regression → full unittest → py_compile → UltraApp smoke → git diff --check.
5. Большие live RUN не выполнять до отдельного решения; R-027/R-031 остаются future 151G stress cases.

## KT-3 acceptance
- Dredd packet task-scoped и механически complete по active requirements.
- Server fail-closed до Dredd при missing mandatory material.
- Workspace-wide diff не default.
- Unexpected/external/unattributed task-relevant changes не скрываются.
- TASK 151B freshness и остальные authority/permission/verification invariants сохранены.

## Next safe step
Activate TASK 151C in block 1 of 000, independently read it back, then audit actual code before choosing edits.
## Code audit result
- `_collect_final_audit_evidence()` currently calls `_agent_git_status(root, audit_policy)` and `_agent_git_diff(root, [], audit_policy)`, so Final Audit observes the whole READ scope by default.
- `lifecycle.evidence()` is appended only after collector return; collector completeness does not mechanically verify Planner requirement coverage.
- Current packet has mutation facts, run-owned filesystem hashes, deterministic verification state and new-file material, but only a names-only Executor tool summary.
- TASK 151B freshness snapshot is bound around Final Audit and must remain authoritative.

## 151C implementation design
1. Build task-scoped target paths from accepted task plan artifacts/evidence dependencies plus current-RUN mutation/run-owned/verification/tool targets.
2. Internal Final Audit Git status/diff must use only those paths; if no task paths exist, Git observation is explicit NOT_APPLICABLE instead of workspace-wide.
3. Include compact accepted task plan/state, requirement→source coverage, compact task evidence records, mutation receipts/material and freshness snapshot metadata in one server-built packet.
4. Planner-enabled Final Audit treats missing mechanical requirement coverage as critical and blocks before Dredd.
5. Preserve legacy/direct Final Audit compatibility when no Planner lifecycle exists.
6. Recheck evidence freshness before and after packet collection and after verifier as today; stale packet is discarded.
7. Update verifier FINAL prompt to consume packet completeness/coverage/task-scoped Git semantics.
8. Add regression tests for task-scoped paths, no default workspace-wide diff, missing requirement fail-closed, unattributed target changes, freshness metadata and planner integration.