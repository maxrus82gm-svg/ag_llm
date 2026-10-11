# CODEX-WA4-R-001 — Strict Rollout Preflight / OBSERVE

STATUS: RESULT READY / AWAITING INDEPENDENT VERIFICATION

Executor: Codex; работа 2026-10-11, завершение ротации 2026-10-12 (Asia/Yekaterinburg). Independent acceptance remains ChatGPT.

## Решение и scope

Реализована ограниченная on-demand read-only диагностика OBSERVE, а не глобальный режим контроля файлов. GET /tasks/{task_id}/observe и CLI observe --task-id читают существующие server-owned stores, RC-5 projection и snapshot/current-state evidence текущей микрозадачи. Они не подключаются к execution path, не пишут диагностический store, не меняют admission, status, recovery, claims, receipt или NEXT. WARN / GATEWAY REQUIRED / STRICT не включены. Полноценное наблюдение всех внешних операций текущим API невозможно.

## Preflight: authority и физические пути записи

| Путь / вызывающий | Что реально контролирует Web Alarm | Наблюдаемость и обходы | Что потребуется позднее |
| --- | --- | --- | --- |
| HTTP POST /tasks/{id}/mutations; клиент/Remote/оператор | WA4-E executor: durable contract/payload, VERIFIED manifest+snapshot, RC-3 owner/revision/physical-byte CAS под TASK→mutation→target locks; STARTED до записи; exact post-proof→historical DONE receipt | operation state + correlated MUTATION_EXECUTED event. Запись DONE может предшествовать event, поэтому отсутствие event не доказывает отсутствие эффекта. История не доказывает нынешние bytes | Сохранять gates, идемпотентность, bounded reconciliation. Новые policy/adapters отдельно |
| CLI mutate / прямой Python MutationExecutor.execute | Тот же logical server-owned executor, хотя HTTP server process не обязателен | Те же stores/locks/receipts. Обхода RC-3 через этот entry нет; модель server-owned логическая, не отдельный OS security principal | Утвердить допустимые adapters; не требовать HTTP ради формы |
| HTTP tracked rollbacks; CLI task recover / HTTP recover/resume | RC-4/RC-6: current-stage/lawful ACTIVE + fresh accepted Resolver, сохранение current state до destructive restore, all-target claims включая NOOP, CAS, final byte proof | Rollback stores/receipts; это отдельная recovery mutation, не normal gateway operation и не OBSERVE | Сохранить отдельный явно разрешённый recovery path; не смешивать с normal write/replay |
| Legacy CLI snapshot restore / Python ManifestSnapshotStore.restore_microtask | Проверяет snapshot, затем пишет/удаляет project files и ставит BACKUP_VERIFIED | Обходит RC-4 preservation/Resolver/claims/CAS/tracked receipts. Изолированный тест реально перезаписывает неизвестные bytes без RC-4 session. HTTP snapshot action=restore по-прежнему отказан | Отдельно утвердить retirement либо безопасный перевод в tracked RC-4; сейчас НЕ менять совместимость |
| CLI microtask prepare, snapshot verify, checkpoint rebuild; HTTP control-plane, reports, operations begin/transition, Resolver/claims | Workflow/storage writes: TASK, manifest/snapshot, payload, event/checkpoint/report/claim/resolution stores. Обычно не project bytes; recover/rollback — исключения выше | DONE может быть записан после внешней записи/ADOPT. Receipt не устанавливает, кто физически писал. Prepare/verify/rebuild имеют свои side effects и не вызываются OBSERVE | Защитить control plane/store от недоверенного writer; определить перечень прав и callable library boundaries |
| Desktop Commander Remote: прямые write/edit, shell, GUI | Только если клиент вызвал Web Alarm gateway/recovery. RemoteEntry.enter выдаёт read-only context; не перехватывает инструменты Remote | Наличие канонического entry или transport event не доказывает прохождение последующей записи через gateway. В web_alarm нет interception Remote file/shell/GUI calls | Контролируемый Remote adapter и capability policy; shell/GUI writes нельзя просто объявить защищёнными |
| Локальные Claude/Codex: прямые чтения/правки рабочих файлов | По текущему пользовательскому контракту допустимы в assigned local scope, вне Web Alarm tracked gateway | File write сам по себе не создаёт Web Alarm event. OBSERVE может увидеть оставшееся различие только в manifest текущего этапа; caller/time/operation неизвестны | Новое явно согласованное разграничение protected workflow и обычной локальной работы; адаптеры и права отдельно, Git-запрет неизменен |
| Obsidian, редакторы, formatter/build/test/tool, прочие процессы, пользователь | Нет внешнего write interception / OS access control | Create/edit/delete/rename/move могут проходить мимо locks; временное изменение с возвратом bytes и файлы вне manifest не видны. Git-переписывание файлов — концептуально ещё один external writer, Git не запускался | Для telemetry — watcher/USN/adapters с loss/overflow/restart semantics; для enforcement — реальное ограничение write capabilities, не watcher |
| Directory operations, hardlinks/reparse paths, произвольные shell/non-file эффекты | Gateway поддерживает файловые WRITE/CREATE/DELETE; move/rename — CREATE destination + DELETE source, не атомарная транзакция. Общего command/directory transaction API нет | Нельзя выдавать shell/build/GUI/network/system change за covered file mutation. Наблюдение состояния файла не покрывает его родительскую топологию или внешние ресурсы | Отдельные contracts/restore policy либо запрет таких эффектов в protected scope по новому решению |

### Проверенные source selectors

- web_alarm/server.py: mutations endpoint, snapshot verify-only endpoint, operation transition endpoints, create_server.
- web_alarm/cli.py: _handle / snapshot restore / mutate / task recover.
- web_alarm/mutation_executor.py: execute, _manifest_refusal, _execute, _mutate_locked, _apply, _execute_composite.
- web_alarm/target_claim_service.py: _cas, mutation_boundary, authorize. Standalone authorize возвращает mutation_authority=false; переносимой authority нет.
- web_alarm/rollback_service.py: _authority, prepare, _preserve, _apply_locked, _prove_current, _finalize.
- web_alarm/recovery_coordinator.py: _perform, recover; web_alarm/remote_entry.py: enter.
- web_alarm/operation_store.py: begin, transition, _validate_history; reconciliation.py: collect; projection.py: build.

## Контракт ограниченного OBSERVE

1. canonical_state и NEXT берутся из существующей RC-5 projection; новый статус исполнения не вводится. DONE остаётся DONE, UNKNOWN_AFTER_DISCONNECT остаётся UNKNOWN; receipt только HISTORICAL_ONLY.
2. operation_history выдаёт validated store facts. CORRELATED_EXECUTOR_EVENT означает совпадение persisted MUTATION_EXECUTED с identity/mutation kind/receipt, не криптографически доказанное происхождение. Без такого event — NOT_ESTABLISHED, даже если bytes уже записаны и DONE сохранён.
3. state_observation сравнивает exact bytes/size с snapshot PRE-state только для manifest текущей микрозадачи. Различие может быть законным gateway effect, редактором, legacy restore или иным действием; attribution=NOT_ESTABLISHED, external_mutation_proved=null. Это НЕ внешний event и НЕ protocol violation.
4. coverage.external_events/external_operation_count/unobserved_operation_count=null, continuous_monitoring=false. Отсутствие telemetry не превращается в ноль операций. Вне manifest ничего не сканируется; closed TASK — history-only; unprepared не подготавливается; unreadable/corrupt evidence показывается как unavailable/incomplete.
5. Две projection плюс сравнение operation basis дают bounded store consistency check. Это не транзакционный снимок проекта, не гарантия current post-state и не защита от writer после чтения. Нет бесконечных повторов. Стоимость чтения существующих histories/targets не ограничивается новым пагинатором.
6. Диагностика вызывается явно; нового persistent diagnostic state и автоматического monitor нет. Поэтому reopening проверяется recomputation на том же isolated storage в fresh Python process. POST/authority/mode parameters отказаны только на новом read-only endpoint; прежние mutations не получают нового gate.

## Preflight blockers и сохранённые риски

- Полный external OBSERVE BLOCKED: отсутствует достоверный поток внешних файловых событий с coverage/loss semantics и writer attribution. Реализован честно ограниченный вариант; никакого implicit полного PASS.
- Legacy restore остаётся реальным обходом tracked RC-4. OBSERVE не может безопасно отменить его и не должен ломать ранее разрешённые операции. Это blocker следующего enforcement scope, не скрытое исправление сейчас.
- Local same-user Python/shell/editor может писать project и server stores. Loopback API и advisory RC-3 locks не являются OS security boundary. Correlated histories не аутентифицированы; согласованная подмена stores вне threat model этой задачи.
- Внешний несовместимый writer может попасть в CAS→write gap (ранее R-1); polling/watcher не делает compare-and-replace атомарным. Windows sharing failures, отсутствие auto-parent mkdir, payload limits, P-2/P-3/P-4/R-1…R-4, non-atomic move не закрыты.
- Дополнительный source-level preflight finding: storage_policy.py/PayloadStore ограничивают durable payload (secret names, 1 MiB, forbidden workspace roots), но это не blanket policy для всех stores. WorkspaceRegistry.register и TaskStore принимают явно заданный storage_root без общей проверки пересечения с project; ManifestSnapshotStore._prepare_locked копирует перечисленные snapshot targets через read_bytes без того же secret/size admission. Это не эксплуатировалось на пользовательских данных и не исправлялось; до STRICT требуется отдельная проверка конфигурации storage и snapshot scope/secret/size/retention. Новая диагностика не копирует payload или snapshot contents в ответ.
- Тесты только offline/disposable. Не проводились live Remote-disconnect, реальные пользовательские мутации, нагрузочное/большое history испытание, OS ACL rollout. UI/UX backlog и Ultra без изменений.

## Маршрут следующих стадий — DESIGN ONLY

| Стадия | Предложенная работа | Входной gate / доказательства |
| --- | --- | --- |
| WARN | Coverage-aware диагностические предупреждения в отдельно утверждённых adapters/UI; различать state drift, событие, loss и неизвестную attribution. Определить ownership/capabilities для tracked workflow | Independent OBSERVE PASS + отдельный USER GO; сценарии всех writer classes и false-positive/negative review; локальные workflow не объявлять защищёнными автоматически |
| GATEWAY REQUIRED | Требовать logical gateway для значимых tracked normal writes; явно оставить gated RC-4 recovery. Закрыть legacy snapshot restore, разобрать direct Python/control-plane access. Читать/искать/проводить безопасные read-only проверки без gate | Утверждённый перечень adapters/операций, retirement/migration и rollback plan; доказанные no-bypass в заявленной области; негативные tests прямых методов/shell/GUI, fresh-process recovery и regression |
| STRICT | Только в явно оговорённой protected области. Для технической защиты от внешних writers нужен отдельный broker/OS principal/ACL либо sandbox capabilities; согласовать исключения редакторов и fail-closed при потере контроля. Watcher — evidence, не enforcement | Отдельный security/authority design и USER GO, независимая adversarial приёмка ограничений OS, alias/reparse/rename/directory/store tampering, crashes/restarts, совместимость и recovery; остаточные bypass должны быть явно вне заявленной защиты |
| FINAL AUDIT | Проверить заявленную границу на практике, multi-workspace, data retention/secret scope, recovery/replay, operator UX, документацию | Независимый full regression + factual boundary audit; только verifier/user меняют общий статус. OBSERVE отчёт не разрешает следующий этап |

## Источники и расхождения документации

Обязательный маршрут прочитан: 08 → общий 000 → персональный 000 Codex → 34 → 18 → 01 → 23/24/25, адресные определения/секции. PRIMARY PROFILE 23; ARCH CLASS Web Alarm Workspace / Strict Rollout / Mutation Control. DOC-GIT-01@1, DOC-TASK-BLOCK1-01@1, DOC-READ/CHANGE/VERSION применены.

Новая персональная постановка и прямой USER GO назначают WA4-R. На входе общие 000/34/01/23/24/25 содержали NEXT WA4-O / WA4-R NOT STARTED. Во время full regression стороннее параллельное обновление изменило 000/01/05/06/24/25/34: теперь они корректно фиксируют WA4-O automated PASS / interim UI и WA4-R candidate, но ещё утверждают, что постановка не вставлена и запуск не подтверждён. В этой сессии исходный БЛОК 1 реально прочитан целиком и получена прямая стартовая команда пользователя; поэтому source-of-assignment — пользователь и неизменённая персональная карточка, а не отстающий общий снимок. Новые общие фрагменты перечитаны read-only, не откатывались и не редактировались. Их противоречие текущему запуску передано координатору в дельте. WA4-O independent CI 719/719, 167 focused, 29 operator+launcher, 23 JS, 5 smoke и baseline 8966e152359c53f048f8c7b102e5c21db5e16006 — данные утверждённой постановки, не локальная Git-проверка. Локальная версия фиксируется только content SHA-256.

## Фактические изменения и тестовое evidence

Изменены только web_alarm/observation.py (новый read-only DTO), server.py (GET endpoint/capability и актуализация старого module comment), cli.py (observe command), test_web_alarm_observation.py (30 новых тестов), данный report/evidence и персональная карточка при final rotation. Executor, RC-3/RC-4/RC-5/RC-6 production code, OperationStore/contract, UI/launcher и Ultra не менялись.

Focused: 228/228 PASS, 0 FAIL/ERROR/SKIP, 305.725 s, exit 0, 0 isolation violations. 30 новых OBSERVE tests включают все 6 paired gateway actions, настоящие HTTP GET/POST, отсутствие новых files/status/authority calls, fresh-process CLI reopen, historical receipt/replay, external create/edit/delete/rename/CRLF drift, отсутствие coverage вне manifest и transient change, external DONE без gateway evidence, post-DONE executor-event failure, live-store race, corrupt snapshot/receipt/history и закрытую TASK. Full Web Alarm: 749 total = 748 PASS + 1 SKIP, 0 FAIL / 0 ERROR, 686.342 s, exit 0, 0 isolation violations. Единственный SKIP: test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed — symlink creation is not permitted here. Это ограничение Windows permissions текущей среды, не PASS этого сценария. Все source_sha256 полного прогона совпали с финальными source bytes; focused и full используют одну финальную runtime/test revision.

Node UI regression: 23/23 PASS, 0 FAIL/SKIP, exit 0 (UI не изменялся). Python compileall web_alarm + новый test: exit 0; pycache только в system TEMP. В четырёх целевых Python files нет trailing whitespace/NUL. Исходные hashes, 36 точных selectors и параллельная документационная дельта — versions.json; каждый guarded результат содержит точные test IDs/statuses и source_sha256, поэтому code ↔ evidence можно перепроверить без истории Git.

Два development run не скрыты: 21 tests = 15 PASS + 6 fixture ERROR, затем 19 PASS + 2 fixture FAIL. Причины и source revisions сохранены в development.json. Исправлены fixtures/ожидания согласно существующему API; production guarantees для получения PASS не менялись. Финальные focused/full запускаются по конечным исходникам.

### Команды воспроизведения

Из M:\GitHub\ag_llm, с собственными новыми каталогами под system TEMP (не live storage):

~~~powershell
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --task CODEX-WA4-R-001 --output "$env:TEMP\wa4r-Iurd2b\focused" test_web_alarm_observation test_web_alarm_mutation_executor test_web_alarm_lost_response test_web_alarm_target_claims test_web_alarm_target_claims_concurrency test_web_alarm_cli test_web_alarm_server test_web_alarm_projection_repair2 test_web_alarm_recovery_coordinator_repair4b test_web_alarm_rollback
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --task CODEX-WA4-R-001 --output "$env:TEMP\wa4r-Iurd2b\full" all
node --test test_web_alarm_operator_ui.js
.\.venv\Scripts\python.exe -B -X "pycache_prefix=$env:TEMP\wa4r-Iurd2b\compile" -m compileall -q web_alarm test_web_alarm_observation.py
~~~

Guard wa4a_acceptance.py неизменён: запрещены Git metadata, внешние socket/DNS, shell/native subprocess; Python child inherits guard; записи разрешены только внутри system TEMP. Loopback разрешён для настоящего HTTP. Это audit isolation для доверенных tests, не OS sandbox против враждебного native кода. Windows-native helpers уже существующих tests не становятся доказательством невозможности произвольного OS bypass. Все destructive examples находятся в новых disposable project/storage. Сырые stdout и fixtures оставлены только во временном окружении.

Для использования диагностики после приёмки: HTTP GET /tasks/{existing_task_id}/observe либо python -B -m web_alarm.cli --storage-root <existing-state-root> observe --task-id <task_id>. Эта задача не запускала команды на production/live storage.

## DOC IMPACT / SHARED DOC DELTA

DOC IMPACT: YES; CURRENT STATE IMPACT: YES; ARCHITECTURE IMPACT: YES (ограниченный read-only diagnostic contract, authority unchanged); CONTEXT LIBRARY IMPACT: NO; REGISTRY / ROUTING IMPACT: YES (status handoff, routing unchanged); NEW NORMATIVE DOCUMENT REQUIRED: NO; отдельный task-report/evidence необходим для независимой проверки. CANONICAL OWNER: 23 (architecture), 24 (rollout plan), 25 (accepted history); coordinator ChatGPT для common docs. Нормативные Rule-ID/contracts не изменены. Новых wiki-связей или цифровых Repair-тегов не добавляется.

Предлагаемая дельта координатору, не заявление о выполненной общей записи:

- 23: описать только bounded on-demand OBSERVE, external feed unavailable, receipts/events historical, state-difference unclassified, no new enforcement/authority. Сохранить legacy restore и direct writer bypass в ограничениях.
- 24: WA4-R preflight / limited OBSERVE — RESULT READY / AWAITING INDEPENDENT VERIFICATION; WARN/GATEWAY REQUIRED/STRICT/FINAL AUDIT не начинались. После независимого review следующий переход требует отдельного USER GO и утверждённого adapter/security/migration scope. UX-2026-10-11 A/B/C не изменялся.
- 25: после независимой приёмки append-only entry с реальными локальными/independent counts; не давать retroactive PASS старому Remote combined criterion или всей WA4-R.
- 000/34/01 и 05/06: сохранить параллельно внесённую WA4-O automated PASS / interim visual acceptance; заменить неверное для этой сессии WA4-R candidate / no user insertion or launch на фактически выполненный CODEX-WA4-R-001 preflight/limited OBSERVE, RESULT READY / AWAITING INDEPENDENT VERIFICATION. Основание — исходный personal БЛОК 1 и прямой USER GO в данном чате. Не присваивать DONE; сохранить прошлые вехи, unresolved P/R и Ultra scope. 23 также требует краткой актуализации устаревшего current route.
- 18/08: текущие нормы/route менять не требуется. Будущее требование локальным агентам использовать protected gateway потребует отдельного явного решения; запрет Git не ослабляется.

Общий документационный контур: DOC CLOSEOUT INCOMPLETE — запись/статусы common/profile owners оставлены ChatGPT согласно scope; это не недостаток runtime test и не самостоятельный DONE.

## NEXT SAFE ACTION

ChatGPT независимо сверяет code ↔ hashes ↔ tests, повторяет guarded focused/full при необходимости и принимает именно ограниченный OBSERVE, включая доказанные слепые зоны и legacy bypass. Затем пользователь отдельно утверждает следующую TASK. До этого WARN/GATEWAY REQUIRED/STRICT не включать. После отчёта Codex остановится.

## Final rotation / loss check

Исходная постановка сохранена дословно в БЛОКЕ 2, factual result — в БЛОКЕ 3; прежние БЛОКИ 2–3 сохранены дословно внутри длинного fenced archive (10 backticks). Только после проверки обеих записей БЛОК 1 переведён в ожидание. Windows один раз отказал EPERM при финальном rename: первая фаза и staged final были сверены по SHA-256, одна ограниченная повторная попытка успешно завершила замену. Результаты и hashes — rotation.json, конечные artifacts — manifest.json. Ни чужие документы, ни пользовательские данные ради этого не удалялись.
