# Программа качественного перехода: оптимизация runtime, контекстов и памяти

**Статус:** ПРИНЯТО КАК КАНОНИЧЕСКАЯ ПЕРЕХОДНАЯ ПРОГРАММА / РЕАЛИЗАЦИЯ ПОЭТАПНАЯ.

Этот документ временно владеет общей программой качественного перехода после стабилизации TASK 144–151.
Он определяет порядок оптимизации model calls, context composition, Final Audit evidence и будущей historical memory.

Фактическое CURRENT-состояние остаётся в `01_Архитектура и текущее состояние.md`.
Конкретные TASK и статусы остаются в `05_Реестр задач.md`.
История исполнения всей программы ведётся отдельно в [[21_Журнал качественного перехода - решения, метрики и аудит|21_Журнал качественного перехода]].

После завершения программы подтверждённые решения должны быть разнесены по профильным документам.
Документы 20 и 21 удаляются только после отдельного zero-loss reconciliation и финального документационного аудита.

**Актуальное правило маршрута (2026-10-11 / сохранение результатов Ultra):** единственная действующая новая execution-последовательность после утверждения RT-002/FINAL-B2 — **§5а ниже**. Вся первоначальная волна 151A–151J хранится как история уже завершённых 151A/151B, исторических целей и отложенных задач, **НЕ как параллельный NEXT**. Старые 151C/KT3 и 151D/E/F/H/I не закрыты и не запускаются сами; старые критерии КТ и memory 152–154 не получают автоматического PASS. При несовпадении схем применять §5а, исторические свидетельства искать в 21 и Git. Архив/immutable 33.3 не переписывать.

## 1. Цель

Существенно уменьшить токены, latency и лишние model calls без ослабления correctness.

Неприкосновенные свойства:

- authoritative Server;
- неизменный RAW TASK;
- permissions и scope;
- обязательные физические проверки;
- независимый Dredd Final Audit;
- fail-closed lifecycle;
- полный воспроизводимый Audit.

Главный принцип: модель принимает смысловые решения и создаёт материал; Server выполняет однозначно определённые операции, проверяет контракты и управляет состоянием RUN.

## 2. Исходный benchmark и проблема

Историческая точка T-021 / R-021:

| Роль | Model calls | Токены |
| --- | ---: | ---: |
| Planner | 2 | 7 008 |
| Executor | 6 | 28 640 |
| Dredd | 1 | 37 166 |
| **Всего** | **9** | **72 814** |

Дополнительно:

- physical tools: WRITE → exact READ → exact EQUALS;
- Dredd verification context: около 145 568 символов;
- Executor SYSTEM: около 21 230 символов на request;
- Global Ultra Context: около 16 151 символа;
- Project Context: около 2 038 символов;
- основная стоимость RUN находится во входных контекстах, а не в completion.

T-021 является историческим ориентиром, но не единственным benchmark.
Экономия доказывается воспроизводимыми B1/B2/B3 на зафиксированной конфигурации.

## 3. Инварианты перехода

1. RAW TASK не подменяется Planner summary, Digest или Micro History.
2. Permissions, receipts, exact verification, IDs и statuses не lossy-compress моделью.
3. `executed=false` не считается доказательством исполнения.
4. Stale, missing или contradicting evidence не позволяет SUCCESS.
5. Compact model packet не заменяет полный Audit.
6. Exact semantics equals/contains/sha256/newline/escaping/arguments fingerprint сохраняются.
7. Planner и Dredd остаются независимыми ролями там, где они действительно нужны.
8. Любая экономия принимается только вместе с regression и live evidence.

## 4. Целевая логика обычного RUN

```text
USER TASK
  ↓
Persistent RAW Chat
  ↓
Server + Context Compiler
  ↓
Planner
  ↓
Validated Task Contract
  ↓
Executor — только смысловой выбор / создание материала
  ↓
Server mutation path
  permissions / scope / backup / preconditions / receipt
  ↓
Server Direct Exact Evidence
  exact READ / exact VERIFY
  ↓
Server Completeness + Freshness Gate
  ↓
Server factual candidate ИЛИ semantic Executor final
  ↓
Compact Final Audit Packet
  ↓
Dredd
  ↓
Server terminal gates
  ↓
SUCCESS
  ↓
Run Store full Audit
  ↓
Structured Task Digest
  ↓
Micro History / Relevant Prior Facts
```

Server не спрашивает модель о действии, если принятый контракт уже однозначно определяет допустимый invocation.
Модель остаётся обязательной там, где требуется смысловой выбор, генерация материала или независимая семантическая проверка.

## 5. Порядок работ

### Стабилизационное завершение

- TASK 150 — UI binding: Chat → Task Block → RUN → Planner/Audit.
- TASK 151 — integrated regression + CURRENT documentation reconciliation.
- После 151 фиксируется STABLE BASELINE S1.

### Историческая/отложенная оптимизационная волна 151A–151J (НЕ текущая последовательность исполнения)

- **151A — Benchmark + Context Accounting + Usage Accounting.**
  B1/B2/B3, включая B1-clean и B1-dirty. Каждый provider attempt получает identity/outcome; каждый context block измеряется.
- **151B — Evidence Freshness.**
  Привязка evidence к run/plan/stage/requirement/state revision; stale evidence не закрывает новый requirement.
- **151C — Compact Final Audit Packet + Task-scoped Git Evidence.**
  Dredd получает полный по смыслу, но компактный пакет; workspace-wide diff перестаёт быть default payload.
  Recovery CODEX-ULTRA-151C-RECOVERY-001 от 2026-10-09 подготовлен к независимой проверке: RESULT READY / AWAITING INDEPENDENT VERIFICATION. КТ-3 остаётся PENDING; findings, offline checks и ограничения — в документе 21, правила packet — в документе 13. Переход к 151D разрешён после независимого PASS ChatGPT.
- **151D — Server Direct Exact Evidence.**
  Exact READ/VERIFY из принятого контракта выполняются Server через существующие permission/scope/budget gates без лишнего Executor decision call.
- **151E — Server Factual Final Report.**
  Полностью детерминированная задача получает server-owned factual candidate; semantic final остаётся за моделью там, где нужен смысл.
- **151F — Modular Global Context.**
  CORE + применимые policy modules вместо повторной передачи всего Global Context.
- **151G — Stage Context Compiler.**
  Working set текущей stage вместо бесконечного function/tool transcript. R-027 и R-031 являются обязательными stress/negative inputs: full tool outputs должны сохраняться в Run Store, но не бесконечно повторяться в каждом stateless provider request. Compiler обязан удерживать bounded in-stage material, выбирать stage-relevant facts/results, отдельно обрабатывать большие read outputs и не терять RAW TASK, authoritative Server facts, negative evidence, requirement/freshness identity. Regression должен доказывать, что повторный large `read_file` не раздувает каждый следующий Executor request на сотни тысяч символов.
- **151H — Planner Prompt Optimization.**
  COMMON CORE + INITIAL / READINESS / REPLAN projections.
- **151I — Role Budgets.**
  Наблюдение превращается в bounded enforcement только после доказанной корректной сборки context.
- **151J — Integrated Optimization Regression / Consolidation.**
  Совместный B1/B2/B3, negative matrix, rollback switches, сравнение before/after.

## 5а. RT-002/B2 — ЕДИНСТВЕННЫЙ текущий маршрут реализации Ultra (утверждён 2026-10-10)

**2026-10-14 / CURRENT S2 — BOUNDED INDEPENDENT SOURCE REVIEW ACCEPTED WITH EXECUTION LIMIT:** `CLAUDE-RT002-S2-001`, `CLAUDE-RT002-S2-REPAIR-001`, `CLAUDE-RT002-S2-REPAIR-002`; source main@76335ffb83373b6af0dff9f5c0081d250b7d835a (user commit №324). Pure `ultra_budget_policy.py` is **not imported by production** and does **not** impose paid-call limits; no S3a/S3b/S3c/S5 performed. Source-only independent ChatGPT review verified all 73 core test methods correspond exactly to MANIFEST, 74th optional provenance method, and closure of two original repair findings (terminal conflicts / JSON types) plus two follow-up findings (corrupt scope identity / float-division token underestimation). In particular 10269 B / stored 4.1076 requires exact integer ceiling 2501, not float 2500; 82152 B exceeds 20000-token threshold. Claude-reported offline: S2 core 73/73 PASS, provenance 74/74 PASS (342 embedded=local), S1 69/69 PASS, S0 166/166 PASS; all 13 mutation controls expected exit 1. ChatGPT did NOT independently execute S2/S1/S0 on this new SHA; no Ultra CI runs at exact SHA. **S2 BOUNDED INDEPENDENT SOURCE-REVIEW ACCEPTED WITH EXECUTION LIMIT** as safe research/policy input for next dependency stage, **NOT new independently executed test-suite VERIFIED**, not live, not defaults approval. Key unresolved USER DECISIONS: candidate A/B/C or custom, margin/min_samples, missing_profile, MCP/compressor, Final Audit protected reserve (observed R-029/030 ~75.6k/78.2k), executor max_tokens, role attempts, precached:null, full-read cap; REPAIR-002 U1 bytes/token floor, U2 malformed scope quarantine, U3 scope-id length; REPAIR-001 R1 sparse duplicate terminal representation. **S3a NOT ASSIGNED: requires separate USER GO**, and must implement authoritative durable reservation/concurrency with no bypass. See 21, 36.3, report `Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S2-REPAIR-002/repair_report.md`.

**2026-10-14 / CURRENT S1 — INDEPENDENT SOURCE-REVIEW ACCEPTED WITH EXECUTION LIMIT:** RT-002/B2 S1 — 2026-10-14 / CLAUDE-RT002-S1-001 + REPAIR-001/002. Публикация main@b309b18e87b20775806b1222abd5a7e3eb6bd018 (user commit №318); production runtime и S0 tests не изменены. R-031 по RAW: 15 Executor calls, два полных READ-блока resend 8+3, отсутствие сброса внутри stage и в DIRECT; семь LLM HTTP POST плюс отдельный OAuth POST, MCP без учёта, Compressor вне Run Store; UNKNOWN, best-effort accounting и canonical/wire hash divergence переданы в предпосылки S2/S3. Исходные находки независимого review S1 F1 (ложный exit 0 при SKIP/evidence) и F2 (неполная инвентаризация alias/multiplicity) закрыты Claude в REPAIR-001 и REPAIR-002; проверены по опубликованному коду. Итоговый `test_rt002_s1_routes.py` по отчёту SHA-256 `4465d47716e8876adf78f7245eb85a9505ac0a8b0aa6632d658afcb71576a66e`, 69 методов и точный MANIFEST. **Исполнение:** Claude сообщил S1 69/69 PASS (guard 0, evidence 0, exit 0) и S0 166/166 PASS; ChatGPT независимо подтвердил структуру и код, **НО самостоятельно эти новые 69 тестов не запускал**: доступного Ultra CI на точном SHA нет. Это ограниченная acceptance S1 как evidence/route research для dependency S2, **НЕ** независимая executable-suite VERIFIED, НЕ live acceptance и НЕ реализация бюджета/guard. R-026 writer attribution UNRESOLVED; реальное использование MCP — USER DECISION; S2 **NOT ASSIGNED, separate USER GO required**. Историческая фраза S1 NOT ASSIGNED в нижней записи 2026-10-11 — архивное состояние, не CURRENT. См. 21, 36.3, Alarm/ALARM_TASK_SESSION/TASK_CLAUDE-RT002-S1-REPAIR-002/repair_report.md.

**2026-10-11 / CURRENT S0 INDEPENDENT OFFLINE PASS:** ChatGPT independently ran unchanged RT-002 S0 guarded suite via authorized Desktop Commander DESKTOP-SC96D3U (M:\GitHub\ag_llm, Python 3.12.10): **166/166 PASS, 0 FAIL, 0 ERROR, 0 SKIP, 0 isolation violations; exit 0, 110.073 s**. Manifest contains original F01–F04 and all 11 terminal-callback methods. Command `.venv/Scripts/python.exe -B test_rt002_s0_kernel.py`. Original and post-run file hashes equal: server.py SHA-256 `44d8cc8affaf9c76272f74ec19e046352e8a19a094c3e48e2dc37ccda6159f54`, test_rt002_s0_repair.py `860f723f4c864deb0fbf6a7699a0ef9b44a29fc6c08038cffb026b36e32fb868`, runner `cf9b1d771e7e83888378108a8a6de1fc8e5bcc6e3673f6fc0b6ec5b1fb821e3b`. Local temporary logfile `C:\Users\REX\AppData\Local\Temp\codex-rt002-s0-baq6h0ex\unittest.log` SHA-256 `c64fc45950b9c387b7cc1486459f5b30a4d13b3f5c49a131733eb79267ed5817` (hash independently reread), `result.json` manifest/observations. This is ChatGPT runtime evidence, not merely Codex-reported 166. **S0 bounded OFFLINE kernel gate: INDEPENDENT ACCEPTED / VERIFIED.** Historic user-operated live R-036/T-036 BLOCKED permission rejection and R-037/T-037 WRITE/READ/EQUALS SUCCESS + Dredd PASS remain separate; no real live destructive callback injection. A synchronous `on_event` can see provisional SUCCESS before corrective BLOCKED; very-late external races and unavailable durable corrective BLOCKED after storage failure remain known limits. No source changes, Git commands, paid models or network calls during guarded suite. **S1 NOT ASSIGNED — separate USER GO/TASK required.** Old 151C/KT3 PARKED/PENDING; S6b/151G gated by S13a. ARCH Ultra 01/13/20/21, not WA 23–25 or Voice 12. The #250/#247 paragraphs below are unchanged historical evidence snapshots, not CURRENT verification status.

**S0 REPAIR handoff (2026-10-10 / user commit №250):** `CODEX-RT002-S0-REPAIR-001` modifies production `server.py`, `run_store.py`, `audit_storage.py` and regression suites; **Codex-reported 155/155 offline PASS, 0 guard violations**. Independent code review considers F01–F04 repair plausible, but **no independent executable verification** (both Remote desktops offline); terminal `run_finished SUCCESS` callback integrity window remains an **unreproduced adversarial question** requiring targeted test. This is a factual status update **NOT S0 acceptance / NOT 151C DONE**; dependent S1+, 151G remain locked until a documented independent result. UI STOP backlog stays separate.

**S0 actual outcome (2026-10-10 / commit №247):** Codex standalone offline reported **97=93 PASS + 4 FAIL (0 errors/skips, exit 1)** with FOUR HIGH proof failures / TWO causes: evidence from READ/VERIFY can be bound to a later filesystem fingerprint; absent mandatory durable AuditThreadRecorder/tool_finished record can leave packet apparently complete and RUN marked SUCCESS. Independent GitHub source inspection confirms the suspicious code paths; **independent execution not performed (Remote devices offline)** and server/planner local byte/EOL identity has not been fully reconciled. **S0 = FINDINGS / NOT ACCEPTED FOR NEW WAVE; no dependent S1/S2/etc** until authorized focused repair, retained regression and independent rerun. This is a factual safety finding, not plan B2 reapproval or 151C/KT3 DONE. Canonical design/immutable B2 unchanged.

**Постоянная независимость от Круглого стола:** этот §5а сохраняет утверждённое решение, полный граф predecessors, контракт безопасности, матрицу V1–V13, A1–A8, границы OFFLINE/LIVE и отложенные узлы. Даже если оперативные слоты 28–35 будут позднее очищены по отдельному решению, §5а остаётся authoritative execution owner. Очистка 33.3 НЕ разрешает удалять его единственный архивный sealed snapshot, trace принятия и Git provenance; исторические причины F01–F15 консолидированы ниже. При возникновении расхождения с sealed B2 остановить handoff и сверить, не менять решение молча.

**Статус:** USER PLAN APPROVED — `RT-002/FINAL-B2` (immutable GitHub commit №242 `e7365ea773c9adc4e813e05a58810e40b4de4bb4`; blob `05cfcd9f3a4bcc26e9dab81a6bcb744b4ed15550`; SHA-256 `c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf`), внешняя запись USER PLAN APPROVAL в `28`. Это новая **каноническая ветка execution TASK**, утверждённая после RT-002 и Codex REVIEW-1, а **не** объявление об уже выполненном коде. Исходная нумерованная 151A–151J ниже/выше сохранена как историческая/отложенная программа; в точках конфликта **для новой RT-002 волны применять эту §5а**.

**Статусы/переходы:** `151C / КТ-3` = PARKED / RESULT READY / AWAITING INDEPENDENT VERIFICATION / **НЕ DONE**. 151D/E/F/H/I и V13 = DEFERRED и **не получают** ложного PASS от новых gates. Зависимости старой 151D/E-ветки остаются обязательными для самой ветки, но **для новой аварийной волны** старый `151C DONE` не является required predecessor — вместо этого по отдельному доказательству применяются **S0** и перед compiler **S6a**. До accepted S0 dependent новые TASK запрещены. **S6b/151G запрещён до independent ACCEPTED S13a**, даже если S3/safety код уже написан. Данная dependency override осознанно утверждена человеком вместе с B2 и не означает общего пропуска КТ-3/4/5.

**Исполнение:** только **одна активная Codex implementation TASK за раз**, если человек не изменит маршрут; пользователь назначил первой `CODEX-RT002-S0-001` / **S0** и запросил **GPT-6 Sol, Very High**. Реальный backend/effort проверить в интерфейсе, requested ≠ independently verified. Codex — свободный инженер в рамках конкретной TASK: собственные локальные исследования, релевантные offline tests/fixtures/adversarial checks и корректные предложения; ограничения не запрещают инициативу. Но он не вправе менять полномочия, чужие TASK, USER PLAN APPROVAL или реализовывать следующие узлы без отдельного поручения. Каждая задача завершает **RESULT READY → независимый ChatGPT verifier → USER acceptance/новая TASK**; не выдавать self-test за DONE.

| № / раздел B2 | Явные predecessors (перед **началом**), ответственный тип | Evidence/verification/human check |
| --- | --- | --- |
| **S0** / fresh baseline gate | USER PLAN APPROVAL + verified handoff; независимый kernel analyst/verifier | Source/permission/exact args, mandatory packet, negative/freshness/replay, безопасный offline snapshot. Существенный drift ⇒ BLOCKED. Узкая пригодность scope, НЕ старый КТ-3 |
| **S1** / baseline and routes | approved snapshot, после отдельной TASK assignment; evidence/transport | R031 raw 8+3 offline, 7 POST sites + mode callers, Chat/Compressor boundary, unknown и precise provenance; не live |
| **S2** / budget policy | independently ACCEPTED S0 и S1; Server policy/UI owner | validated bytes/attempts/RUN policy, conservative units, UNKNOWN, protected reserve, будущие UI defaults после mock calibration |
| **S3a** / durable budget ledger | ACCEPTED S2; ledger owner | reserve/terminal/late/UNKNOWN/crash/concurrent state machine mock; failure fail-closed |
| **S3b** / physical pre-HTTP guard | ACCEPTED S3a+S1; transport | Все LLM physical sends, denied=0, final body bound+hash, tool schemas, standalone policies |
| **S3c** / reserve before mutation | ACCEPTED S3b+S0; Server/evidence | tool + provider verification reserve, blocked when insufficient, no stale SUCCESS |
| **S4** / file read limits | ACCEPTED S2; production apply после S3b; tools | отдельный full-read/request cap, honest unsupported >current physical bound, no silent partial |
| **S5** / UI/policy snapshot | ACCEPTED S2; runtime demo после S3b/S4; UI/settings | edit/save/restart/reset, independent Planner/history/Final Audit, live RUN immutable effective revision |
| **C1** / final protocol | ACCEPTED S0; R032 fixture; result owner | JSON protocol negative, human answer + user-requested JSON positive, no false PASS |
| **C2** / paths/predicates | ACCEPTED S0; focused fixtures; Planner/tool owner | unambiguous base/target/scope, contains!=equals, no guessed path |
| **S9** / usage accounting | ACCEPTED S1+S3a; accounting | unique physical attempts, UNKNOWN/cached/duplicate/late; no made-up billing |
| **S13a** / independent emergency release | independently accepted S3c+S4+S5+C1+C2+S9; separate verifier | **Независимый OFFLINE PASS/ACCEPTED**, all physical routes bounded, restart/rollback/UI/negative evidence, not LIVE/КТ-7 DONE |
| **S6a** / evidence/expansion | ACCEPTED S0+S3b+S3c+S4; context verifier | actual material + rights/freshness/source generation/negative evidence/tool pairing; missing→BLOCKED |
| **S6b / минимальная 151G** | **independently ACCEPTED S13a + S6a**, C1/C2 required correctness cases accepted; context owner | bounded stage+DIRECT/repair/diagnostic working sets; R031 replay without lost material, not full old context stack |
| **S7** / Inspector | ACCEPTED S3b+S6a, implementation completion after S6b; UI | true sent/denied/planned, source locators, truncation+freshness, safe preview |
| **S10** / factor independence | ACCEPTED S5+C1+S9; post-compiler factor matrix after S6b; policy | Planner/history/Audit 2×2×2, independent settings without bypass |
| **R1** / dirty research | ACCEPTED S1; evidence analysis | frozen clean/dirty injected evidence, causal delta FOUND or UNRESOLVED, no local Git |
| **S13b / future 151J** | ACCEPTED S13a+S6b+S7+S10 + R1 result; independent verifier | All A1…A8, B1/B2/B3, false BLOCKED+semantic regressions, UI, **LIVE PENDING** |
| **D / V-13** | Separate user permissions + own historical KT prerequisites | 151D/E/F/H/I, modular contexts, dialogue/compressor/rates/memory 152–154, not an RT-002 emergency prerequisite |

**Минимально исполнимая критическая последовательность:** S0/S1→S2→S3a→S3b→S3c плюс S4/S5/C1/C2/S9→**independent S13a PASS** → S6a→S6b→S7/S10→S13b. S6a может быть начат по собственным listed predecessors до S13a, но compiler **S6b нельзя начинать до accepted S13a**. Все predecessors требуют independent acceptance, а не только Codex self-report. Ответственные лица/точный write scope назначаются отдельной TASK; общие server.py/ultra_ui.py/verifier_runtime.py не писать конкурентно.

**Матрица непропускаемых решений** (source exact §6 B2): V1→S1; V2→S1/S6/S13b; V3→S2/S3/S13a (до 151G); V4→S4+request cap/S5; V5→S6a/b/S7; V6→C1; V7→S9; V8→R1 **research only**; V9→A1…A8; V10→this approved handoff; V11→S5/S10; V12→C2; V13→D deferred. **Acceptance A1…A8** принадлежит B2 §7 и здесь обязателен без сокращения: A1 separated large read; A2 2×2×2 roles/history/audit; A3 all pre-HTTP routes/boundaries; A4 recovery/cancel/concurrency; A5 duplicate/late/UNKNOWN; A6 dirty/clean causal evidence; A7 internal protocol vs explicit JSON; A8 missing/truncated/wrong-target evidence. B1/B2/B3 positive benchmarks + negative, fake socket/credential isolation, UI smoke и rollback — в B2 §7–8; не выдавать `offline passed` за `LIVE VERIFIED`.

**Hard safety contract** (source B2 §4–5): authority на final serialized HTTP body и durable reserve-before-send; policy bytes/read/attempts/RUN с model-specific estimate (bytes/4 ≠ гарантированный token cap); UNKNOWN liability, output and mandatory tool/provider verification reserve, no balance reset on retry/replan/restart/UI, same ledger across modes, no paid network in offline. No actual material loss, full source+generation+ACL/freshness/negative preserved; old compiler rollback только под общим guard. UI задаёт все основные настраиваемые полями с единицами/defaults, отдельными Planner/history/Audit controls и human-readable denied reason. False BLOCKED/usefulness измеряются отдельно от экономии tokens. No premature fixed numeric defaults/prod enable/paid stress.

**Live vs offline:** прежняя §10 остаётся целью **полной КТ-7**, но введён **отдельный приёмочный режим для аварийной волны**: approved offline acceptance допускает S0…S13a и безопасное bounded S6b в рамках матрицы; это не закрывает прежние live KT6/KT7. Полная live серия только по особому USER GO/лимиту/stop criteria и отдельному acceptance. Даже если old §13 diagram визуально ведёт через 151C, для RT-002 применяется эта утверждённая вставка; старые KT3/4/5 остаются PENDING до их собственных доказательств.

**Документационное владение:** `20` = канонический owner исполнения и зависимостей, `21` = факты и истории реальных проверок, `05` = статусы, `34/000` = текущая навигация; `33.3 B2` immutable approved reference, `28` внешний approval/seal. При каждой фактической TASK сверять локальный source snapshot и observed evidence; Git history/commit/branch — только внешнему уполномоченному координатору, **никакого локального Codex Git/GitHub**. Контроль результата: scope, source-version, independent tests, honest limitations, human readable UI/demo или метод проверки; user может принять/попросить исправления до следующей TASK.


### Zero-loss перенос финального REVIEW-1 / B2 — постоянный индекс причин и доказательств

Этот индекс является частью утверждённого маршрута Ultra и сохраняется независимо от оперативного Круглого стола. **Не создавать по нему новые TASK без USER GO.** Статус ACCEPTED здесь означает принятие требования в B2, **не** исправленный код и не PASS этапа. Первоначальные отзывы сохраняются как immutable Git history/архив, однако следующий исполнитель может восстановить основания из этого раздела и §5а выше.

| Finding REVIEW-1 | Принятое решение / защита / узел B2 |
| --- | --- |
| F01 HIGH | ACCEPTED: не выдавать 151C за принятую; PARKED, узкий S0 вместо полного старого T0 |
| F02 HIGH | ACCEPTED conditionally: явный revised dependency graph новой ветки, старая ветка не получает PASS; §5а является принятой ревизией |
| F03 HIGH | ACCEPTED: S1/S3b исследуют 7 физических LLM POST мест и всех mode-callers, в том числе Chat и Compressor |
| F04 HIGH | ACCEPTED: S3a/S3b durable reserve, UNKNOWN, crash/concurrency и pre-send enforcement |
| F05 HIGH | ACCEPTED: bytes != tokens != billed money, output reserve, cached и UNKNOWN учитывать отдельно |
| F06 HIGH | ACCEPTED: budget ledger authoritative, сбой хранения ⇒ fail-closed; diagnostics/UI не могут обходить gate |
| F07 HIGH | ACCEPTED: S6a/b actual material, права, source/generation/freshness, отрицательные факты и protocol pairing |
| F08 HIGH | ACCEPTED: C1 блокирует внутренний JSON как human final, но сохраняет legitimate explicit JSON output |
| F09 MEDIUM | ACCEPTED: S4 не обещает range/find за физическим лимитом reader, отдельные read/request caps |
| F10 MEDIUM | MODIFIED: существующие Planner/Audit флаги сохранить, историю отделить раньше, S10 тестирует 2×2×2 |
| F11 HIGH | ACCEPTED: Git координируется отдельно, seal/approval не подменяют независимый handoff |
| F12 MEDIUM | ACCEPTED: A1–A8 точно охватываются до общей приёмки; offline != live |
| F13 MEDIUM | ACCEPTED: C2 точные paths/predicates, R1 dirty-causality только исследование |
| F14 MEDIUM | ACCEPTED: rollback компилятора остаётся под тем же hard budget guard; долги UNKNOWN не сбрасываются |
| F15 LOW | MODIFIED: owner по ответственности, конкретный агент в отдельной TASK, никаких ложных live/verified статусов |

**Итог:** 13 ACCEPTED, 2 MODIFIED, 0 REJECTED. Все 9 HIGH закрыты **на уровне требований утверждённого B2**, не как завершённые production fixes. Приемочные сценарии A1–A8, их oracle и позитивные B1/B2/B3 изложены в §5а; каждый из них обязателен для соответствующего независимого acceptance. Утверждённая версия: RT-002/FINAL-B2, seal commit №242 `e7365ea773c9adc4e813e05a58810e40b4de4bb4`, blob `05cfcd9f3a4bcc26e9dab81a6bcb744b4ed15550`, SHA-256 `c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf`. Архивные inputs: первоначальный 33 (T0–T13), 32 (V1–V13), 31 synthesis, Codex 33.1 REVIEW-1 №238 (15 findings). Подтверждение USER PLAN APPROVAL и handoff хранится также в 28 и Git, но **для практического продолжения достаточно 20 §5а + 21 evidence + 05 task states + профиль 13**. Никакая будущая очистка 28–35 не может считаться zero-loss без проверки этой матрицы, sealed locators и raw evidence retention.

## 6. Память после оптимизационной базы

Память не является способом лечить текущий перерасход T-021 и не внедряется раньше 151J.

- **TASK 152 — Server Structured Task Digest.**
  Server-owned IDs/status/artifacts/evidence refs/open items; optional Compressor narrative отделён от authoritative structure.
- **TASK 153 — Rolling Micro History.**
  Recent digests, chronological ledger, pinned OPEN items, archive overview. Исходные digests не удаляются.
- **TASK 154 — Relevant Prior Facts / Context Compiler V2.**
  Релевантные факты извлекаются из structured digests/source records; Micro History остаётся обзором, а не единственным источником истины.

Compressor запускается threshold/batch based, а не автоматически после каждой маленькой задачи.
Compressor не имеет authority менять terminal status, permissions, receipts или verification result.

## 7. Final Audit Packet — целевой принцип

Dredd не должен получать весь workspace только потому, что он доступен READ policy.

Compact packet должен содержать:

- RAW TASK;
- accepted contract и все действующие requirements;
- requirement → applicable evidence coverage;
- actual material, необходимый для смысловой проверки;
- mutation facts и receipts;
- exact verification + freshness;
- unexpected / external / unattributed changes;
- unresolved / contradicting facts;
- candidate final response;
- completeness metadata.

Server проверяет механическую полноту packet.
Dredd проверяет смысловую полноту RAW TASK и фактического результата.
Если обязательный материал механически отсутствует — Dredd не вызывается для угадывания.

## 8. Direct execution — граница допустимого

Server Direct Exact Evidence разрешается только если:

- stage допускает server evidence completion;
- invocation уже однозначно задан accepted contract;
- tool входит в allowlist;
- permissions/scope/budget разрешают вызов;
- зависимости и порядок известны;
- смысловой выбор отсутствует.

Первая версия ограничивается exact `read_file` и поддерживаемыми режимами `verify_file_content`.

Server не выбирает без модели:

- что исследовать;
- какой файл считать целевым при неоднозначности;
- какой вариант решения лучше;
- какие произвольные проверки придумать.

В Audit обязательно фиксируется initiator: MODEL или SERVER.

## 9. Контекстные бюджеты

Сначала measurement, затем enforcement.

Стартовые ориентиры для небольшой задачи:

| Роль | Целевой вход |
| --- | ---: |
| Planner INITIAL | 2–4k |
| Planner READINESS | 1–3k + material |
| Planner REPLAN | 3–6k + state |
| Executor | 2–4k + material |
| Dredd FINAL | 2–6k + material |

Нельзя молча обрезать RAW TASK, actual material или отрицательное evidence.
При превышении: deduplicate → remove optional history → compact deterministic facts → explicit expansion → fail-closed.

## 10. Benchmark и критерии приёмки

Профили:

- B1 — маленький файл: WRITE → exact READ → exact EQUALS → Final Audit.
- B2 — изменение существующего кода + compile/test/smoke.
- B3 — аналитическая/содержательная задача, где Executor реально нужен.

Для B1 используются clean и заранее dirty Workspace.
Для сравнения — одинаковые модели, permissions, task content и исходное состояние.
Положительные benchmark выполняются несколькими повторами; ориентир — минимум 5 на профиль/конфигурацию с медианой и диапазоном.

Каждая оптимизация проходит:

1. targeted tests;
2. integration tests;
3. full suite + relevant UI smoke;
4. live B1/B2/B3;
5. negative regression;
6. metrics/Audit comparison;
7. documented rollback method.

Обязательное условие — ноль известных false PASS в проверенной matrix.

Цель B1:

- основной рубеж: ≤20k tokens при сохранении всех обязательных проверок;
- хороший диапазон первой волны: 15–25k;
- амбициозный ориентир после prompt optimization: 11–15k.

Это ориентиры, а не обещание. Экономия считается по воспроизводимому baseline, а не по одному удачному RUN.

## 11. Краткий план контрольных точек

| КТ | Доказательство для перехода |
| --- | --- |
| **КТ-0 — S1** | TASK 150/151 закрыты; baseline воспроизводим; current docs согласованы |
| **КТ-1 — ACCOUNTING** | каждый model attempt и каждый context block объясним и измерим; UNKNOWN usage не считается нулём |
| **КТ-2 — FRESHNESS** | stale evidence не может закрыть requirement после mutation/replan/repair |
| **КТ-3 — COMPACT AUDIT** | Dredd packet task-scoped, полный по требованиям и отрицательным фактам; workspace-wide diff не default |
| **КТ-4 — DIRECT EVIDENCE** | B1 сохраняет три physical tools, но READ/VERIFY больше не требуют Executor decision calls |
| **КТ-5 — FACTUAL FINAL** | deterministic B1 не требует Executor для фразы «готово»; Dredd проверяет тот же factual candidate |
| **КТ-6 — CONTEXT V2** | modular SYSTEM + Stage Compiler + Planner projection не повышают protocol/repair error rate |
| **КТ-7 — OPTIMIZED BASE** | integrated B1/B2/B3 и negative matrix зелёные; B1 целится ≤20k; rollback paths проверены |
| **КТ-8 — MEMORY** | 152–154 дают bounded historical context без full Chat и без подмены authoritative facts |
| **КТ-F — FINAL RECONCILIATION** | все принятые решения разнесены по профильным docs; 20/21 больше не содержат уникальных фактов и могут быть удалены |

Контрольная точка не закрывается только по code review.
Для каждого рубежа обязательны соответствующие tests/live evidence и запись в документе 21.

## 12. Журнал программы и временный характер 20/21

Каждая TASK программы 150–154 и подзадачи 151A–151J получают запись в:
`21_Журнал качественного перехода - решения, метрики и аудит.md`.

Запись должна содержать:

- baseline/configuration;
- что изменилось;
- сохранённые invariants;
- tests/integration/live;
- positive/negative outcomes;
- tokens/calls/tools/latency;
- известные ограничения;
- решение по контрольной точке;
- rollback;
- Documentation Impact.

До финального reconciliation 20/21 являются рабочими переходными источниками.
После КТ-F их подтверждённое содержание переносится в постоянные профильные документы, затем 20/21 удаляются отдельной TASK только после проверки zero-loss.

## 13. Порядок исполнения — только RT-002/B2 §5а

**Канонический активный план:** таблица predecessors и acceptance §5а; не копировать в этот раздел конкурирующую устаревшую схему. Для навигации: `S0 (+ S1 после acceptance)` → `S2` → `S3a/S3b/S3c` с указанными в §5а параллельными `S4/S5/C1/C2/S9` → отдельная независимая `S13a` → `S6a` → `S6b` (минимальная 151G) → `S7/S10` и `R1` → `S13b`. **Это обзор, не замена таблицы зависимостей §5а:** отдельные predecessors могут позволять начало S6a до S13a, но S6b только после independently accepted S13a + S6a.

**Неисполняемый исторический маршрут:** прежняя цепочка 151C → 151D → 151E → 151F → 151G → 151H → 151I → 151J и контрольные точки КТ-3/4/5 не являются текущим NEXT после USER PLAN APPROVAL RT-002. Отложенные задачи остаются в реестре `05` со статусами PARKED/DEFERRED, а решения и фактическая история — в `21` и Git; это не отменяет обязанности их когда-либо закрыть по отдельному решению. Memory `152–154` и полный live benchmark `КТ-7` не разрешены автоматически.

**Текущая консервация после independent verification 2026-10-11:** S0 REPAIR #252 INDEPENDENT 166/166 PASS (ChatGPT protected runner; exit 0, guard 0; complete audit in 21), **S0 offline VERIFIED**, S1 not assigned without USER GO. Earlier T-036 BLOCKED/T-037 SUCCESS support live functional behavior, not adversarial callback injection. Provisional SUCCESS and residual races documented in 21. 151C/KT3 deferred, 151G gated by S13a. Ultra 01/13/20/21 distinct from WA 23–25 and Voice 12.

## 14. Accounting contract

Для каждого физического обращения к provider фиксируются:

```text
provider_attempt_id
logical_call_id
role / mode
request context schema/version
request block list
source references
chars / UTF-8 bytes
token estimate
request snapshot/hash
terminal outcome
provider usage
```

Terminal outcome минимум:

- completed;
- provider_error;
- timeout;
- transport_error;
- parse_error;
- cancelled.

Если provider usage недоступен, значение остаётся UNKNOWN, а не превращается в ноль.
`usage.complete=true` допустим только при доказанном полном учёте известных попыток.
Final Audit, Planner Review и будущий Compressor входят в общий расход системы.

## 15. Evidence freshness identity

Перед direct Server execution обязательна отдельная TASK 151B.

Evidence должно позволять установить как минимум:

```text
task_block_id
run_id
plan_version
stage_id
stage attempt / repair generation
requirement identity
tool
arguments_sha256
target / dependency identity
observed state hash or revision
execution sequence
executed
result
source record id
```

Timestamp является хронологией, но сам по себе не доказывает freshness.

Replan/repair не могут автоматически наследовать старый PASS.
Изменение зависимого target после проверки должно инвалидировать применимость старого evidence.
Если зависимость неизвестна, используется консервативный fail-closed путь.

Final Audit PASS также относится к конкретному evidence snapshot.
Перед SUCCESS Server повторно подтверждает terminal invariants и отсутствие значимого state drift.

## 16. Обязательная regression matrix

### Positive

- B1 new file + exact READ + EQUALS + Final Audit.
- B2 code change + required compile/test/smoke.
- B3 semantic/analytical task.
- ALREADY_SATISFIED по текущему контракту.
- Mixed task: physical artifact + required user-facing explanation.

### Semantic defects

- RAW TASK требует четыре условия, Planner contract содержит только три.
- План выбрал неправильный artifact, но физически выполнился без ошибок.
- Candidate final утверждает неподтверждённое действие.
- Server factual mode ошибочно выбран для смысловой задачи.

### Evidence defects

- equals FAIL, затем PASS другой проверки.
- READ неправильного target.
- verification до обязательной mutation.
- target изменён после PASS.
- replan повторно использует stage id.
- repair происходит после прежнего successful evidence.
- state меняется во время Final Audit.
- unresolved record/hash/reference.
- обязательный actual material был truncated.

### Permissions / attribution / Workspace

- WRITE или VERIFY disabled.
- target вне scope.
- Server direct path пытается обойти policy.
- dirty Workspace с заранее изменёнными файлами.
- внешний процесс меняет тот же target.
- tracked / untracked / deleted changes.
- невозможно доказать отсутствие изменений вне наблюдаемой области.

### Protocol / model behavior

- invalid Planner JSON/enums.
- double-escaped exact text.
- READY при реальных unresolved requirements.
- empty / punctuation-only / serialized tool-markup final.
- provider timeout/error/parse error с доступным usage.
- exhausted repair/replan budget.
- более простая поддерживаемая модель, если она назначена.

Для каждого поддерживаемого model profile отдельно сравниваются false PASS, false BLOCKED, protocol errors, repairs и token cost.

Сокращённый prompt не принимается, если выигрыш съедается дополнительными repairs или ухудшается correctness.

## 17. Storage performance — отдельная ветка измерений

Run Store profiling начинается с 151A, но изменение durability не входит автоматически в token optimization.

Измеряются:

- append / serialization;
- fsync;
- index lookup/update;
- context reconstruction;
- UI lazy loading;
- evidence collection;
- network/model time.

Оптимизация storage выполняется только после доказанного bottleneck.

Нельзя ради latency молча ослаблять:

- ordering;
- crash recovery;
- Windows file-lock behavior;
- records/index consistency;
- backward-compatible чтение RUN;
- существующие durability guarantees.

Эти измерения также записываются в 21, но не блокируют КТ-7, если доказано, что storage не является существенным bottleneck текущей оптимизационной волны.