# DOC-TEST-001 — Cross-project testing architecture / factual handoff

**CLOSEOUT ADDENDUM (2026-10-12):** User authorized merge. Documentation [PR №14](https://github.com/maxrus82gm-svg/ag_llm/pull/14) merged into `main` (`ae3934eea60851cde2abe88e348701068065e556`). Separate Astra diagnostic CI [PR №13](https://github.com/maxrus82gm-svg/ag_llm/pull/13) merged (`9d7fa6d2ddcdc9124b48ff1075e8e5fb4945102d`), unchanged production/test sources. Local Git/Obsidian sync NOT VERIFIED; F1–F3, runner repairs and one-click implementation remain OPEN. The original RESULT READY / AWAITING MERGE status below is the historical pre-merge handoff, not current status.

**STATUS:** RESULT READY / AWAITING USER REVIEW AND OPTIONAL INDEPENDENT AUDIT  
**Executor/coordinator:** ChatGPT (authorized by user in conversation 2026-10-12)  
**ARCH CLASS:** Cross-project / testing rules / documentation-only  
**SOURCE BASE:** main `96b7d9ecc95f5a8e3a807203ce51ab218bd41b61` (commit #289)  
**WRITE SCOPE:** new testing architecture docs, navigation/routing, short Ultra rule bridges, factual report; **NO** production, test source, runner or existing CI changes.

## Intent (recorded before GitHub writes)

User requested test-first awareness by every LLM from the beginning of development, review of modified code regardless of green tests, reusable accumulating local/GitHub test suites, risk-based test groups, safe intermittent-failure protocol, documentation of only significant tests, separate Web Alarm and Ultra test profiles, and strict simple Obsidian topology: 00 → a single testing architecture → three direct children. Desktop Commander to be used sparingly; local TEMP of Astra optional and replaceable by persisted GitHub evidence.

## Inputs actually inspected

- Canonical routes: `Документация/08_Старт.md`, `000_Задачи для агента.md`, `34_TACTICAL_CONTEXT.md`, `18_Регламент сопровождения документации.md`, `01`, `02`, `09`, `13`, `23/24/25`, `00`.
- Astra report: `reports/ASTRA-WEB02-TEST-ARCH-001/report.md`; pilot source `test_web_alarm_new_invariants.py`; `coverage.json`, `checks.json`, `versions.json`, `pilot-evidence.json`; CI PR #13 results (both 3/3 + 103/103 PASS).
- GitHub source tree check: real `test_web_alarm_*.py`, `test_final_audit.py`, `test_rt002_s0_kernel.py`, runner and workflow.
- Desktop Commander availability/local TEMP was confirmed in the previous interaction, including three helper scripts. They are **not** run or copied: canonical relevant report/evidence is already versioned in the repository; TEMP scripts are temporary packaging/rotation tools, not universal testing infrastructure.

## Canonical document ownership and graph

1. `36_Единая архитектура тестирования.md`: **WHY / architecture / navigation**; only three new outgoing Wiki links.
2. `36.1_Обязательный регламент тестирования для LLM.md`: **WHAT agents MUST do**; seven TEST-...@1 Rule-ID definitions.
3. `36.2_Профиль тестирования Web Alarm Workspace.md`: WA-I01…WA-I13, complex pilot P1–P3, F1–F3, runner, safety oracles, commands and limitations.
4. `36.3_Профиль тестирования Ultra.md`: UL-I-specific needs for server authority, RUN/Verifier, backups, completion, project testing commands and future capabilities.

Other changed files:
- `00_Главная - карта проекта.md`: **one** new Wiki link to 36 only.
- `08_Старт.md`: Rule-ID owner/routing table and canonical roles for four documents, regular code TASK route with INDEPENDENT_PLAN exception; **plain text** references, no new Wiki links.
- `02_Правила разработки и работы с Ultra.md`: short cumulative testing principle and updated graph exception for approved topology.
- `09_Обязательный регламент Ultra.md`: mandatory test-impact text rule alongside existing compile/UI checks, without claiming implementation as server gate.
- Registry/journal/tactical handoff: only factual pending status in branch, no false DONE/VERIFIED and no changes to other active runtime tasks.

## Mechanical checks performed

- Four intended new Markdown docs present on separate `docs/test-architecture-20261012` branch.
- Graph: 00 has one Wiki-link to 36; 36 has three Wiki-links to 36.1, 36.2, 36.3; all children have no outgoing Wiki-links; 08/02/09 contain no added graph links to the testing branch.
- All seven expected TEST Rule-IDs are defined once under 36.1, with machine-readable `rule-meta` contract, matched in 08 route.
- Markdown fenced code counts balanced on all affected documents; no unauthorized 36 Wiki-links outside map/tree.
- Existing project test names referenced in sample profiles were checked against GitHub root listing.
- **NO runtime Python tests run for documentation-only change.** Source/runner/workflow changes: none.

## Continuity and existing task-card ownership

At final reconciliation, `Документация/000_Задачи ChatGPT.md` already contained an unrelated earlier ChatGPT documentation TASK with `RESULT READY / AWAITING INDEPENDENT VERIFICATION` in its user-controlled БЛОК 1; `000_Задачи для агента.md` still routes a separate Web Alarm/Ultra workstream. **Neither was overwritten, rotated, or falsely closed** by this cross-project documentation effort, to preserve user assignment and prior history. This DOC-TEST-001 task is instead discoverable via 05/06/34, its own versioned `reports/DOC-TEST-001/report.md`, and PR №14. The prior task-card states must be reconciled by their actual owners separately; do not treat them as up-to-date Web Alarm rollout facts. This report does not claim pre-execution placement into a personal БЛОК 1.

## What is NOT implemented

- One-click/batch test launcher; common source-manifest+evidence validator; safe shared runner across Ultra/Web Alarm; historical runner defects (0-test green, negative subtest PASS count); F1–F3 Web Alarm repair; any rollout gate, Voice test profile or Ultra runtime enforcement. These are **proposals/gaps**, never claimed as PASS.
- No automatic loading of Markdown by Ultra Server. Global Agent context activation must follow its existing separate assignment/memory routes; adoption in human/developer workflow starts once this proposal is reviewed/merged and synchronized.
- This documentation branch has not been merged into `main` and is not yet visible to the user's local Obsidian checkout without synchronization.

## Documentation Impact

```text
DOC IMPACT: YES
CURRENT STATE IMPACT: NO (runtime unchanged)
ARCHITECTURE IMPACT: YES (development/testing process)
CONTEXT LIBRARY IMPACT: NO (14-16 unchanged)
REGISTRY / ROUTING IMPACT: YES (08)
NEW DOCUMENT REQUIRED: YES (one parent + three distinct children)
CANONICAL OWNER: 36 / 36.1 / 36.2 / 36.3
AFFECTED: 00, 08, 02, 09, short 05/06/34 pending handoff
CONTRADICTION CHECK: REQUIRED; checked, existing 02 absolute no-link rule aligned
LOSS CHECK: PASS for additive content (no old report/history deletion)
```

**NEXT:** user reviews draft PR, may request independent alternative LLM critique; after USER APPROVAL merge and local Obsidian Git sync, verify one-parent-three-child graph visually. Separate scoped TASK for one-click launcher / runner validator or F1–F3 is future work. No automatic testing of Ultra runtime changes is implied.
