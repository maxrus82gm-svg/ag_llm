# CODEX-WA4-A-001 — Deterministic Lost-Response Acceptance

**Исполнитель:** локальный Codex. **Дата:** 2026-10-11. **ARCH CLASS:** Web Alarm Workspace / Mutation Gateway / Recovery / Acceptance.

**RESULT STATE: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Независимый DONE/VERIFIED не присваивался.

## 1. Результат и границы

Детерминированно воспроизведена цепочка: сервер выполняет mutation, сохраняет receipt, HTTP handler пытается отправить ответ, транспорт не доставляет ни одного байта, клиент фиксирует UNKNOWN, процесс завершается. Новый процесс с новым API/store повторяет исходный запрос и получает исходный receipt без второй записи.

Acceptance выявила пробел в A8: исходный runtime мог вернуть HTTP 200 / REPLAYED при противоречивом receipt, контракте или operation history. После воспроизведения добавлена проверка связности persistent evidence. Сам executor, HTTP/CLI mutation interface, lifecycle, Resolver и recovery algorithm не перепроектировались.

Разрешение на старт — пользовательский запрос и неизменённый при исполнении БЛОК 1 карточки Codex. Пройден маршрут 08 → общий 000 → 34 → 18 → 01 → 23/24/25. Общие документы ещё показывали WA4-A как следующий кандидат; отдельный USER GO дан в этом чате. Историческая ссылка WA4-E: commit `a142817b33964691584aadbd6ea6464779df1815`, №177, из handoff 23–25. Git-состояние и принадлежность локальных файлов этому коммиту самостоятельно не проверялись.

Все испытания используют disposable temporary Workspace и отдельный temporary storage. HTTP acceptance работает через настоящий `_JsonHandler._run` / `WebAlarmApi.dispatch` и in-memory wire. Существующий полный regression дополнительно использует loopback HTTP. Реальный Remote disconnect, внешняя сеть/модели, live TASK/storage, Git/GitHub, Ultra и изменение UI не использовались. WA4-O/WA4-R не запускались.

## 2. Изменения

| Файл | Фактическое изменение |
|---|---|
| `wa4a_acceptance.py` | Test fixture, отдельные Python workers, HTTP delivery-loss wire, crash hooks, fsync-журнал физических применений, барьер четырёх клиентов, guarded unittest runner и structured evidence |
| `test_web_alarm_lost_response.py` | 46 acceptance/adversarial tests; ожидаемый исход и assertions заданы в каждом тесте, фактические данные сохраняются в JSON |
| `web_alarm/operation_contract.py` | Проверка action ↔ mutation kind, диапазона receipt revision, соответствия receipt/post-state и match/EOL flags; противоречивый DONE/VERIFIED запрещён |
| `web_alarm/operation_store.py` | При загрузке v2 сверяются Workspace с TASK и intent/transition/execution history с контрактом, revision/status/receipt; отсутствие исходного intent evidence блокирует использование операции |
| Персональная карточка Codex | После проверок — исходная постановка в БЛОК 2, factual handoff в БЛОК 3, БЛОК 1 освобождён; прежние блоки и архив сохранены дословно |
| Эта папка | Полный factual report, structured test evidence, версии исходников и проверка ротации |

Первый надёжный RED на исходном production: **11 tests = 3 PASS / 8 FAIL / 0 ERROR / 0 SKIP**. Восемь нарушений получили HTTP 200 при неверном hash/flag/revision receipt, несовместимом kind/pre-state контракта, повреждённом JSON журнала либо противоречивом intent/DONE evidence. `red.json` сохраняет actual responses и исходные SHA-256.

После первого repair отдельный RED подтвердил ещё три варианта: неверный Workspace identity, терминальный status журнала и receipt события исполнения (**4 tests = 1 PASS / 3 FAIL**; позитивный тест — допустимый обрыв до DONE-события). Ещё один RED подтвердил исполнение pending INTENT с утраченным журналом (**1 test = 0 PASS / 1 FAIL**): физическая запись состоялась, поэтому было недостаточно защищать только завершённые операции. Эти проверки сохранены в `red2.json` и `red3.json`; соответствующие production checks добавлены после воспроизведения.

Загрузка evidence не исправляет и не переписывает повреждённые источники. При отказе требуется разбор, а не новое право записи. События не становятся источником mutation authority: STARTED-before-write, RC-3 ownership/CAS и post-proof сохраняются в прежних местах. V1 legacy records остаются на прежнем пути.

**Допустимый crash gap:** operation record сохраняется раньше завершающего события. Отсутствие DONE/MUTATION_EXECUTED после уже durable receipt допускается; присутствующий event обязан быть непротиворечив. Первоначальный intent history обязателен. Прерванное создание INTENT до записи его первого события требует ручного разбора; автоматическое восстановление журнала не добавлялось.

## 3. Acceptance matrix

PASS ниже означает результат самопроверки исполнителя; независимая приёмка остаётся за ChatGPT.

| ID | Ожидаемый исход | Полученный исход | Статус |
|---|---|---|---|
| A1 | После durable receipt потерянный ответ не означает failure; повтор возвращает прежний receipt без side effect | Client UNKNOWN / 0 received bytes; серверный trace содержит EXECUTED/receipt до DELIVERY_DROPPED. Write/create/delete и move/rename replay сохраняют исходные receipts и число применений | PASS |
| A2 | Полностью новые process/API/store воспроизводят persisted outcome | Исходный процесс завершён; два новых workers возвращают REPLAYED / physical_mutation_performed=false. Operation JSON byte-identical, receipt/contract идентичны, history prefix сохранён; target bytes/mtime/file identity неизменны, execution event не добавлен | PASS |
| A3 | Одновременные duplicate requests дают ровно одно исполнение | Четыре клиента на первом запросе: 1 EXECUTED + 3 REPLAYED. После lost response: 4 REPLAYED. Оба случая — всего 1 physical apply и 1 MUTATION_EXECUTED | PASS |
| A4 | Другой request с тем же ID отказан, исходная операция неизменна | Все шесть изменений: payload, target, action, precondition, request metadata, microtask → HTTP 409 / OPERATION_ID_CONFLICT; original operation bytes/receipt сохранены | PASS |
| A5 | Окна прерывания дают безопасный retry/reconcile/adopt/manual; UNKNOWN не выдаётся за SUCCESS | Все окна ниже проверены в отдельных процессах; разрешение Resolver требуется там, где оно предусмотрено. P-2 остаётся явным fail-closed | PASS |
| A6 | PRE/exact POST/partial/ambiguous различимы; move/rename не атомарны | PRE → RETRY_SAFE; exact POST → ADOPT_CURRENT_STATE; mixed → ROLLBACK_CURRENT_MICROTASK; drift и PRE=POST → MANUAL_REVIEW_REQUIRED. Partial move повторяет только неисполненный DELETE; drift source сохраняется и даёт PARTIAL | PASS |
| A7 | Повтор не создаёт mutation authority в обход действующих gates | Отказаны closed pending/new operations, non-ACTIVE microtask, target вне manifest, corrupt snapshot/payload, чужой/released claim, stale retry evidence/CAS. Неверные physical post bytes не дают DONE/receipt. Исторический replay не перезаписывает последующий drift | PASS |
| A8 | Identity, contract, receipt и history согласованы после restart; повреждение fail-closed | Все 17 integrity cases → HTTP 409. Повреждённые артефакты сохраняются; pending INTENT без history больше не выполняет запись. Позитивные replay сохраняют исходную operation JSON и prefix истории | PASS |

### Окна A5

| Точка потери | Persistent состояние до повтора | Повтор и recovery | Физические применения |
|---|---|---|---|
| До STARTED | INTENT, exact PRE | Новый process исполняет первую mutation; RETRY_SAFE | 0 → 1 |
| После STARTED, до записи | STARTED, exact PRE, receipt отсутствует | HTTP 409 / RECONCILIATION_REQUIRED; Resolver RETRY → одно исполнение | 0 → 1 |
| После physical write, до receipt | STARTED, exact POST, receipt отсутствует | HTTP 409; ADOPT → RC-6 VERIFIED, затем исторический replay | 1 → 1 |
| После durable receipt, до DONE event | DONE/receipt есть, завершающих событий нет | Прежний receipt / REPLAYED; отсутствующее событие не фабрикуется | 1 → 1 |
| После receipt/DONE event, до execution event | DONE/receipt есть, MUTATION_EXECUTED отсутствует | REPLAYED; execution event остаётся отсутствующим | 1 → 1 |
| При отправке готового HTTP response | DONE/receipt и execution event сохранены, клиент UNKNOWN | Новый process возвращает прежний receipt | 1 → 1 |

Отдельно UNKNOWN_AFTER_DISCONNECT + принятой RETRY resolution → `RETRY_LIFECYCLE_UNSUPPORTED`, HTTP 409, 0 writes. Это сохранённое ограничение P-2. ADOPT не считается вторым исполнением; после crash до execution event его количество закономерно равно нулю. Отсутствие повторной записи подтверждается отдельным fsync-журналом `_apply`, байтами и operation evidence, а не только числом execution events.

## 4. Проверки и воспроизведение

Среда: Windows, Python 3.12.10 / MSC v.1943 / AMD64, `M:\GitHub\ag_llm\.venv\Scripts\python.exe`. Команды выполняются из корня проекта. Полные stdout-логи оставлены вне проекта во временной директории; в этой папке сохраняются structured evidence.

```powershell
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --output "$env:TEMP\CODEX-WA4-A-001-focused-v2" test_web_alarm_lost_response test_web_alarm_mutation_executor test_web_alarm_operation_contract test_web_alarm_operation_store test_web_alarm_target_claims test_web_alarm_resolver test_web_alarm_recovery_coordinator
.\.venv\Scripts\python.exe -B wa4a_acceptance.py --output "$env:TEMP\CODEX-WA4-A-001-full-v2" all
.\.venv\Scripts\python.exe -B -X "pycache_prefix=$env:TEMP\CODEX-WA4-A-001-compile-final" -m compileall -q web_alarm wa4a_acceptance.py test_web_alarm_lost_response.py
```

| Итоговый запуск | RUN | PASS | FAIL | ERROR | SKIP | Exit |
|---|---:|---:|---:|---:|---:|---:|
| WA4-A | 46 | 46 | 0 | 0 | 0 | 0 |
| Исходные WA4-E | 36 | 36 | 0 | 0 | 0 | 0 |
| Смежные RC (contract/store/claims/Resolver/coordinator) | 84 | 84 | 0 | 0 | 0 | 0 |
| Focused всего | 166 | 166 | 0 | 0 | 0 | 0 |
| Полный Web Alarm | 689 | 688 | 0 | 0 | 1 | 0 |

Focused: 160.785 s, violations=0. Полный: 588.267 s, violations=0. Счётчики взяты из runner results, не из исторических 643/5 CI PASS. `full.json` содержит каждый тест, source hashes и skip reason: test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed — symlink creation is not permitted here.

Compileall — exit 0, все создаваемые bytecode направлены во временную папку. Ordinary file checks четырёх целевых Python-файлов: trailing whitespace=0, conflict markers=0. Git diff/check не запускался.

Runner устанавливает audit guard в родителе и через temporary sitecustomize во всех Python subprocesses: writes разрешены только в системном temp, non-Python subprocesses/shell/Git metadata и внешние socket/DNS запрещены; loopback оставлен для существующих HTTP tests. Это контроль доверенных тестов, не ОС-песочница. Native Windows fixture helpers проверены по исходникам и используют временные пути.

До надёжного RED были две калибровки новой оснастки: 34 tests = 0 PASS / 1 FAIL / 33 ERROR; затем 34 = 21 PASS / 9 FAIL / 4 ERROR. Исправлены Windows Popen audit argument shape, точное имя MANUAL_REVIEW_REQUIRED, assertion поля Resolver и выбор snapshot вместо payload blob. Эти ошибки не объявляются production defects. Полная хронология чисел — `runs.json`; в каждой калибровке isolation violations=0.

Промежуточные зелёные прогоны 39/39, 120/120, 43/43, 165/165 и первый полный 688 (687 PASS, 1 SKIP; 626.275 s) относятся к промежуточным версиям. После полного прогона отдельный RED подтвердил backdated receipt revision: 1 test = 0 PASS / 1 FAIL, HTTP 200. Проверка receipt-bearing history дополнена после воспроизведения; добавлен 46-й тест. `red4.json` сохраняет пробу. Все итоговые focused/full повторены на окончательных исходниках.

## 5. Версии и evidence

`versions.json` хранит исходные/final SHA-256 и размер файлов, hashes нормативных источников и фактический scope check. `red*.json`, `focused.json`, `full.json` дополнительно фиксируют source hashes соответствующего запуска. Внутри одного incident receipt сравнивается целиком; timestamps/PID независимых новых fixtures между отдельными прогонами должны отличаться.

| Production файл | SHA-256 исходный | SHA-256 итоговый |
|---|---|---|
| `web_alarm/operation_contract.py` | `b711c447b47117f4a5cb319ce644e0e5d9f48f5992bb75a5f7e00ad3c6005ba4` | `bedd5887df54093814244ed1b8b8f8d6480c2120e4e0dd3f791a2356cdf391b6` |
| `web_alarm/operation_store.py` | `1e9bfdb8db010b6a9abe61cb3cbe9a79db50353a7ec0b85ba799ad38436863e3` | `2afc17719c017eab2e6550d9bcfd7b895c2e90cb818a669a7bfee872bd163002` |

Scope check: из 216 исходно зафиксированных файлов 211 остались byte-identical; авторские изменения существующих файлов ограничены двумя Web Alarm runtime файлами и персональной карточкой. Mutation executor/server/CLI и исходные WA4-E tests не изменялись. Ultra и общие документы других агентов не редактировались. Наблюдался внешний drift `.obsidian/graph.json` и `.obsidian/workspace.json`; эти файлы не записывались и не восстанавливались исполнителем. Проверка ротации сохраняется в `rotation.json`: исходная постановка, прежние БЛОКИ 2/3 с архивами и их hashes/дословное включение.

## 6. Ограничения и независимая проверка

1. Доказана deterministic HTTP handler acceptance и process restart. Реальный сетевой/Remote disconnect не проводился; потеря CLI stdout отдельно не инъектировалась. Существующие CLI tests входят в regression.
2. `REPLAYED / KNOWN_RECEIPT` возвращает **исторический** outcome. Он не утверждает, что target сейчас по-прежнему равен POST_STATE. Тест последующего внешнего drift получает старый receipt, сохраняет новые bytes и отдельно получает MANUAL_REVIEW_REQUIRED при reconciliation. Current-byte proof обязателен для нового physical execution и ADOPT.
3. P-2, P-3, P-4 и R-1…R-4 остаются. Microtask-wide evidence может требовать ROLLBACK вместо узкого ADOPT. Неподчиняющийся writer между CAS и replace, Windows sharing retries, автоматическое mkdir и payload limits этим scope не решаются. Move/rename — два durable child IDs, не atomic transaction.
4. A8 проверяет обнаружимые повреждения и противоречия. Криптографическая аутентификация журнала/защита от согласованной подмены всех источников не реализованы. Повреждённый/утраченный первоначальный журнал блокирует дальнейшее исполнение; автоматического healing нет. Crash может оставить допустимый отсутствующий terminal tail.
5. History validation читает TASK event log при загрузке v2 operation. Нагрузочные характеристики больших историй не измерялись; стоимость линейна по журналу на загрузку. Benchmark/индексация не добавлялись.
6. Независимая приёмка, Git publication и CI после публикации не выполнялись. Для воспроизведения использовать guarded команды выше и сверить source hashes; отдельно рассмотреть семантику исторического replay и допустимых log gaps.

## 7. DOC IMPACT / передача

DOC IMPACT: YES. CURRENT STATE IMPACT: YES. ARCHITECTURE IMPACT: YES — уточнение implementation integrity gate, без redesign authority/recovery. CONTEXT LIBRARY IMPACT: NO. REGISTRY / ROUTING IMPACT: YES. NEW DOCUMENT REQUIRED: YES — этот factual report запрошен постановкой. CANONICAL OWNER: 23, plan 24, history 25; единственный редактор общих документов — ChatGPT.

Фактически изменены персональная карточка и эта папка evidence. Общие 000/34/05/06/01/04/08/18/23/24/25 — read-only, статусы DONE/VERIFIED исполнителем не проставлялись.

**SHARED DOC DELTA для ChatGPT:**

- 23: после проверки описать v2 consistency checks, обязательный intent evidence, допустимое отсутствие terminal tail и историческую семантику receipt.
- 24/25: зафиксировать WA4-A результат, A1–A8, точные current test counts/hashes и оставшиеся P/R. DONE/VERIFIED — только после независимого PASS.
- Общие 000/34/05/06 и Web Alarm строка 01: отразить передачу CODEX-WA4-A-001 на проверку и запрет автоматического запуска WA4-O/WA4-R. В 01 также есть старая перекрёстная фраза WA4-E «stays pending», противоречащая текущей Web Alarm строке и 23–25; предложено исправить координатору, локально не менялась.
- 04/08/18 и инструкции других агентов: NO CHANGE; нового маршрута/полномочий/общего регламента не вводится.

CONTRADICTION CHECK: выполнен в пределах локальных источников, предложенные shared дельты ещё не записаны. LOSS CHECK: подтверждается `rotation.json`. DOC CLOSEOUT INCOMPLETE — общий контур ожидает независимую проверку и запись ChatGPT; это не скрытая локальная мутация общих статусов.

**NEXT:** независимая приёмка ChatGPT; публикацию выполняет пользователь/уполномоченный координатор. Другие задачи не запускать.
