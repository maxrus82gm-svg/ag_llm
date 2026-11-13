# Снимок БЛОКОВ 2–4 перед H32 closeout

**Источник:** `Документация/000_Задачи Codex.md`, `main@36c41c79b066b4c19120ce11266a727d10cb7407`, 13.11.2026. Полный дословный сохранённый текст ниже. БЛОК 1/1.1 не включены, их исходное содержание осталось неизменным.

---

# БЛОК 2 — ПЯТЬ ПОСЛЕДНИХ ЗАДАЧ (КОМПАКТНО)

Постоянный архив — №001 Codex и адресные `reports/<TASK-ID>/task_record.json`.

- **08.11 / H-CODEX-000024 / `CODEX-RT002-B2-S1-INVENTORY-RECON-001`:** independent Windows S1 69 PASS + 23 extra PASS/18 mutations; separate S2 72 PASS/1 FAIL; task PARTIAL, S1 bounded PASS, S3b HOLD.
- **08.11 / H-CODEX-000023 / `CODEX-RT002-B2-S3A-DURABLE-LEDGER-001`:** S3a ledger 35/35 author PASS, Run Store 51; independent S3a runtime NOT RUN, privacy/fencing OPEN.
- **07.11 / H-CODEX-000022 / `CODEX-WUA-S5-TURN-UX-RECOVERY-001`:** bounded Windows GUI smoke PASS; RAW cancel, Tcl, 480px residual OPEN.
- **07.11 / H-CODEX-000021 / `CODEX-WUA-S5-TURN-CHECK-DIAG-001`:** Turn diagnostic PARTIAL, historical cancellation RAW cause OPEN.
- **07.11 / H-CODEX-000020 / `CODEX-WUA-CHAT-S5-OFFLINE-FULL-CHAT-001`:** Stage5 fake UI+Turn, independent Windows 387 PASS, live NOT RUN.

---

# БЛОК 3 — КРАТКИЕ ФАКТИЧЕСКИЕ ИТОГИ

- **H24 S1:** changed only `test_rt002_s1_routes.py`; initial 67/69 RED, author+independent 69/69 PASS, 23/23 guarded negative/fake checks PASS, full 18 source mutations detected. Independent S2 exact 72/73 FAIL: old isolation test includes OFFLINE S3a ledger. No real provider / full repo CI.
- **H23 S3a:** Offline durable ledger and 35 authored PASS; independent runtime gate still OPEN; historical adoption, privacy/RAW, durability/fencing require separate actions.
- **H22 Stage5:** Windows user F5, Turn check and two independent Chat histories bounded PASS, residual OPEN.
- **H21 Stage5:** Turn check diagnosis PARTIAL; original canceled RAW issue unproven.
- **H20 Stage5:** independent Windows fake UI 387 PASS, no real GigaChat or clean portability proof.

---

# БЛОК 4 — НЕЗАВИСИМАЯ ПРИЁМКА
---

## WEB28 / 12.11.2026 — H-CODEX-000030 — pre-send READ-ONLY independent bounded PASS

`CODEX-WUA-CHAT-S3B-PRESEND-PREFLIGHT-001` / `H-CODEX-000030`, main №574 `d26c4ad9380b2bb1a0ccd1dd88bdf2facd3c954c`: independent Windows Python 3.12 7/7 OFFLINE PASS, guard0; four H30 cases + 3 adjacent tests, source SHA and author report SHA verified. Three initial synthetic TEMP attempts failed from Windows MAX_PATH; clean rerun in short TEMP all PASS without product edits. **VERDICT: H30 DOC CLOSED, P0/P1 PREFLIGHT RESEARCH ONLY**. Author PARTIAL at submission and separate H31 correction F-01 faithfully preserved. Not full S3b; GitHub dedicated H30 CI pending on same atomic GPT push, H31 physical CMD/browser/full CI/real/OAuth/paid/TEMP cleanup NOT RUN. Review `reports/CHATGPT-WEB28-H30-REVIEW-20261112/review.md`, evidence `reports/CHATGPT-WEB28-H30-REVIEW-20261112/independent_runs.json`. Next only with USER GO narrow Ordinary fake final-wire/S2/S3a one-send; B1/1.1 unchanged.

## WEB29 / 12.11.2026 — H-CODEX-000031 — F-01 TEST launcher independent bounded PASS

`CODEX-WUA-CHAT-S3B-F01-LAUNCH-GUARD-001`; source main №573 `a26b3157`; [GitHub Windows run 43264689001](https://github.com/maxrus82gm-svg/ag_llm/actions/runs/43264689001): **18 existing + 3 reviewer = 21/21 PASS, guard violations 0**. Fail-closed для неподтверждённых script/args/kind под `--require-test`; два approved offline профиля сохранены, STANDARD и CMD не изменены. **VERDICT: PASS / H31 DOC CLOSED в BOUNDED INDEPENDENT OFFLINE scope.** Физический CMD/browser/F5, общий S3b, full CI, real/paid НЕ ПРОВЕРЕНЫ. H30 REVIEW PENDING. Local H30/H31 TEMP cleanup PENDING. Review `reports/CHATGPT-WEB29-H31-F01-REVIEW-20261112/review.md`. USER HARD GATE: независимый зелёный CI → полное обновление регистров/БЛОК4 → единый нумерованный GPT commit → merge пользователем. БЛОКИ 1/1.1 не менялись.


## WEB28 / 10.11.2026 — H-CODEX-000029 — per-chat usage/settings BOUNDED OFFLINE + USER GUI PASS

`CODEX-WUA-CHAT-PERCHAT-USAGE-SETTINGS-001`, main №570 `0aa3846e`; авторские 8 Python + 57 JS PASS, TEST CMD PASS, ранее независимые Windows 65/65 PASS по сохранённому контексту. Пользовательский GUI/F5: 2 Workspace/4 чата; `01_01` сохраняет 150000/15000, другие — 250000/10000. TEST `UNKNOWN` корректен при отсутствующем fake usage. **VERDICT: DOC CLOSED / P0+P1 BOUNDED OFFLINE PASS**, без реального provider cap и live. Не подтверждены реальный usage/20k-кнопка отдельным GUI тестом, broad CI/clean Windows. S3b/Stage7/paid HOLD. Review: `reports/CHATGPT-WEB28-H29-PERCHAT-REVIEW-20261110/review.md`. БЛОК 1 и БЛОК 1.1 не изменять.


## WEB25 / 08.11.2026 — H-CODEX-000024 — S1 inventory OFFLINE independent PASS / product PARTIAL

Source main@`a455d97f` №542, Codex H24/finish ROTATED exit0, B1 WAITING and B1.1 H24 untouched. Independent Remote Desktop Windows SHA matched exact `test_rt002_s1_routes.py`; guarded **S1 69/69 PASS** (exit0 guard0) and **23/23 extra PASS**, 18 in-memory mutation cases. Independent **S2 72/73 (1 FAIL)** due old `test_no_production_module_imports_the_policy_yet` discovering intentionally standalone `ultra_budget_ledger.py`; source-level mismatch, not evidence of live HTTP dispatch. S3a independent test NOT RUN; three author weakening controls not independently replayed. **Verdict S1 TARGETED INDEPENDENT OFFLINE PASS; H24 OVERALL PARTIAL**, S2 remedy separately authorized; S3b/Stage6/Stage7 live HOLD. Report `reports/CHATGPT-WEB25-CODEX-RT002-S1-REVIEW-20261108/review.md`.

## WEB25 / 08.11.2026 — H-CODEX-000023 — RT-002/B2 S3a OFFLINE PARTIAL

Source main@`53d7ce91` №539; Codex finish ROTATED exit0, БЛОК1 WAITING, БЛОК1.1 H23 без вмешательства verifier. Новые два исходника + author evidence: S3a 35 PASS, Run Store 51, S2 73, mutants 3/3 red; S1 67 PASS / **2 FAIL** source inventory. WEB25 проверил 16 источников включая пять CRLF→LF Git normalizations, source state machine, lock and error paths; **NO independent S3a runtime**. **Verdict: PARTIAL / BOUNDED SOURCE+AUTHOR EVIDENCE**, не independent S3a acceptance или S3b readiness. Ordinary Chat policy, historical adoption, RAW wire retention, 4096-events cap, power-loss/fencing и S1 repair OPEN. Review `reports/CHATGPT-WEB25-CODEX-RT002-S3A-REVIEW-20261108/review.md`. Next только отдельная S1 reconcile/independent S3a gate по USER GO; live/paid/Colibri/MCP HOLD.

## WEB23 / 05.11.2026 — H-CODEX-000013 — Stage3 TEST PARTIAL

`CODEX-WUA-CHAT-S3-TURN-IMPLEMENTATION-001` published main@a3b44c6, author finish ROTATED (B1 WAITING/B1.1 exact). Independently Windows CI: 30 Turn/HTTP/prerequisites, 53 Run Store, 171 Python, 161 JS PASS at least once; repeated full Python **1/171 FAIL** `WorkspaceBusyError` in legacy two-process writer test, exact isolated replay **5/5 PASS**, still OPEN. **Verdict PARTIAL / TEST functional**, user GUI not yet run; no real LLM/Stage4 GO. Evidence `reports/CHATGPT-WEB23-CODEX-S3-TURN-REVIEW-20261105/review.md`, №05 `FOLLOWUP-WUA-S3-WS-WRITER-BUSY-001`, event `EVT-WEB23-CODEX-S3-TURN-REVIEW-20261105`. B1/B1.1 not changed by verifier.


## WEB23 / 04.11.2026 — H-CODEX-000012 — independent Windows CI 56 PASS

Independent GitHub Actions run `41885808568` (https://github.com/maxrus82gm-svg/ag_llm/actions/runs/41885808568), source GPT@e14222fb523acc558e57e31eebd1425829fc8651 (product inherited unchanged from main@e3253b4): **53 Run Store/audit + 3 original Stage3 oracles PASS, 0 FAIL/SKIP**. Verifier inspected decoded runner logs and completed job conclusion SUCCESS; verdict **PASS / TARGETED INDEPENDENT WINDOWS CI**. Full regression/real Workspace/picker NOT RUN; residual FOLLOWUP OPEN, separate Stage3 USER GO required. B1/B1.1 were not edited. Event `EVT-WEB23-RUNSTORE-S3-WINDOWS-CI-20261104` in №06.

## Previous — WEB23 / 04.11.2026 — H-CODEX-000012 — bounded source/author evidence

**Verifier:** ChatGPT WEB23. **Source:** main@e3253b41502ac2d76c61c0faf7a5b660e2cc7eb9, `reports/CODEX-WUA-RUNSTORE-S3-GATE-REPAIR-001/`. Independently inspected source, negative/positive author oracles, logs, manifest, history and finish. **Verdict: PASS / BOUNDED SOURCE + AUTHOR EVIDENCE** for audit-path refusal, writer-lock serialization and explicit recovery; independent Windows/CI/restart runtime **NOT RUN**. Author 389 PASS/5 SKIP; WinError 10053 initial run remains unresolved despite successful retry. One `test_run_store_v2.py` source SHA mismatch traced exactly to single CRLF→LF at line 479 during publication; no semantic change, strict full-manifest SHA PASS not asserted.

**SLOT:** author finish ROTATED exit0, B1 WAITING, B1.1 exact assigned task and H-CODEX-000012; verifier did not alter either slot. **OPEN:** independent P9/Stage3 Windows regression, existing picker, Stage3 Turn not implemented, staging/Tk/portability and other FOLLOWUP. No Stage3/live/paid/Blueprint/Colibri/MCP GO. Full review `reports/CHATGPT-WEB23-CODEX-RUNSTORE-S3-GATE-REVIEW-20261104/review.md`, №06 `EVT-WEB23-RUNSTORE-S3-GATE-REVIEW-20261104`. Proposed GPT doc commit awaiting user merge.

## Previous — WEB22 / 04.11.2026 — Stage3 prerequisite diagnosis

`CODEX-WUA-CHAT-S3-TURN-RECOVERY-001`: source+author-evidence diagnostic PASS, product Stage3 PARTIAL/NOT IMPLEMENTED; original RED 1 PASS/2 FAIL, bounded source review, independent runtime NOT RUN. Permanent review `reports/CHATGPT-WEB22-CODEX-S3-PREREQ-REVIEW-20261104/review.md`, event `EVT-WEB22-CODEX-S3-PREREQ-20261104`.

## Previous — WEB22 / 04.11.2026 — Workspace/Chat UX

`CODEX-WUA-CHAT-UX-LIVE-FIX-001` AMENDMENT 01: source+author-evidence PASS bounded, user accepted Windows GUI first/following chats; full independent runtime/negative GUI NOT RUN. Review `reports/CHATGPT-WEB22-CODEX-UX-LIVE-FIX-REVIEW-20261104/review.md`, event `EVT-WEB22-CODEX-UX-LIVE-FIX-20261104`. Earlier WEB21/LLM15 verdicts remain in exact published `main@e3253b4` card snapshot, their reports and №06; not deleted from history.

---

**CURRENT WEB23:** Run Store repair source+author-evidence bounded PASS; independent pinned Windows/CI NOT RUN. Stage3 Turn NOT IMPLEMENTED; user GO needed. B1 WAITING, B1.1 H-CODEX-000012.
