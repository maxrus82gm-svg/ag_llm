# Журнал наблюдений Remote — обрывы, transport и recovery evidence

**Статус:** ACTIVE TECHNICAL EVIDENCE JOURNAL.

**Ветка:** Web Alarm Workspace / WA-3 recovery architecture.

**Роль документа:** хранить реальные технические наблюдения об обрывах Remote, partial execution, reconnect, replay и reconciliation. Это не архитектурный источник и не план реализации. Архитектурные решения остаются в `23_Архитектура Web Alarm Workspace.md`; этот файл поставляет им накопленные факты.

**Правило:** сюда заносится только наблюдаемое или проверяемое evidence. Предположения маркируются отдельно и не превращаются в факт.

---

## 1. Зачем нужен отдельный журнал

Remote-обрыв не является одной ситуацией.

Практически важны разные классы:

- связь оборвалась **до mutation**;
- отдельная mutation успела выполниться, но ответ потерян;
- composite-вызов выполнился **частично**;
- локальный executor продолжает жить, но Remote transport временно недоступен;
- channel reconnect восстановил доставку позже;
- operation уже находится в `executing/STARTED`, поэтому повтор может дать duplicate side effect;
- terminal result мог не дойти до вызывающей стороны при уже выполненной работе.

Для WA-3.3 нельзя сводить эти случаи к одному `FAILED`.

---

## 2. Уровни достоверности

### CONFIRMED

Факт подтверждён чтением диска, process state, package source или повторной verification.

### OBSERVED

Факт наблюдался в реальной рабочей сессии, но не обязательно имеет полную transport-трассу.

### HYPOTHESIS

Технически правдоподобное объяснение, которое ещё нельзя назначить причиной конкретного обрыва.

---

## 3. Текущий Remote runtime на машине — снимок 2026-10-02

### 3.1 Установленная версия

На машине фактически запущен:

`@wonderwhy-er/desktop-commander 0.2.52`.

Запуск идёт через:

`npx.cmd @wonderwhy-er/desktop-commander@latest remote`.

### 3.2 Process lifetime

Read-only PowerShell inspection показал:

- wrapper `cmd.exe` / `node.exe` стартовал около **08:17:51**;
- основной Remote device process стартовал около **08:17:59**;
- дочерний `node.exe` executor существует с около **08:18:20**;
- на момент проверки около **12:07** эти процессы всё ещё были живы;
- у двух node-процессов оставались established TCP connections;
- в Windows Application Error за последние 6 часов не найдено совпадающих crash/error событий для node/Desktop Commander/PowerShell.

**Вывод CONFIRMED:** по текущим наблюдаемым обрывам нет evidence, что Desktop Commander process полностью падал и перезапускался.

Это сужает область поиска: часть сбоев находится выше уровня process lifetime — channel/network/result delivery/Chat transport — либо представляет кратковременный transport reset при живом executor.

Это **не доказывает**, что каждый прошлый сбой имел одну и ту же причину.

---

## 4. Что видно в transport-коде Desktop Commander 0.2.52

Источник наблюдения: установленный локальный package
`@wonderwhy-er/desktop-commander/dist/remote-device/remote-channel.js`.

### 4.1 Broadcast не является source of truth

В коде явно зафиксировано:

- Realtime broadcast — быстрый "doorbell";
- durable таблица `mcp_remote_calls` — источник истины;
- после reconnect устройство делает recovery scan pending calls;
- один reconnect scan ограничен batch до 100 pending calls.

**Практический смысл:** doorbell может потеряться во время короткого disconnect, но pending call способен быть найден после восстановления канала.

### 4.2 Call сначала claim-ится, потом исполняется

Doorbell-handler делает conditional transition:

`pending → executing`

и только затем передаёт call локальному executor.

Claim привязан к call id и статусу `pending`, поэтому duplicate doorbell не должен автоматически превращаться во второе выполнение.

Особенно важен комментарий самого transport-кода: если после claim error read-back показывает `executing`, нельзя угадать, кто именно claim сделал. Повторное выполнение side-effecting call в этой ситуации может выполнить действие **дважды**, поэтому transport предпочитает пропустить повтор.

**Это напрямую совпадает с инвариантом Web Alarm: неизвестную незакрытую mutation нельзя повторять вслепую.**

### 4.3 Reconnect recovery поднимает только доказанно pending calls

После успешного reconnect transport выбирает ещё живые строки со статусом `pending` и снова пропускает их через conditional claim.

Из этого следует важное разделение:

- `pending` после reconnect ещё можно безопасно claim-ить;
- `executing` уже является неоднозначным состоянием и требует reconciliation.

### 4.4 В коде явно учитываются half-open WebSocket

Desktop Commander содержит отдельную защиту от состояния, когда socket выглядит `OPEN`, но фактически мёртв.

В текущей версии присутствуют:

- reconnect backoff с jitter;
- `JOINING_WEDGE_TIMEOUT_MS = 30000` — около 30 секунд непрерывного `joining` до forced recreate;
- `HEARTBEAT_STALE_TIMEOUT_MS = 75000` — около 75 секунд без подтверждённого heartbeat при формально `joined`;
- `RECREATE_TIMEOUT_MS = 45000` — верхняя граница recreate;
- явный teardown старого channel;
- явный `realtime.disconnect()` для сброса half-open WebSocket;
- ожидание выхода realtime-js из `disconnecting` перед новым subscribe.

**Вывод CONFIRMED:** сама библиотека считает half-open socket и зависший `joining` реальными transport failure modes и содержит self-healing watchdog.

### 4.5 Result delivery — отдельный шаг после фактического выполнения

После tool execution Remote отдельно записывает terminal result/status обратно в `mcp_remote_calls`.

Код отдельно обрабатывает ситуацию, когда result не удаётся сохранить. В комментариях прямо отмечен нежелательный сценарий: call может остаться `executing`, а пользователь ждать timeout для tool, который **фактически уже выполнился**.

**Архитектурный вывод:** "клиент не получил успешный ответ" не эквивалентно "mutation не произошла".

Именно поэтому WA-3.3 должен сравнивать фактический Workspace с pre/post evidence, а не принимать transport response за единственный источник истины.

---

## 5. Реальные incident cases проекта

### INC-REMOTE-001 — disconnect после restore point, до implementation

**Связано с:** WA-3.1.

**Наблюдение:**

- restore point уже существовал и был SHA256 VERIFIED;
- после reconnect source/snapshot hashes совпадали;
- новые `remote_entry.py` и test-файл отсутствовали;
- `000` всё ещё показывал WA-3.1 как неактивированную;
- implementation mutation ещё не началась.

**Масштаб partial execution:** **0 code mutations**.

**Правильное действие:** продолжить с первой неподтверждённой точки — activation.

**Запрещённое действие:** повторять "последнюю задачу целиком".

**Кандидат decision для будущего WA-3.3:** `RETRY_SAFE` / resume from known pre-state.

---

### INC-REMOTE-002 — composite Remote call оборвался после частичного выполнения

**Связано с:** WA-3.2 integration.

**Наблюдение:**

Один composite orchestration call должен был:

1. изменить `web_alarm/__init__.py`;
2. затем изменить `web_alarm/server.py`.

Tool-call вернулся transport failure.

Disk reconciliation показал:

- обе правки в `__init__.py` **уже применены**;
- `server.py` **ещё не изменён**.

**Масштаб partial execution:** часть последовательности mutations выполнена, часть — нет.

**Правильное действие:** не replay composite call. Продолжить только с доказанно отсутствующей Server integration.

**Главный вывод:** failure на уровне внешнего Remote-вызова не является atomic rollback всего набора уже awaited mutations.

---

### INC-REMOTE-003 — documentation closeout частично применился

**Связано с:** WA-2.1 documentation closeout.

Composite documentation edit вернулся transport failure после частичного исполнения.

После reread:

- несколько правок `24_План реализации Web Alarm Workspace.md` уже присутствовали;
- один CURRENT-status edit отсутствовал.

Были сохранены уже применённые изменения и добавлена только отсутствующая часть.

**Масштаб partial execution:** несколько документных mutation внутри одной orchestration sequence.

**Вывод:** partial execution относится не только к code mutation; одинаковая recovery-модель нужна для docs и других side effects.

---

### INC-REMOTE-004 — ранее наблюдавшаяся повторная доставка после reconnect

В предыдущих Remote-сессиях проекта наблюдалось, что pending вызов после reconnect мог быть доставлен повторно транспортом.

Текущий source Desktop Commander подтверждает техническую возможность recovery pending calls после reconnect и conditional claim для борьбы с duplicate delivery.

**Статус evidence:** OBSERVED + transport mechanism CONFIRMED.

Для количественной оценки частоты нужны отдельные operation/event counters; текущих данных недостаточно.

---

### INC-REMOTE-005 — tool result не сохранился при живом Remote process

**Связано с:** старт WA-3.3.1, read-only inspection.

При одновременном чтении нескольких файлов Remote вернул точную ошибку:

`Result could not be stored (TypeError: fetch failed)`.

Сразу после этого отдельный маленький read прошёл успешно, а PowerShell подтвердил те же Desktop Commander node PID и исходные `CreationDate` — локальный Remote process не перезапускался.

**Масштаб side effect:** вызов был read-only; mutation отсутствовала, поэтому повтор отдельных чтений безопасен.

**Почему случай важен:** текст ошибки практически совпадает с механизмом `updateCallResult()` в установленном `remote-channel.js`, где tool может уже отработать локально, а отдельная запись terminal result обратно в durable Remote state не сохраниться. Это первый текущий live-case, где наблюдение напрямую похоже именно на **result-delivery/storage failure при живом executor**, а не на process crash.

**Статус evidence:**
- точная ошибка tool layer — CONFIRMED;
- process не перезапускался — CONFIRMED;
- что именно fail произошёл в том же внутреннем `updateCallResult()` code path — HYPOTHESIS, хотя сообщение и локальный source сильно согласуются.

**Recovery:** поскольку операция read-only, выполнен маленький connectivity/read check, затем чтения разрешено повторить по одному. Для mutation такой вывод был бы недостаточен — потребовался бы Workspace reconciliation.

---

### INC-REMOTE-006 — Chat/Remote disconnect при продолжающемся локальном verification process

**Связано с:** WA-3.3.1 full regression.

Полный verification process был уже запущен под PID `19320`, после чего связь с Chat/Remote снова оборвалась.

После reconnect процесс **не перезапускался и не запускался повторно**. Чтение output того же PID показало, что он самостоятельно завершил полный прогон:

- **100/100 tests PASS**;
- `WA331_FULL_VERIFY_PASS`;
- exit code `0`.

Дополнительная read-only PowerShell проверка сразу после reconnect снова показала те же Desktop Commander node PID и те же исходные `CreationDate` (~08:17–08:18).

**Масштаб side effect:** verification process продолжил работу полностью независимо от потери ответа в Chat; повторный запуск не потребовался.

**Вывод CONFIRMED:** по крайней мере в этом инциденте обрыв произошёл **выше локального executor/process уровня**. Локальная команда продолжала выполняться и дошла до подтверждённого результата, пока вызывающая сторона потеряла связь.

Это усиливает архитектурное требование: после transport failure нельзя считать запущенную операцию неисполненной только потому, что caller не получил финальный response.

**Recovery:** read existing process output → принять уже полученный terminal result → не replay process.

---

### INC-REMOTE-007 — повторный scope-extension перезаписал manual snapshot path

**Связано с:** WA-3.3.1 documentation closeout preparation.

Перед closeout документации manual TASK-session расширял snapshot scope. При независимой SHA256-проверке оказалось, что для шести документов (`01`, `04`, `05`, `06`, `24`, `25`) в `manifest.json` существуют по **две записи одного и того же path** с разными историческими hashes.

При этом обе записи ссылались на один и тот же snapshot path. Более поздний `Copy-Item` заменил байты snapshot, поэтому ранняя manifest-запись стала указывать на уже другой файл и verification закономерно упала.

**CONFIRMED:**
- duplicate manifest rows существуют;
- affected paths имеют count=2;
- current source совпадает с более поздним snapshot/hash;
- старый manifest hash больше не совпадает с общим snapshot path;
- closeout edits на эти документы к моменту обнаружения ещё не начинались.

**Что НЕ доказано:** конкретный trigger повторного scope-extension (transport replay, ранее частично выполненная подготовка или повторная orchestration) по имеющимся данным однозначно не установлен.

**Архитектурный вывод:** snapshot storage для scope-extension должен быть **append-safe и immutable**. Нельзя повторно использовать один физический snapshot path для разных captured revisions одного source path. Нужен уникальный snapshot instance/revision id и dedupe/check-before-append.

**Recovery:** исходный manifest не переписывать и не удалять как evidence; для closeout создать отдельный versioned manifest/snapshot directory, проверить `source hash before == snapshot hash == source hash after`, и только затем продолжать documentation mutation.

---

### INC-REMOTE-008 — automatic continuation прошёл дальше видимой Chat-точки

**Связано с:** переход WA-3.3.1 → WA-3.3.2.

После очередного disconnect текущий видимый Chat оставался на recovery WA-3.3.1. Однако disk reconciliation обнаружил:

- WA-3.3.1 session уже содержит `DONE / VERIFIED` closeout и `next=WA-3.3.2`;
- существует отдельный `TASK_WA-3.3.2` session;
- `reconciliation_decision.py` и focused tests реально созданы;
- session WA-3.3.2 содержит последовательность INTENT/DONE/FAILED/REPAIR/VERIFIED;
- независимый повторный verification после обнаружения дал **16/16 focused PASS** и **116/116 full WA PASS**;
- часть документации уже была переведена на WA-3.3.2 DONE, тогда как `000`, `05`, `06`, `25` оставались на более ранней точке.

**CONFIRMED:** локальные действия продолжились дальше той точки, которую видел текущий Chat, и оставили persistent state в разных слоях на разных этапах closeout.

**Что НЕ доказано:** точный transport mechanism — delayed delivery, pending recovery, повторная orchestration или иной внутренний queue path — по текущему evidence однозначно не установлен.

**Архитектурный вывод:** automatic next-task continuation нельзя считать завершённым только по отправке последнего tool call. Нужен persistent gate: следующая microtask может стать ACTIVE только после атомарного closeout предыдущей (`DONE_VERIFIED` + synchronized checkpoint/docs) и отдельной recorded activation новой задачи. При reconnect Chat обязан читать этот gate, а не исходить из последнего видимого сообщения.

**Recovery:** не откатывать доказанно работающий WA-3.3.2; независимо verify code → признать implementation VERIFIED → привести документацию к одной authoritative точке → только затем разрешать WA-3.3.3.

---

### INC-REMOTE-009 — composite tool orchestration вернул ошибку после первой mutation

**Связано с:** reconciliation документации WA-3.3.2.

Один composite tool-call должен был сначала обновить status-блок в документе `25`, затем append-нуть подробную запись WA-3.3.2. Внешний вызов завершился ошибкой/блокировкой, поэтому его результат нельзя было считать атомарным.

Disk reread показал:
- первый `edit_block` уже применён;
- второй append отсутствовал.

**CONFIRMED:** даже orchestration-level rejection/error не гарантирует, что ни одна более ранняя mutation внутри последовательности не успела примениться.

**Recovery:** перечитать все targets composite-call, не повторять уже применённый `edit_block`, выполнить только отсутствующий append отдельным вызовом.

**Архитектурный вывод:** composite orchestration должна рассматриваться как sequence of independently observable operations, пока нижний слой не предоставляет настоящий atomic transaction/receipt. Каждому mutation step нужен собственный operation receipt или post-state proof.

---

## 6. Что пока НЕ доказано

На текущем этапе нельзя утверждать:

- что каждый Chat/Remote reset вызван half-open WebSocket;
- что проблема находится только в Desktop Commander;
- что проблема находится только в ChatGPT UI/transport;
- что каждый transport failure означает потерю результата записи в `mcp_remote_calls`;
- что текущая сеть пользователя является первопричиной;
- что все инциденты имеют один и тот же failure mode.

Текущие факты показывают лишь то, что **несколько разных уровней могут разойтись по состоянию**:

`Chat response`
→ `Remote transport`
→ `mcp_remote_calls state`
→ `local executor`
→ `real Workspace`.

Последний слой — фактический Workspace — должен быть главным evidence для reconciliation side effects.

---

## 7. Что собирать при каждом следующем обрыве

Минимальный incident packet:

1. TASK / microtask.
2. `operation_id`.
3. Remote-call тип.
4. Последний подтверждённый lifecycle operation.
5. Был ли tool result получен в Chat.
6. Состояние Desktop Commander process — жив/перезапущен.
7. Current microtask / checkpoint.
8. Snapshot status.
9. Manifest targets.
10. Для каждого target:
   - exists-before;
   - pre/snapshot hash;
   - current exists;
   - current hash;
   - expected post hash, если известен.
11. Какие отдельные mutation в composite sequence доказанно успели выполниться.
12. Recovery decision.
13. Что фактически было сделано после recovery.
14. Regression result после продолжения.

Не собирать гигантские логи без причины. Нужны короткие структурированные evidence records.

---

## 8. Техническая телеметрия, которую имеет смысл добавить позже

Для Web Alarm полезно автоматически сохранять compact transport observation:

```text
incident_id
captured_at
task_id
microtask_id
operation_id
remote_call_kind

chat_result_received
remote_error_class

desktop_commander_pid
desktop_commander_process_start
process_restarted_since_intent

operation_status
checkpoint_status
snapshot_status

targets_total
targets_match_pre
targets_match_expected_post
targets_drifted
targets_missing_evidence

decision
next_safe_action
```

Это даст возможность позже оценивать:

- сколько обрывов произошло до mutation;
- сколько — после полной mutation;
- сколько — в partial state;
- среднее число targets, затронутых partial execution;
- долю reconnect без process restart;
- сколько случаев решились `ADOPT_CURRENT_STATE`, `RETRY_SAFE`, `ROLLBACK_CURRENT_MICROTASK`, `MANUAL_REVIEW_REQUIRED`.

---

## 9. Как этот журнал используется WA-3.3

WA-3.3 не должна пытаться диагностировать "почему интернет оборвался" как обязательное условие восстановления.

Для безопасного recovery достаточно доказать **что произошло с Workspace**.

Transport evidence используется как дополнительный слой:

- process не перезапускался → не считать executor crash доказанным;
- operation `pending` → возможно безопасное claim/retry по transport identity;
- operation `STARTED/executing` → не replay, сначала Workspace reconciliation;
- response lost + expected post-state доказан → `ADOPT_CURRENT_STATE`;
- current = pre-state и operation не могла завершиться → `RETRY_SAFE`;
- partial/drift/insufficient evidence → rollback candidate или `MANUAL_REVIEW_REQUIRED`.

---

## 10. Правило пополнения

После каждого реального Remote disconnect/reconnect, если он затронул активную TASK:

1. сначала выполнить recovery текущей TASK;
2. не задерживать рабочее восстановление ради длинной диагностики;
3. после стабилизации записать короткий incident case сюда;
4. отделить CONFIRMED от HYPOTHESIS;
5. если появился новый повторяемый failure mode — только тогда поднимать изменение архитектуры в документ 23 или план 24.

Этот файл должен со временем стать набором реальных failure patterns, а не коллекцией предположений.

---

## 11. Findings после WA-3.3.1 — что уже можно доказать, а чего пока не хватает

### CONFIRMED: pre-state evidence сильное

Manifest/Snapshot уже хранит для existing target точный `size_before` + `sha256_before` + snapshot bytes. Для new target pre-state явно выражен как `exists_before=false`. Поэтому состояние `PRE_STATE` можно доказывать механически и restart-safe.

### CONFIRMED GAP: exact expected post-state пока не является обязательной persistent частью OperationRecord

Текущий `OperationRecord` хранит `expected_precondition_sha256`, request fingerprint и result summary, но не хранит отдельный `expected_postcondition_sha256` и не хранит исходный request payload как authoritative postcondition material.

Следствие:
- `delete` можно доказать как exact expected post-state через manifest `expected_change=delete` + отсутствие файла;
- для `edit/create` без отдельно сохранённого expected post hash текущий changed file можно доказать как **не pre-state**, но нельзя автоматически доказать, что это именно правильный post-state;
- collector поэтому возвращает `CHANGED_UNCLASSIFIED` и `expected_post_complete=false`, а не угадывает success.

**Design implication для WA-3.3.2:** отсутствие exact post evidence должно вести fail-closed, а не к `ADOPT_CURRENT_STATE`.

**Potential later improvement:** перед mutation persistent Operation intent может хранить canonical expected postcondition (exists + hash/size либо другой строгий verifier identity). Решение о расширении schema должно приниматься отдельно после Decision Engine tests, а не молча добавляться внутри read-only stage.

### CONFIRMED GAP: VerificationRecord schema есть, отдельного verification store пока нет

В `models.py` существует `VerificationRecord`, но отдельный persistent Verification Store в текущем WA runtime не реализован. WA-3.3.1 поэтому может использовать как verification evidence только уже persistent факты, например `OperationRecord.status=VERIFIED` + `result_summary`.

**Design implication:** Decision Engine обязан различать `verification evidence absent` и `verification failed`; отсутствие evidence не превращать в PASS.

### Практический вывод

WA-3.3.1 дал полезную границу authority:

`PRE_STATE` может быть доказан уже сейчас очень надёжно.

`EXPECTED_POST_STATE` доказуем только когда exact expected post evidence действительно существует.

Любой другой changed state должен оставаться `CHANGED_UNCLASSIFIED` / `MISSING_EVIDENCE` / `DRIFT` до следующего deterministic decision stage.

---

### OBS-OBSIDIAN-001 — recovery snapshots засоряют Graph View одинаковыми basename

**Связано с:** manual Alarm fallback / TASK-session snapshots.

Пользователь визуально обнаружил множество одинаковых узлов `01_Архитектура...`, `05_Реестр задач`, `history`, `context` и т.д. в Obsidian Graph. Disk inspection подтвердил, что в canonical `Документация` оригиналы одиночные, но внутри `Alarm/ALARM_TASK_SESSION/.../snapshot*` накоплено **212 Markdown-файлов**. Например, `01_Архитектура и текущее состояние.md` присутствовал в vault 16 раз: один canonical original + recovery copies.

`.obsidian/app.json` уже содержал `/Alarm/` в `userIgnoreFilters`, однако Graph View продолжал отображать excluded files. Для самого graph добавлен persistent filter `-path:Alarm`; заодно исключены очевидные runtime/cache dirs `.venv`, `.pytest_cache`, `.ultra`, `sandbox_verify`, `_ultra_agent_test`. Настройки продублированы в `userIgnoreFilters`. Recovery snapshots не удалялись.

После расчётного применения этих runtime-фильтров количество Markdown в graph scope уменьшается с 272 до 39; duplicate basenames из recovery исчезают, остаётся только два содержательных `README.md` вне отфильтрованных runtime directories.

**Архитектурный вывод:** production Web Alarm state/snapshot storage желательно физически держать вне пользовательского Obsidian vault. Если fallback storage временно находится внутри project root, vault-specific ignore + Graph path filter являются обязательной защитой от визуального и поискового загрязнения.

---

### INC-REMOTE-010 — WA-3.3.3 продолжилась дальше видимой Chat-точки; recovery подтверждён двумя fresh sessions

**Связано с:** WA-3.3.3 Server / Remote integration.

После пользовательского возврата и визуальной проверки Obsidian Graph disk reread показал, что WA-3.3.3 уже успела выполнить implementation edits, focused integration и начать final full regression, хотя видимый Chat перед этим находился только на read-only inspection/planning стадии.

`session.jsonl` содержал DONE для ReconciliationService, Context Pack, Remote Entry, Server endpoint, package export и focused test; также были зафиксированы два outer result-storage failures, после которых disk reread доказывал уже применённые edits. Последняя запись была только `INTENT` на final full regression без terminal result.

**Recovery Session A:** старого Python verification process уже не было. Новый независимый process выполнил py_compile, focused integration **7/7 PASS**, full WA **123/123 PASS**, `git diff --check` PASS.

**Recovery Session B:** после явного закрытия Session A новый PowerShell/Python process заново прочитал persistent handoff и отдельно проверил restart semantics: new Server instance, Canonical Remote Entry и real HTTP reconcile endpoint → **3/3 PASS** без Workspace mutation.

**CONFIRMED:** implementation/result не зависит от памяти старого Chat/Python process; persistent state достаточен для восстановления. Также подтверждён failure mode, где automatic continuation может пройти дальше последней видимой пользователю Chat-точки.

**Архитектурный вывод:** recovery acceptance полезно выполнять минимум в двух фазах: (A) independent implementation verification; (B) fresh-process reopen/persistence verification. Closeout следующей microtask разрешать только после обеих фаз и reread persistent closeout gate.

---

### OBS-RECOVERY-SESSION-001 — многофазный close/reopen test без реального transport disconnect

**Связано с:** WA-3.3.3 closeout и WA-3.3.4 final recovery matrix.

Поскольку Chat/Remote transport нельзя безопасно и детерминированно разрывать изнутри текущего агента, проверка session continuity выполнена через несколько независимых persistent фаз с новыми PowerShell/Python process instances.

**WA-3.3.3:**
- Session A — независимый fresh-process verification: focused 7/7, full WA 123/123 PASS;
- Session B — fresh reopen/restart semantics: new Server instance + Remote Entry + HTTP reconcile 3/3 PASS;
- Session C — отдельный versioned documentation closeout;
- Session D — новый process перечитал session/context/000/05 и получил одну authoritative точку `DONE_VERIFIED → WA-3.3.4`.

**WA-3.3.4:**
- Session A — core four-way recovery decisions 4/4 PASS;
- Session B — extended restart/duplicate/UNKNOWN/new/delete/corrupt matrix 10/10 PASS;
- Session C — fresh full WA regression 133/133 PASS.

**CONFIRMED:** working state не требует памяти предыдущего Python process; persistent task-session + canonical docs достаточно, чтобы новый process восстановил одну рабочую точку. Versioned session boundaries также не потребовали runtime repair.

**Ограничение:** это не заменяет будущий controlled test реального transport disconnect. Такой controlled disconnect остаётся отдельным acceptance requirement WA-3.

---

### INC-REMOTE-011 — outer result-storage failure after full closeout bundle already persisted

**Связано с:** WA-3.3.4 final closeout.

Composite closeout call вернул `Result could not be stored (TypeError: fetch failed)`. Disk reread после ошибки показал, что все три последовательные mutation уже успели примениться полностью: `context.md` = DONE / VERIFIED, `history.md` дополнен, `session.jsonl` содержит CLOSEOUT_VERIFIED + CLOSED + TASK_STATUS DONE_VERIFIED.

**CONFIRMED:** caller-facing failure произошёл после полного локального side effect sequence. Повтор всего closeout bundle создал бы duplicate history/session records.

**Recovery:** только reread three targets; поскольку все ожидаемые post-state уже доказаны, никаких mutation не replay-илось.

**Вывод:** terminal caller error может соответствовать как partial execution, так и full execution. Единственный надёжный способ различить эти случаи — post-state reconciliation по каждому target/operation receipt.

---

### INC-REMOTE-012 — переход к новой TASK сохранил manifest, но не session/context

**Связано с:** transition WA-3.3.4 → WA-3.4.

Composite переход должен был: закрыть WA334-D, создать `TASK_WA-3.4`, сформировать immutable/versioned `manifest_initial_v1`, затем создать context/session и активировать `000`. Внешний вызов завершился `Result could not be stored (TypeError: fetch failed)`.

Disk reconciliation показал:
- WA334-D close records уже записаны;
- `TASK_WA-3.4` directory создана;
- `manifest_initial_v1.json` и snapshot files полностью существуют;
- snapshot hashes повторно проверены → PASS;
- `context.md` и `session.jsonl` на тот момент отсутствовали.

**Recovery:** manifest/snapshots не пересоздавались и не перезаписывались; были созданы только отсутствующие context/session и затем активирован `000`.

**Архитектурный вывод:** new-task bootstrap сам является многошаговой mutation и требует persistent bootstrap phase/receipts: `TASK_DIR_CREATED → SNAPSHOT_VERIFIED → SESSION_CREATED → HANDOFF_ACTIVATED`. После failure продолжать только с первого отсутствующего receipt.

---

### OBS-RESTART-001 — process-level Chat/Server restart recovery подтверждён

WA-3.4 проверила два независимых случая. Новый Chat subprocess при живом HTTP Server получил тот же checkpoint/reconciliation fingerprint/NEXT SAFE ACTION. Затем два независимых Python subprocess по очереди поднимали новый Web Alarm Server из одного disk state и создавали новый `RemoteEntry`; recovery state оставался идентичным, Workspace не менялся. Focused suite **2/2 PASS**, full WA regression **135/135 PASS**.

**Вывод:** текущий persistent слой действительно достаточен для восстановления после process restart; hidden in-memory state старого Chat/Server для этого не требуется.
