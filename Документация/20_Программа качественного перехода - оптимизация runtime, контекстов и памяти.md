# Программа качественного перехода: оптимизация runtime, контекстов и памяти

**Статус:** ПРИНЯТО КАК КАНОНИЧЕСКАЯ ПЕРЕХОДНАЯ ПРОГРАММА / РЕАЛИЗАЦИЯ ПОЭТАПНАЯ.

Этот документ временно владеет общей программой качественного перехода после стабилизации TASK 144–151.
Он определяет порядок оптимизации model calls, context composition, Final Audit evidence и будущей historical memory.

Фактическое CURRENT-состояние остаётся в `01_Архитектура и текущее состояние.md`.
Конкретные TASK и статусы остаются в `05_Реестр задач.md`.
История исполнения всей программы ведётся отдельно в [[21_Журнал качественного перехода - решения, метрики и аудит|21_Журнал качественного перехода]].

После завершения программы подтверждённые решения должны быть разнесены по профильным документам.
Документы 20 и 21 удаляются только после отдельного zero-loss reconciliation и финального документационного аудита.

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

### Оптимизационная волна 151A–151J

- **151A — Benchmark + Context Accounting + Usage Accounting.**
  B1/B2/B3, включая B1-clean и B1-dirty. Каждый provider attempt получает identity/outcome; каждый context block измеряется.
- **151B — Evidence Freshness.**
  Привязка evidence к run/plan/stage/requirement/state revision; stale evidence не закрывает новый requirement.
- **151C — Compact Final Audit Packet + Task-scoped Git Evidence.**
  Dredd получает полный по смыслу, но компактный пакет; workspace-wide diff перестаёт быть default payload.
- **151D — Server Direct Exact Evidence.**
  Exact READ/VERIFY из принятого контракта выполняются Server через существующие permission/scope/budget gates без лишнего Executor decision call.
- **151E — Server Factual Final Report.**
  Полностью детерминированная задача получает server-owned factual candidate; semantic final остаётся за моделью там, где нужен смысл.
- **151F — Modular Global Context.**
  CORE + применимые policy modules вместо повторной передачи всего Global Context.
- **151G — Stage Context Compiler.**
  Working set текущей stage вместо бесконечного function/tool transcript.
- **151H — Planner Prompt Optimization.**
  COMMON CORE + INITIAL / READINESS / REPLAN projections.
- **151I — Role Budgets.**
  Наблюдение превращается в bounded enforcement только после доказанной корректной сборки context.
- **151J — Integrated Optimization Regression / Consolidation.**
  Совместный B1/B2/B3, negative matrix, rollback switches, сравнение before/after.

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

## 13. Текущий порядок

```text
150 UI binding audit
151 Integrated stabilization close
  ↓
КТ-0 STABLE BASELINE S1
  ↓
151A Accounting / Benchmark
  ↓
КТ-1
151B Evidence Freshness
  ↓
КТ-2
151C Compact Final Audit + task-scoped Git
  ↓
КТ-3
151D Server Direct Exact Evidence
  ↓
КТ-4
151E Server Factual Final Report
  ↓
КТ-5
151F Modular Global Context
151G Stage Context Compiler
151H Planner Prompt Optimization
151I Role Budgets
151J Integrated Optimization Consolidation
  ↓
КТ-6 / КТ-7
152 Structured Task Digest
153 Rolling Micro History
154 Relevant Prior Facts / Context Compiler V2
  ↓
КТ-8
Final architectural + documentation audit
  ↓
КТ-F
delete transitional docs 20/21
```

Не перескакивать к памяти, пока не закрыта оптимизационная база.
Не объединять несколько зон риска в одну repair TASK без необходимости.
Любое изменение, которое экономит токены за счёт потери доказательств или semantic coverage, отклоняется.

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