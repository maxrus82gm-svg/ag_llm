# Задачи Codex

**Назначение:** персональная карточка локального Codex CLI для задач проекта `ag_llm`. Авторизована пользователем 2026-10-08. Проектный маршрутизатор — [[000_Задачи для агента]]; общий регламент — `18_Регламент сопровождения документации.md`. Codex и Claude не используют общие TASK ID и не пишут отчёт за другую модель.

## Правила

**Единая граница Git (`rule-ref:DOC-GIT-01@1` в 18, пользовательское решение 2026-10-10):** локальный Codex не обращается самостоятельно к Git/GitHub ни для чтения `status/diff/log/show`, ни для записи, через CLI/UI/scripts/API/тест. Если нужна история или сверка committed версии, запросить exact path/range у пользователя либо ChatGPT-координатора в момент работы; если интерактивно нельзя — в отчёте с пометкой BLOCKED по зависимой операции. Исторические отчёты о прошлых Git-проверках сохраняются как события прошлого, а не как разрешение на новые.

- Перед TASK: `08_Старт.md` → `000_Задачи для агента.md` → `18_Регламент сопровождения документации.md` → `01` → профиль темы. Кодекс приступает только к утверждённому БЛОКУ 1; права на мутации определяются scope.
- **Локальный режим.** Codex CLI не использует аварийный handoff ChatGPT через Desktop Commander Remote. Не создавать `Alarm/ALARM_TASK_SESSION/TASK_*`, `session.jsonl`, `context.md`, `history.md`, пооперационный `INTENT/DONE/VERIFIED`, массовые резервные копии tracked-файлов и сырые stdout-логи в репозитории. Использовать локальный контекст, прямую работу с исходниками и временные изолированные пробы **без Git/GitHub по умолчанию** — `rule-ref:DOC-GIT-01@1` из документа 18. Исключение — явно утверждённая пользователем задача с особыми требованиями аудита и защиты.
- **Безопасность.** Не экспериментировать на живом storage; Git не заменяет защиту нерегистрируемых в Git пользовательских данных. Не отключать штатный runtime backup/rollback Web Alarm и не удалять существующую историю автоматически.
- **Минимум артефактов.** В разрешённых рабочих файлах оставлять только целевые правки, необходимые regression tests и действительно существенные evidence; Git-коммиты/публикацию организует пользователь или уполномоченный координатор. Полный task-report отдельным файлом только при необходимости для независимой проверки либо при прямом запросе пользователя. Остальные технические детали — во временном окружении Codex.
- По завершении: один самостоятельный копируемый блок `text` в Chat (TASK ID, статус, изменения, проверки с точными числами, обнаруженные риски, DOC IMPACT, NEXT). Не смешивать итоговый блок с промежуточным ходом работы.
- Внутри scope самостоятельно проверить релевантные edge cases; проблемы вне scope сообщить с evidence и предложением, не менять другие подсистемы без разрешения.
- Не выполнять commit/push и не объявлять `DONE / VERIFIED` без явного разрешения и независимой приёмки.
- После исполнения: сохранить полную утверждённую постановку в БЛОКЕ 2, factual result — в БЛОКЕ 3; только затем очистить БЛОК 1 до ожидания. Канонические журналы обновляются после независимого PASS, не на основании самопроверки Codex.

---

# БЛОК 1 — ТЕКУЩАЯ ЗАДАЧА

**Статус:** WAITING — новой утверждённой задачи нет.
**Последний результат:** CODEX-RT002-S0-001 — RESULT READY / AWAITING INDEPENDENT VERIFICATION, предлагаемый verdict FINDINGS; подробности в БЛОКЕ 3. S1+ не начинать без независимого решения и нового назначения. Старая 151C PARKED / КТ-3 PENDING.

---

# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

**TASK ID:** CODEX-RT002-S0-001 — RT-002/B2 / S0: Fresh Kernel Integration Baseline and Safety Gate.
**Статус:** **USER APPROVED / READY FOR MANUAL START** (2026-10-10), одна задача за раз; исполнитель — **Codex, GPT-6 Sol, Very High** (выбрано пользователем, реальный backend/effort проверять отдельно).
**ARCH CLASS:** Ultra Runtime / Verification / Safe Rebaseline.
**PRIMARY PROFILE:** \`13_Архитектура оперативной верификации и контроля выполнения задач.md\`.
**SECONDARY:** \`20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md\` (§5а), \`21_Журнал качественного перехода - решения, метрики и аудит.md\`; при необходимости \`01\`.
**Утверждённое основание:** итоговый план \`33.3 FINAL-B2\`, immutable commit №242 \`e7365ea773c9adc4e813e05a58810e40b4de4bb4\`, SHA256 \`c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf\`; внешний **USER PLAN APPROVAL** в документе \`28\`, canonical handoff в \`20 §5а\` (commit №244). **Старая 151C PARKED / КТ-3 PENDING**, её НЕ принимать под видом S0.
**Snapshot от координатора до нового назначения:** \`main@cd48ff1629a8e04a734e36196d32ee52e37c103b\`, \`server.py\` blob \`a2e362e552e77b60378b794fe0bec819ec7a0608\`, \`task_planner.py\` \`07f170d07951ee3bd3def22be545bc579dddf6c2\`, \`run_store.py\` \`b5b0e5d6375d8c51b673c0ad14c1d7298fa29c6d\`, \`verifier_runtime.py\` \`4c6b7b08a50cd6698822c7eaba27718c91d9d11e\`; локальные bytes/dirty state могут отличаться и требуют точной, не-Git проверки.

## Зачем нужна S0

Проверь **доказательно**, пригоден ли реально существующий код Ultra для новой защищённой ветки S2/S3→S6a/151G. До изменения архитектуры нужны permission/scope, exact evidence, freshness и recovery гарантии. Результат — один из **BASELINE SUITABLE FOR NAMED NEW SCOPE / FINDINGS / BLOCKED**, с четкими границами доказанного. S0 **не** означает независимую приёмку всей старой 151C и не выдаёт КТ-3 DONE.

## Рабочий маршрут и самостоятельность

1. После пользовательского **GitHub Desktop Fetch/Pull** пройти обычный старт \`08 → общий 000 → 34 → 18 → 01 → персональный 000\`; прочитать \`13\`, \`20 §5а\`, адресно \`21\`, \`33.3 B2\`, \`28\` (USER PLAN APPROVAL) и действующие правила \`DOC-GIT/READ/VERSION/CHANGE @1\` с dependencies. Историческая шапка sealed B2 была DRAFT на момент seal; текущие полномочия **в 28 + 20**, не объявлять план неутверждённым по старой immutable шапке.
2. **Тебе разрешена глубокая инженерная самостоятельность:** сам выбери порядок чтения, AST/source review, изолированные mock/fixtures, offline targeted tests и adversarial edge cases. Перечисленные файлы — **не ограничение на чтение**. При обнаружении в scope существенной неучтённой проблемы зафиксируй факт, риск, severity, repro и возможное безопасное решение, не скрывай его ради быстрого PASS.
3. Основные entry points: \`server.py\` (permissions, accepted args/target, tool dispatch, Final Audit packet, SUCCESS), \`task_planner.py\` (RAW TASK/requirements/contains/equals), \`run_store.py\` (source/generation/attempt identities и restart), \`verifier_runtime.py\`, storage/accounting по необходимости; тесты \`test_final_audit_recovery.py\`, \`test_final_audit.py\`, прочие адресные \`test_*.py\`. Не повторять вслепую дорогие исторические архивы. Ссылаться на реальные source selector/revision, отделяя наблюдение от historical claim.
4. **Никакого локального Git/GitHub**, включая status/diff/log/read .git/API или их запуск через tests/helpers; это \`DOC-GIT-01@1\`. Git evidence/SHA от координатора, локально читать файлы напрямую и при необходимости вычислять локальные SHA-256 без Git. Если для конкретного вывода необходима история, дать \`GIT_DATA_REQUIRED\` с точным запросом и продолжить независимые безопасные пункты.
5. **Никакого платного/live провайдера, сетевых вызовов, R-031 stress, пользовательского production storage и других агентов.** Для тестов применять temp workspace, fake socket/HTTP, подменённые adapters; перед большим suite проверить отсутствие скрытых Git/network/write side effects. Если опасность не исключена — skip соответствующий suite и отметить честное ограничение.

## Минимальные инварианты (не потолок исследования)

- **Authority / source identity:** Server scope, task/run/plan/stage/generation/requirement, разрешённый target и аргументы READ/VERIFY; wrong target, denied scope, wrong predicate, false equality/blocking.
- **Полнота до Dredd:** обязательный source/negative tail, truncated/missing READ, wrong target/old generation не могут удовлетворить requirement; incomplete mandatory packet ⇒ \`0 Dredd sends\`, \`0 SUCCESS\`. Проверка пакета против исторического 151C shape — только новая узкая интеграционная пригодность.
- **Freshness/transition:** replan, repair, mutation и внешние изменения требуют свежего proof; после Audit Packet и перед SUCCESS прежний PASS перепроверяется, hash/same bytes другой identity недостаточно.
- **Reserve/recovery:** существующий mandatory physical-tool reserve, restart/replay без повторной мутации, отсутствие ложной успешности при missing evidence/UNKNOWN/storage problem.
- **Positive + negative:** проверить законно выполнимую простую fixture (чтобы guard не блокировал всё), а также deliberate wrong args/target, stale/negative, truncated, restart/abort, permission-denied, unsupported material и failure diagnostics. Найди дополнительные edge cases самостоятельно.

## Что можно менять в этой одной TASK

**Разрешено:** адресные новые или исправленные **изолированные offline regression tests/fixtures** (например \`test_rt002_s0_kernel.py\` и при необходимости \`test_final_audit_recovery.py\`), и только они, если это повышает доказательность. Локальный Codex вправе глубоко читать релевантный production code и сам решать, какие тесты нужны. **Production runtime/config/transport/UI не менять** в S0 — это отдельные будущие TASK после S0 PASS. При найденном небольшом production дефекте приложить repro и предложить минимальный патч для следующей отдельно разрешаемой работы; не маскировать исходное состояние исправлением до проверки.

**Документы:** локально разрешена только собственная task-card \`000_Задачи Codex.md\` для handoff; общие \`000/05/06/13/20/21/28/33.3/34/01\` не редактировать, их сопровождает ChatGPT после независимой приёмки. **Не удалять и не затирать старые карточки** — DOC-034 и REVIEW-1 сохранены ниже в истории. По завершении безопасно перенести S0 постановку в БЛОК 2 и factual result в БЛОК 3, сохранить архив, затем очистить БЛОК 1 до ожидания. Никаких git commit/push.

## Acceptance / отчёт

В БЛОКЕ 3: \`TASK ID\`, прочитанные source и локальные точные hashes, что совпало с предоставленным baseline, что не доказано; \`PASS/FINDING/BLOCKED\` по каждому инварианту со source path/selector; targeted offline commands + **реальные числа** и network/Git isolation; изменённые test paths, found defects, rollback test changes, DOC IMPACT и строго ограниченный NEXT. Фактическое \`RESULT READY / AWAITING INDEPENDENT VERIFICATION\` **не** \`DONE\`. Не сдавай большой общий обзор вместо воспроизводимых probes.

**Завершение:** независимый ChatGPT verifier по опубликованным изменениям и отчёту отдельно устанавливает \`SUITABLE FOR NAMED SCOPE / FINDINGS / BLOCKED\`. Пока нет этого решения, S1 и другие новые TASK не запускать. **Стартовать только по ручной команде пользователя.**


---

# БЛОК 3 — FACTUAL RESULT / HANDOFF

## CODEX-RT002-S0-001 — factual baseline / 2026-10-10

**Статус исполнения:** RESULT READY / AWAITING INDEPENDENT VERIFICATION. **Предлагаемый verdict:** FINDINGS; пригодность для новой защищённой ветки S2/S3 → S6a/151G пока НЕ доказана. Это локальная самопроверка, не независимый PASS, не DONE и не закрытие 151C/КТ-3. Найдены четыре HIGH-воспроизведения с двумя общими причинами. Production оставлен в исходном состоянии.

**Исполнитель:** локальный Codex. Пользователь запросил GPT-6 Sol / Very High; фактический backend и reasoning effort доступными средствами независимо не подтверждены. Другие агенты не привлекались.

### 1. Основание, источник и границы

Применён маршрут 08 → общий 000 → 34 → 18 → 01 → собственная карточка. Адресно прочитаны 13 (server authority, evidence/freshness, §18 Final Audit и pending recovery), 20 §5а, текущая RT-002 запись 21, внешний USER PLAN APPROVAL в 28, 33.3 FINAL-B2 (§2 T0/S0, §3 DAG и границы последующих этапов). Получены определения `DOC-GIT-01@1`, `DOC-READ-01@1`, `DOC-VERSION-01@1`, `DOC-CHANGE-01@1` из 18 вместе с requires; использовано ручное адресное чтение, не несуществующий автоматический resolver.

33.3: **45043 исходных UTF-8 bytes**, полный SHA-256 **c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf** — точное совпадение с утверждённым B2, без нормализации переводов строк. Immutable commit №242 / `e7365ea773c9adc4e813e05a58810e40b4de4bb4` и разрешение/handoff №244 приняты как сведения координатора; старый DRAFT внутри immutable B2 не отменяет внешнее утверждение.

Четыре runtime-файла локально совпали по SHA-256 с байтами, изученными в предыдущем REVIEW. Это сравнение обычных файлов, **не** доказательство совпадения Git blob. Координаторский `main@cd48ff1629a8e04a734e36196d32ee52e37c103b` и предоставленные blob IDs сохранены в полной постановке БЛОКА 2; локальные Git state/HEAD/dirty status не исследовались.

**GIT_DATA_REQUIRED, только для committed↔local сверки:** координатору предоставить полные обычные file-byte SHA-256 либо экспортированные bytes `server.py`, `task_planner.py`, `run_store.py`, `verifier_runtime.py` из указанного snapshot с точным revision. Текущие probes от этого не зависели; утверждение «проверена именно committed версия» остаётся недоказанным. Git-object hashes не вычислялись обходным способом.

### 2. Что изменено и как воспроизвести

Создан только `M:/GitHub/ag_llm/test_rt002_s0_kernel.py` (27453 bytes, SHA-256 **845134a0ee3493e31213107c52bba7437c2364505d3036bda4556b5e3a9c5341**). Это отдельный guarded runner, 16 новых тестовых методов и явный manifest 81 существующей проверки; существующие тесты не изменены. Документационное изменение — только эта карточка: полная S0 постановка перенесена в БЛОК 2, прежние REVIEW-1 БЛОКИ 2/3 сохранены ниже, старые архивы оставлены.

Из `M:/GitHub/ag_llm`:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py
```

**Финальный запуск: 97 tests = 93 PASS + 4 FAIL; 0 ERROR, 0 SKIP, exit 1.** Красные проверки намеренно показывают дефекты baseline; не помечены expectedFailure и не замаскированы общим PASS.

| Группа | Число |
|---|---:|
| Новые KernelBoundaryTests / IdentityBoundaryTests | 14 / 2 |
| StageEvidenceContractTests | 10 |
| FinalAuditByteBudgetTests / RecoveryIntegrationTests | 2 / 16 |
| PersistenceStateTests / PlannerIntegrationTests | 11 / 20 |
| VerifierRuntimeTests, адресный protocol subset | 10 |
| Run Store v2 / provider accounting, прямой вызов pure fixtures | 9 / 3 |
| Всего | 97 |

Повтор четырёх дефектов на том же финальном test-файле:

```powershell
.venv/Scripts/python.exe -B test_rt002_s0_kernel.py test_read_change_before_fingerprint_cannot_certify_old_content test_verify_change_before_fingerprint_cannot_certify_old_predicate test_missing_recorder_cannot_return_certified_success test_lost_tool_outcome_cannot_return_certified_success
```

**4 tests, 4 FAIL, 0 ERROR/SKIP, exit 1.** Все четыре вновь дошли до одного mock Dredd вызова и одного SUCCESS. Изоляция обоих запусков: **0 guard violations**, реальных provider/Git/network вызовов нет.

Проверка обычного unittest discovery:

```powershell
.venv/Scripts/python.exe -B -m unittest test_rt002_s0_kernel -v
```

**0 tests, 1 module SKIP, exit 0** — ожидаемо: без standalone-изоляции модуль не импортирует runtime и не устанавливает глобальные hooks в чужой suite. Это проверка безопасного включения файла, не дополнительный runtime PASS. Промежуточные запуски с доработкой fixtures не включены в 97; ошибки настройки denied scope, ожидаемого LOOP DETECTED и Windows newline устранены до финального результата.

### 3. Изоляция и предел доказательности

Guard устанавливается **до** imports server/legacy fixtures: audit hook блокирует subprocess/os.system/spawn, Python socket connect/bind/DNS, чтение .git, чтение production .ultra и файловые мутации вне уникального temp root. Единственное разрешённое socket housekeeping — синхронный stdlib socketpair для Windows asyncio. LOCALAPPDATA/APPDATA/TEMP/TMP направлены в sandbox; -B запрещает pycache writes.

Executor HTTP, token acquisition, Planner и Dredd заменены fake/AsyncMock adapters; server Git helpers заменены фиктивными обычными словарями. Без этих mocks исходный runtime умеет обращаться к Git: наличие проверки S0 не меняет его архитектуру и не даёт такого права локальному агенту. Из manifest исключены весь FinalAuditGitScopeTests и методы recovery `test_ignored_file_material_remains_available_without_git_diff` / `test_git_diff_state_drift_requires_new_source_evidence`; они не исполнялись. Полный неотобранный legacy suite не запускался. Pytest-style функции вызваны напрямую с temp fixtures и MonkeyPatch, без plugin discovery.

Это process-local Python guard плюс проверка выбранных путей, **не OS sandbox** и не сертификация произвольных сторонних расширений. Stress, GUI, реальные provider/transport и Git semantics не проверены. Mock PASS намеренно используется для проверки механических server gates: выводы не зависят от добросовестности LLM.

### 4. Инварианты: результат с точными selectors

В таблице имена test_* относятся к manifest runner; полный список каждого вызова сохраняется в result.json и воспроизводится из _manifest().

| Инвариант | Verdict | Доказательство / предел |
|---|---|---|
| Server permissions, READ/VERIFY scope, traversal, WRITE denial/grant | PASS в проверенных случаях | Новые test_read_and_verify_denied_scopes_and_traversal, test_denied_read_never_satisfies_requirement_or_calls_dredd; PlannerIntegration test_scope_violation_does_not_reach_audit_or_force, test_write_off_uses_existing_permission_escalation, test_explicit_permission_grant_allows_same_contract_to_continue. Denied READ заканчивается LOOP DETECTED после трёх ошибок, не SUCCESS; диагностируется PermissionError. |
| task/run/plan/stage/generation/requirement/source + exact arguments | PASS в проверенных случаях | test_identity_dimensions_and_same_hash_other_target_are_rejected: 9 подмен identity/status/executed и другой target при одинаковом content hash; StageEvidenceContract old_plan_version, execution_repair_generation, missing_source_record_identity; PlannerIntegration wrong_successful_verify и server_evidence_gate. Аргументы связываются arguments_sha256; модельный текст не становится authoritative fact. |
| equals ≠ contains; false equality | PASS без гонки; FINDING при гонке | test_exact_equality_is_not_contains_and_false_block_is_explicit; test_required_false_equals_blocks_without_dredd: 0 audit, 0 SUCCESS, VerificationError/LOOP DETECTED. Положительный точный equals и READ проходят; F02 показывает отдельную потерю свежести. |
| Полнота обязательного material до Dredd | PASS для missing/truncated/budget cases; FINDING по durability | Recovery test_missing_required_material_blocks_before_dredd, required_material_budget_exhaustion, deduplicated_required_large_read, tool_level_truncated_find_text, truncated_model_result; PlannerIntegration incomplete_requirement_coverage. В этих случаях 0 mock audit, 0 SUCCESS. Но F03/F04: отсутствующий durable source не признаётся incomplete. |
| Negative tail / failed exact outcome / dedup | PASS в проверенных случаях | Recovery failed_exact_check_keeps_details_and_its_outcome_record, failed_exact_metadata_survives_zero_material_budget, empty_search_negative_fact_survives_no_preview_budget, complete_deduplicated_material_keeps_an_explicit_source. count=0 и expected/actual остаются явными; старый truncated generation не блокирует новый fresh proof. |
| replan/repair/mutation/dependency drift | PASS для проверенных transitions | StageEvidenceContract old_plan_version, execution_repair_generation, target_state_drift, dependency_drift_in_compile_paths; PersistenceState stale_candidate, server_binding_other_plan_version, satisfied_receipt_invalidated_by_external_change и replan_cannot_silently_drop_obligation. |
| freshness после packet, после Dredd и перед terminal SUCCESS | PASS в проверенных поздних окнах; FINDING в исходном observation binding | PlannerIntegration state_change_during_packet_collection и state_change_during_final_audit; Recovery directory_listing_drift_after_pass; новый test_mutation_after_audit_pass_before_terminal_gate_requires_new_read: изменение в callback final_audit_passed вызывает terminal_evidence_freshness_blocked, fresh READ и второй audit, только затем SUCCESS. F01/F02 подменяют исходный binding раньше этих gates, поэтому поздние сравнения его не исправляют. |
| Mandatory physical-tool reserve | PASS в проверенных случаях | PlannerIntegration test_tool_reserve_preserves_mandatory_write_read_verify_calls: лимит 3, ровно WRITE/READ/VERIFY; лишние calls остановлены до выполнения. test_tool_reserve_blocks_impossible_plan_before_executor_api: лимит 2, 0 executor API, 0 audit. Это существующий reserve, не будущий S3 resource ledger. |
| abort/restart/replay, UNKNOWN | PASS узко; полного crash recovery proof нет | Новый test_abort_after_write_records_no_success_and_does_not_auto_replay: физический WRITE=1, cancellation до receipt, 0 audit/SUCCESS; новый controller не загружает и не переигрывает старый latch. Existing successful_persistence_advances_before_executor_can_repeat_write не допускает повторного WRITE. Unknown usage остаётся incomplete; duplicate terminal не удваивает usage. Это не доказательство exactly-once при power loss и не реализованный resume interrupted RUN. |
| Storage failures | FINDING | Плановый atomic_state failure прекращает RUN до executor/audit; last-state preservation, retry/fallback generation проверены. Однако F03/F04 допускают SUCCESS без обязательного durable outcome. |
| Unsupported material / diagnostics / protocol | PASS в проверенных случаях | test_missing_oversized_unsupported_and_invalid_predicate_fail_closed: missing file, binary suffix, file limit, bad kind/hash/exists args. Dispatcher failure оставляет tool_started → tool_error. Verifier malformed/unknown/mismatched verdict/check_type и unsupported provider/model не превращаются в PASS и не fallback. Реальный транспорт не тестировался. |

### 5. Findings: воспроизведение, причина и безопасное предложение

#### S0-F01 — HIGH: READ material и observed_state относятся к разным состояниям файла

**Repro:** `KernelBoundaryTests.test_read_change_before_fingerprint_cannot_certify_old_content`. Только temp target: READ возвращает `OLD MATERIAL`; wrapper сразу после реального READ заменяет файл на `NEW MATERIAL`, до возврата управления server evidence binding. Не подменяются result, contract, hashes, lifecycle или решение Server. Это детерминированное воспроизведение внешнего изменения в реальном промежутке между чтением и повторным snapshot.

**Факт:** packet содержит `OLD MATERIAL`, а `observed_state_sha256` совпадает с fingerprint уже `NEW MATERIAL`. completeness.complete=true / critical_for_success=false; mock Dredd=1, terminal SUCCESS=1. Следующие freshness checks сравнивают текущий файл с ошибочно новым binding и не видят старость READ.

**Источник:** server.py `_agent_read_file`, `_planner_dependency_fingerprint`, `_run_agent_task_impl` — формирование observed_state_sha256 и consistency_tool_facts после dispatcher; task_planner.py `evidence_dependency_state_fingerprint` / `_matched_evidence_requirement_ids_for_stage`. Значимость: сервер заявляет свежий обязательный READ, который фактически не видел текущего содержимого.

**Минимальный будущий patch, НЕ применён:** строить observation fingerprint из того же наблюдения/байтов, что породили tool result (для READ — content_sha256 и canonical target/exists). Отдельный текущий snapshot использовать только для сравнения, не для присвоения старому result нового observed_state. При несовпадении reopen generation / запрос fresh proof или явный BLOCKED; проверить read_file_range/find_text/list_dir тем же принципом. Простой дополнительный post-read snapshot сам по себе проблему не решает, если им снова маркируется старый material.

#### S0-F02 — HIGH: старый положительный equals сертифицирует уже неверный target

**Repro:** `KernelBoundaryTests.test_verify_change_before_fingerprint_cannot_certify_old_predicate`. Файл физически записан как `done\n` с newline="", real verify(kind=equals,value="done\n") возвращает true; до binding wrapper меняет target на `WRONG`. Положительный control `test_positive_exact_verify_control_for_fingerprint_race` с теми же исходными bytes/args без изменения проходит.

**Факт:** packet verification.passed=true и actual_sha256=`SHA256("done\n")`, но observed_state относится к `WRONG`; mock Dredd=1, SUCCESS=1. Это не смешение contains/equals и не Windows newline artifact. Причина общая с F01, но проверяется более сильный детерминированный predicate.

**Источник:** server.py `_agent_verify_file_content`, post-dispatch observed_state binding; task_planner.py matcher и freshness. **Будущий patch:** bind VERIFY к actual observation, включая exists/actual_sha256 и args fingerprint; при current state mismatch обязательный свежий VERIFY. Для exists/absent отдельно зафиксировать наблюдаемую existence; для directory/multi-path dependencies не притворяться, что file-only fingerprint универсален. F01/F02 — одна обязательная область исправления и два независимых repro, а не два разных архитектурных механизма.

#### S0-F03 — HIGH: недоступный Run Store не блокирует защищённый SUCCESS

**Repro:** `KernelBoundaryTests.test_missing_recorder_cannot_return_certified_success`: constructor `AuditThreadRecorder` выдаёт OSError, имитируя недоступное хранилище. READ и lifecycle работают в temp; result существует только в оперативном контуре.

**Факт:** audit_storage_error наблюдаем, `source_run_store_record_id=null`, но сгенерированный RAM `source_record_id=evidence_...` достаточен для complete=true / critical_for_success=false; mock Dredd=1, SUCCESS=1.

**Источник:** server.py `_run_agent_task_impl`, init AuditThreadRecorder (комментарий “Audit observability is not allowed to veto the Executor RUN”), `_emit`; `_final_audit_requirement_coverage` / packet completeness. Это действующий best-effort design, а не утверждение о случайной новой регрессии. Он не обеспечивает требуемую S0 гарантию сохранённого обязательного proof/recovery.

**Будущий patch:** разделить необязательную observability и обязательное evidence storage. Для protected requirement нужен успешно сохранённый и адресуемый outcome с RUN/plan/stage/generation/args/target identity; иначе critical_for_success до Dredd и запрет certified SUCCESS. Не превращать любой сбой cosmetic trace/UI logging в общий veto. UI/config в S0 не трогались.

#### S0-F04 — HIGH: потеря durable tool_finished оставляет ложную полноту packet

**Repro:** `KernelBoundaryTests.test_lost_tool_outcome_cannot_return_certified_success`: recorder создаётся, tool_started и другие события записываются; только `observe(tool_finished)` выдаёт OSError.

**Факт:** outcome pointer становится null; fault виден в событии, но completeness снова complete=true / critical_for_success=false; mock Dredd=1, SUCCESS=1. Сохранённый tool_started и RAM material не заменяют запись результата инструмента. Отдельная обычная положительная READ fixture проверяет, что непотерянный source действительно разрешается через load_run_record.

**Источник:** server.py `_emit`, обработка tool_result_record после tool_finished и присваивание source_run_store_record_id; task_planner.py matcher требует только непустой logical source_record_id; packet requirement coverage не проверяет durable outcome availability.

**Будущий patch:** сохранять обязательный outcome до удовлетворения requirement; проверять существование/целостность и точную identity адресуемой записи, а не только непустую строку-ID. Отклонять отсутствующий/недоступный/повреждённый outcome. Явно обрабатывать partial append/index failure и cancellation между mutation и receipt без автоматического retry mutation. F03/F04 — две точки отказа одной обязательной области storage.

**Рекомендация для независимой приёмки:** признать FINDINGS и не выдавать SUITABLE FOR NAMED NEW SCOPE до адресного исправления двух причин и повторной S0-проверки. Наличие 93 зелёных проверок не компенсирует четыре нарушения обязательных guarantees. Выпуск исправлений требует новой отдельно разрешённой TASK; её создание/старт здесь не выполнялись.

### 6. Доступные evidence / reproducibility

Финальный sandbox: `C:/Users/REX/AppData/Local/Temp/codex-rt002-s0-y3mo_q14/`.
- `result.json`: manifest всех 97 cases, фактические counts, isolation violations, events и packets четырёх repro; SHA-256 **72b278ab3cd4a42b735d180c33794179880d40482cb3dd1f52828b0aa0e0b848**.
- `unittest.log`: SHA-256 **9d28dcc90474fc683ff666263e76c1126f1aa78a79a0ce3c6eecb331d237d209**.
- Время runner 27.949 s. Случайные RUN/record IDs и время при повторе закономерно меняются; критерии counts/identity/гейтов остаются теми же.

Повтор: `C:/Users/REX/AppData/Local/Temp/codex-rt002-s0-ltmtrjzz/`.
- `result.json`: SHA-256 **95de5c259e67afccf2ce73c93575b17f39023e2938d6759a344853fb72d8cafd**.
- `unittest.log`: SHA-256 **0ff71ec5a138b610cca0882d4fbaebcf166f8d9bcba2e4811831c6b417e43153**.
- Время runner 2.612 s.

Доступность обоих JSON/log и соответствие log hashes проверены. Это временные локальные evidence, **не immutable archive и не SUBMITTED seal**. Внутренние temp workspaces отдельных fixtures очищаются; воспроизводимый test source и достаточные факты сохранены в разрешённых рабочих файлах. До внешней публикации/печати статус остаётся RESULT READY; номер коммита не придуман. Hash этой карточки публикуется отдельно от её собственных bytes.

### 7. Локальные source revisions (полные file-byte SHA-256)

Пути ниже относятся к `M:/GitHub/ag_llm/`; это точные байты локальных файлов, не Git blobs. Исходный snapshot карточки до ротации: **8ceb169dcafa555dcb67e278d939ae545e032ddbc6bdd70b5c7cae1113b5f4d7**. Финальная проверка охватывает 166 исходных файлов корня и документации: изменена только собственная карточка, остальные **165 byte-identical**; дополнительно создан один разрешённый test-файл. Production/config/transport/UI и существующие tests не изменены.

| Runtime / fixture source | SHA-256 |
|---|---|
| `audit_storage.py` | `15466977e17d2f48e377ccd9b77d7ecc01aaec82c2aabf4501f8cd3c11595905` |
| `planner_runtime.py` | `ab6c12c3fb02145e9acae692360099922048366a7668a977c350cf98af49384e` |
| `provider_accounting.py` | `dd83dbf7a22154347ac6f17ca2110e78757338248bd466f86a0d3599db510902` |
| `run_store.py` | `91f82db61a75980ebae8a0ee4e707ac2c09e33628021991d70d639b97b2eef44` |
| `server.py` | `404d43d6a39924a3a0d725650f0cf4ba67591bca13e071794ab4d576f378090a` |
| `task_planner.py` | `c2ad7723b0ec51769e7fef8de87d97aa5e85cf50cbded2fc5f3082ec2b078346` |
| `test_final_audit_recovery.py` | `8dc022756d5a3b4abb46c86d68f4ea0c9771b4ccba264253843b47b7ade32442` |
| `test_final_audit.py` | `1e7f883ab9579d9775e6f1603dea46dba37f6f95a8eccf5c1ef39846dd383c57` |
| `test_provider_accounting.py` | `5c16cc5ab0d55a9ca88720e4c1b42031f4c3cb5657501045403d235fddb00738` |
| `test_run_store_v2.py` | `28334ef3a59d8ed375eaca7e91e97048cd07f1fdd53526672391546e8fe4b4a2` |
| `test_stage_evidence_contract.py` | `3467538143c6b7bbab031211a9a6f8d18882899f3a60d877dcd4f91f6eaf12c9` |
| `test_task_planner.py` | `49ba81617fb85da8656e67db3613a7b641479ad3f177238ad736df6ae019cfa9` |
| `test_verifier_runtime.py` | `905b6b4cf5553b4f0cfd29edcf3157daa9faa4c78d96416323772880a520cd1a` |
| `verifier_runtime.py` | `7db030fee149d8f8af1a90d384f3ad23e5086cea5d5ce42e6c728fd096764228` |

| Нормативный source (Документация/) | SHA-256 |
|---|---|
| `000_Задачи для агента.md` | `159584416c3edc8d285143bf4e1349d51a8535753922608f1963a9782de30a12` |
| `01_Архитектура и текущее состояние.md` | `0d292f590dfce4f9a72abebb7067c2bbd8eaa1ead3d662ac227d586c4b6bc5da` |
| `08_Старт.md` | `143cd3fb5b7d22d8288726753bfaf248f4d8a5dcd7f2a4e96dd02ba629ce16b0` |
| `13_Архитектура оперативной верификации и контроля выполнения задач.md` | `994cd41a3ca460753b665c901667548f46462ebf2b2e7167341e7d9bae88f742` |
| `18_Регламент сопровождения документации.md` | `88fab7b4a23f1dda95ee1fc2c83417fc261333ffdcac1dfb6d8d21d3444c94aa` |
| `20_Программа качественного перехода - оптимизация runtime, контекстов и памяти.md` | `22c7786c41ce7000c640ac82f523270cc98f1e4287277fa1b02b4f15ffee048a` |
| `21_Журнал качественного перехода - решения, метрики и аудит.md` | `0c1b020bbe0661420b618e1afcd945479028dc58b5e87de57fd009c352b50793` |
| `28_Круглый стол - протокол и текущий вопрос.md` | `1cbb8d05596085955a22575e0c46cb3a3ee05f5bc4ef74515ea593feec8fe9d1` |
| `33.3_Круглый стол - итоговый план.md` | `c331ffadff32231de04e5e29ccec351828678b31407bad6f75362a21d9cecfdf` |
| `34_TACTICAL_CONTEXT.md` | `a487b36fb181d0328ce772b7f681f5f963c9af881ea327638bef858a5c295e11` |

### 8. Closeout / DOC IMPACT / NEXT

**Rollback test changes:** удалить только созданный `test_rt002_s0_kernel.py`, если пользователь отклонит этот набор; runtime откатывать нечего. Возврат карточки возможен из сохранённой постановки БЛОКА 2 и архива REVIEW-1, без уничтожения factual result/истории; никаких reset/checkout. Временные sandbox logs можно удалить после независимой приёмки/сохранения нужных evidence, только по точным путям. Очистка сейчас не выполнялась.

**Documentation Change Impact:** нормативные Rule-ID/contract не изменены. Обязательные БЛОКИ 1/2/3 сохранены; S0 assignment скопирован полностью, REVIEW-1 БЛОКИ 2/3 сохранены отдельным архивом, прежние 151C/DOC-034 архивы — byte-exact. Текст до БЛОКА 1 сохранён byte-exact. Новых wiki/Markdown graph edges не добавлено, прежние ссылки не переименованы; механическая проверка структуры/сохранения выполнена. Это не визуальный Obsidian Graph PASS и не принятие старой DOC-034.

**SHARED DOC DELTA — передать ChatGPT после независимого рассмотрения:**
- 20 §5а / 21: зафиксировать локальный S0 result FINDINGS, 97=93+4 и четыре repro/two root causes; независимый verdict и возможные исправления записывать отдельно. Не выдавать старт S0 за его приёмку.
- общий 000 / 34: отразить ожидание независимой проверки/решения, не объявлять S1 или зависимые этапы разблокированными.
- 13: при подтверждении findings уточнить предел текущего observation binding / durable source guarantees; исправленный runtime описывать только после отдельной реализации и проверки.
- 28 / 33.3: утверждение B2 и immutable bytes не менять; результаты S0 не являются новой редакцией плана или принятием 151C. S13a ACCEPTED before S6b остаётся условием канонического маршрута.

Общие документы вне write-scope не правились. **DOC CLOSEOUT INCOMPLETE для общего контура:** ждёт решения и записей уполномоченного координатора; персональный factual handoff подготовлен.

**Строго ограниченный NEXT:** пользователь публикует локальные изменения; ChatGPT независимо проверяет source hashes, isolation/manifest, воспроизводит четыре failures и устанавливает S0 verdict. При подтверждении — согласовать отдельную TASK исправления двух причин и повтор S0. **Никакой S1+ здесь не начат; 151C PARKED / КТ-3 PENDING сохранены.**


---

## ARCHIVED REVIEW-1 — прежние БЛОКИ 2/3 (сохранено при S0, 2026-10-10)

Ниже прежний closeout сохранён дословно; fenced snapshot не является новым назначением.

````text
# БЛОК 2 — ПОСЛЕДНЯЯ ВЫПОЛНЕННАЯ ЗАДАЧА — ПОСТАНОВКА

**TASK:** CODEX-RT-002-PLAN-REVIEW-001 (историческая, сдана и внешне запечатана). Полная утверждённая постановка и closeout неизменно восстанавливаются из GitHub `main@cd48ff1629a8e04a734e36196d32ee52e37c103b` в старом БЛОКЕ 1; оригинальный документ результата — `33.1` immutable commit №238. Характер: REVIEW / NOT BLIND первоначального 33 по V1…V13 с 15 findings, DAG и A1…A8, без кода. **Планирование завершено, не исполнять повторно.**

---

# БЛОК 3 — FACTUAL RESULT / HANDOFF

**TASK:** CODEX-RT-002-PLAN-REVIEW-001
**Статус:** SUBMITTED / EXTERNALLY SEALED (документальный REVIEW, не runtime DONE). **Result:** `33.1` Codex REVIEW-1, commit №238 `c6b910bde7280ace7250d032ba495554b6c41356`, 15 findings: 9 HIGH / 5 MEDIUM / 1 LOW; seal `28/SEAL-CODEX-REVIEW-1`. Итог B2 создан/утверждён человеком, но Codex-probes не являются независимым runtime PASS.
**Открыто:** CODEX-ULTRA-151C-RECOVERY-001 PARKED/KT-3 PENDING; CODEX-DOC-034-GRAPH-001 результат archived below, всё ещё требует отдельной независимой/визуальной проверки.
**NEXT:** только новая USER ASSIGNED `CODEX-RT002-S0-001` в БЛОКЕ 1.

---


````

## Архив приоритета 151C — решение пользователя 2026-10-10

`CODEX-ULTRA-151C-RECOVERY-001` снята из активного БЛОКА 1 **без признания DONE**. Первоначальная полная постановка и factual recovery-report сохранились неизменёнными в GitHub `main@27ddda0162959f23fabf92ea80a9a58006af93fc`, файл `Документация/000_Задачи Codex.md`, старый БЛОК 1. Результат 151C — `RESULT READY / AWAITING INDEPENDENT VERIFICATION` / КТ-3 `PENDING`; пользователь отложил эту отдельную приёмку и поручил сначала пересмотреть весь план RT-002. Это не означает принятия 151C и не отменяет требований доказательности для будущих TASK.

БЛОКИ 2–3 по `CODEX-DOC-034-GRAPH-001` — **исторический незакрытый RESULT READY**, сохранены без изменений. Следующая ротация только после безопасной координации, не перетирать историю автоматически.

## ARCHIVED DOC-034 — прежний БЛОК 2

**ИСТОРИЧЕСКАЯ КОПИЯ — НЕ CURRENT БЛОК**, original GitHub cd48ff1629a8e04a734e36196d32ee52e37c103b. История не является выполненной независимой приёмкой.

~~~~text
**TASK:** CODEX-DOC-034-GRAPH-001
**Статус:** APPROVED FOR EXECUTION (утверждённая постановка).
**ARCH CLASS:** Documentation / Obsidian Graph; архитектура и runtime не меняются.
**PRIMARY PROFILE:** 18_Регламент сопровождения документации.md.
**CHECK 01:** выполнен; архитектурного влияния нет.
**REGISTRY IMPACT:** NO — сохранить существующую связь 05 → 34.
**CONTEXT LIBRARY IMPACT:** NO — библиотека 14–16 и модельный prompt не затрагиваются.
**DOC IMPACT:** 00, 08, 34 и персональная карточка Codex; правила сопровождения 18 сохраняются.
**Baseline:** HEAD 3b5ab323446c16cacadf9ce2c796af8b8d75c85a; исходные пользовательские изменения .obsidian/graph.json и .obsidian/workspace.json сохраняются.

TASK: CODEX-DOC-034-GRAPH-001 — Исправление связей Tactical Context в Obsidian
Исполнитель: Codex
Проект: ag_llm
Тип: Documentation / Obsidian Graph
Статус: APPROVED FOR EXECUTION
Основание: прямое поручение пользователя в текущем чате.
1. Цель
Исправить связи документа 34_TACTICAL_CONTEXT.md в графе Obsidian.
Требуемая схема:
00_Главная - карта проекта
          │
          ▼
05_Реестр задач
          │
          ▼
34_TACTICAL_CONTEXT

Документ 34_TACTICAL_CONTEXT.md должен иметь ровно одну связь — с 05_Реестр задач.md.
Никаких других связей у документа 34 быть не должно.
2. Что необходимо сделать
1. Открыть репозиторий ag_llm и ознакомиться с Документация/08_Старт.md, глобальным 000_Задачи для агента.md, 34_TACTICAL_CONTEXT.md и правилами документации.
2. Найти все входящие и исходящие связи документа 34_TACTICAL_CONTEXT.md во всём Obsidian Vault.
3. Удалить лишние Wiki Links и Markdown-ссылки, создающие рёбра графа между документом 34 и другими документами.
4. Сохранить связь 05_Реестр задач.md → 34_TACTICAL_CONTEXT.md.
5. Убедиться, что 00_Главная - карта проекта.md связан с 05_Реестр задач.md.
6. Удалить прямую связь 00_Главная - карта проекта.md → 34_TACTICAL_CONTEXT.md, если она существует.
7. Проверить YAML frontmatter документа 34. Если теги continuity, tactical-context или другие метаданные создают дополнительные узлы и связи в графе, убрать соответствующие теги.
8. Убедиться, что другие документы не создают обратных ссылок на 34.
Важно: обычные текстовые упоминания документа 34 удалять не требуется. Если ссылка нужна для инструкции или маршрута чтения, заменить её на обычное текстовое название файла без создания ребра Obsidian Graph.
3. Обязательные ограничения
- Не удалять сам документ 34_TACTICAL_CONTEXT.md.
- Не удалять его оперативный контекст, сведения о задачах, статусах и правилах обновления.
- Не нарушать регламент постоянного сопровождения Tactical Context.
- Не изменять связи между другими документами, кроме необходимого восстановления цепочки 00 → 05 → 34.
- Не менять программный код, runtime и тесты проекта.
- Не сбрасывать настройки Obsidian Graph для маскировки лишних связей. Исправить именно источники этих связей.
- Не выполнять commit/push — это сделает пользователь.
4. Критерии приёмки
После выполнения в Obsidian Graph:
Должно быть:
00_Главная - карта проекта ↔ 05_Реестр задач ↔ 34_TACTICAL_CONTEXT
Не должно быть:
Прямых связей документа 34 с 000_Задачи для агента, 01_Архитектура, 06_Журнал, 08_Старт, 18_Регламент, 23, 24, 25 или любыми другими документами.
Также не должно оставаться связей документа 34 с узлами тегов.
Итог: у узла 34_TACTICAL_CONTEXT должна быть ровно одна связь — с 05_Реестр задач.
5. Порядок выполнения и отчёт
Codex, прочитай эту задачу непосредственно из текущего чата и приступай к исполнению. Дополнительного подтверждения в рамках указанного scope не требуется.
Соблюдай установленный документационный workflow проекта, включая персональную карточку 000_Задачи Codex.md.
После изменений:
1. Проверь ссылки и обратные ссылки по всему Vault.
2. Проверь отсутствие нежелательных связей через YAML-теги.
3. Убедись, что содержание Tactical Context не потеряно.
4. Проверь git diff --check.
5. Подготовь отчёт: какие файлы изменены, какие связи удалены, какие сохранены.
6. Если доступна проверка непосредственно в Obsidian Graph, выполни её. Иначе явно укажи, что проверена структура Markdown, но не визуальное отображение.
Результат передать на независимую проверку ChatGPT.
Код проекта не затрагивать. Не выполнять никаких дополнительных улучшений вне этой задачи.
Codex: задача утверждена пользователем. Прочитай постановку выше, выполни её самостоятельно и предоставь результат для проверки.

---
~~~~


## ARCHIVED DOC-034 — прежний БЛОК 3

**ИСТОРИЧЕСКАЯ КОПИЯ — НЕ CURRENT БЛОК**, original GitHub cd48ff1629a8e04a734e36196d32ee52e37c103b. История не является выполненной независимой приёмкой.

~~~~text
**TASK:** CODEX-DOC-034-GRAPH-001
**Статус:** RESULT READY / AWAITING INDEPENDENT VERIFICATION.
**Дата:** 2026-10-09.
**Baseline:** main, HEAD 3b5ab323446c16cacadf9ce2c796af8b8d75c85a; commit/push не выполнялись.

**Результат:** по структуре Markdown цепочка 00 ↔ 05 ↔ 34 сохранена, у узла 34 ровно один уникальный сосед — 05_Реестр задач.md. Сохранены исходная ссылка 05 → 34 и обе существовавшие ссылки 34 → 05; три вхождения ссылок образуют одно ребро, а не три разных соседа.

**Изменены только четыре Markdown-файла:**

- Документация/00_Главная - карта проекта.md — ссылка на 34 заменена текстовым именем файла; существующие ссылки на 05 сохранены.
- Документация/08_Старт.md — ссылка на 34 заменена текстовым именем файла; обязательный маршрут чтения и closeout сохранены.
- Документация/34_TACTICAL_CONTEXT.md — 11 исходящих ссылок на другие документы заменены текстовыми именами файлов, удалены YAML-теги project/continuity и project/tactical-context; aliases сохранены. Выполнен обязательный delta-handoff: текущая документальная TASK, сверка Git, NEXT и последний handoff; оперативные задачи, статусы, открытые вопросы и правила сопровождения сохранены.
- Документация/000_Задачи Codex.md — полная утверждённая постановка сохранена в БЛОКЕ 2, factual result в БЛОКЕ 3; БЛОК 1 возвращён в ожидание после проверки сохранённых блоков.

**Удалены:** 13 вхождений Wiki Links, образовавших 9 лишних рёбер между 34 и документами 00, 000, 01, 06, 08, 18, 23, 24, 25. Новых рёбер нет. Markdown-ссылок на 34, требующих удаления, не обнаружено. Теги 34 удалены из источника, настройки графа не менялись.

**Проверки:** весь Vault, включая скрытые/ignored каталоги, кроме служебной .git: 301 Markdown-файл, 0 Canvas, 0 символических ссылок; обработаны Wiki Links, Markdown/HTML-ссылки, reference links, пути/расширения/URL encoding и aliases. После изменений остался только источник входящей ссылки 05; исходящие ссылки 34 ведут только в 05. YAML/inline tags у 34 отсутствуют. Полный набор остальных рёбер совпадает с исходным. Loss check: после исключения разрешённых замен ссылок/тегов и трёх closeout-дельт с одной актуальной Git-сверкой весь остальной текст 34 совпадает с исходным. Все семь разделов, карта чтения и регламент DELTA сохранены. Реестр 05 и регламент 18 побайтово не менялись. SHA-256 остальных 1 207 tracked-файлов совпали со снимком на входе. git diff --check — PASS.

**Границы и риски:** структура Markdown проверена, визуальное отображение Obsidian Graph не проверено: доступного управления Obsidian/CLI в текущем окружении нет. Независимый PASS ещё не получен. На входе уже были изменены .obsidian/graph.json и .obsidian/workspace.json; их текущие байты сохранены. Код, runtime, тесты, Alarm, глобальная карточка и канонические журналы не изменялись; новые файлы не создавались. Git HEAD/index не менялись.

**DOC IMPACT:** 00, 08, 34, персональная карточка Codex. REGISTRY IMPACT: NO — существующая связь 05 сохранена без изменения реестра. CONTEXT LIBRARY IMPACT: NO — библиотека 14–16 и runtime prompt не затронуты.

**NEXT:** независимая проверка ChatGPT по этой постановке и diff, затем визуально подтвердить в Obsidian Graph единственного соседа 34 — реестр 05; commit/push выполняет пользователь. Статус не повышать до DONE / VERIFIED до принятого независимого PASS.
~~~~

