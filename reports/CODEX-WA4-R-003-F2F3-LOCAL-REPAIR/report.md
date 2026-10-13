# CODEX-WA4-R-003-F2F3-LOCAL-REPAIR — factual report

**STATUS: RESULT READY / AWAITING INDEPENDENT VERIFICATION.** Локальный исполнитель 007/Codex; Windows, Python 3.12.10; 2026-10-13. Независимый verifier: ChatGPT / WEB_07. Это локальный repair, не merge/rollout/STRICT approval. F1 остаётся OPEN. ARCH CLASS: Web Alarm Workspace; PRIMARY PROFILE: 23; TEST PROFILE: 36.2.

## 1. Вывод и границы доказательства

**F2: подтверждены и исправлены конкретные runtime-дефекты.** Старый поиск TASK мог выдать ложный duplicate из двух наблюдений по разные стороны одного атомарного move. Прямой `TaskStore.complete_task` не разделял operations lock с begin/acquire/release, позволяя переместить TASK посреди защищённого другим lock чтения/append. После repair контролируемые расписания дают нормальный EXECUTED либо строгий REFUSED с соответствующими raw bytes/records; late writes и повторный apply не разрешаются.

**F3: историческая фаза установлена, механизм воспроизведён нативно и исправлен; полная историческая атрибуция ограничена.** Оригинальный CI record доказывает pre-move PermissionError/WinError 5, active-only TASK/PLANNED. Локальный phase-barrier reproducer показал тот же native отказ из-за RAW read handle `OperationStore.begin`, открытого до operations lock. Перенос чтений внутрь lock устраняет этот обход. Исходный CI не записывал владельца handle: нельзя утверждать, что установлен именно тот процесс или исключены все причины WinError 5. Исторический FAIL сохранён; этот отчёт не присваивает ему VERIFIED.

Дополнительно ручная ревизия обнаружила ложный UNKNOWN в первой версии исправления location lookup; отдельный RED test потребовал bounded destination recheck. Смежный focused FAIL выявил недостаточную постановку старого теста двух исполнителей: start barrier не фиксировал общий CAS basis. Оба случая раскрыты ниже, без повторов до случайного PASS.

## 2. Вход, provenance и scope

Пройден маршрут 08 → персональный 000 → 34 → 18 → 01 → профили 23/24/25 → 36/36.1/36.2, включая TEST-COLLAB-01 и TEST-ENG-01. Активный БЛОК 1 оставался byte-identical до финальной регламентной ротации. Два handoff пользователя/WEB_07 и вложенные JSON/ZIP — AMENDMENT/evidence; постановка не заменялась.

Supplied CI source: `37123b176097c15c8d21e0040bdf7d7f3e8072a3`, run `38379575748`, artifact `wa4r002-independent-38379575748-1`. Локальную equivalence этой ревизии не проверял через Git. Начальные file-byte SHA и узкие before copies шести изменённых исходников зафиксированы отдельно от supplied commit ID.

Пользователь передал оригинальный ZIP локальным файлом. Адресно прочитаны только `wa4r002-focused/results.json`, его единственная FAIL-запись и пустой isolation.jsonl. SHA-256 results — `956a8c608d169c3a610073692b948ecca71e38f8c3293fe1cc660584ae0f9398`; ZIP — `020d2770b48f90e0d24df071b10c2ad5fe5caa2972d8d3070445ac875963e120`. FAIL record полностью совпал с отдельным JSON excerpt (JSON object equality). ZIP и excerpt сохранены без изменения; весь CI журнал повторно не исследовался.

Исторический F3: chain `CloseoutError → TaskStoreError → PermissionError`, native `os.replace(active/task_w, completed/task_w)`, errno=13, winerror=5. c0 exit=0/FAILED:CloseoutError, b1/b2 BEGUN, m3 CREATED. Terminal active=true/completed=false, PLANNED, operations op_b1/op_b2, plan m1/late_m3, 7 events, оба исходных project файла сохранены. Это не post-move failure и не состоявшийся crash_exit. Исторический F2 duplicate chain взят из утверждённого БЛОКА 1; данный ZIP не содержит исходный 80-round F2 artifact.

Git/GitHub, .git, live project/storage, Ultra/Voice/UI, существующий runner/workflow и общие документы мной не изменялись. Все fault injection и реальные rename/handle tests — только собственные disposable TEMP fixtures. Runner guard запрещал внешнюю сеть, Git и неразрешённые записи/команды; существующие локальные loopback HTTP tests допустимы. Это test isolation, не sandbox против враждебного OS-процесса.

## 3. Причины, альтернативы и изменения

| Механизм | Доказательство до repair | Итоговое изменение / предел |
| --- | --- | --- |
| `_task_path`: active=True, затем completed=True из разных моментов | Real directory move между stat probes; ERROR duplicate при физическом completed-only состоянии | Destination-first lookup; genuine duplicate по-прежнему исключение. Это поиск пути, не linearizable snapshot |
| Первая поправка: completed=False, move, active=False | `gap-before`: ERROR unknown при completed-only; исходник промежуточной версии сохранён | Только одна дополнительная destination probe; никаких повторов мутации или бесконечных циклов |
| Direct completion обходил operations lock | Старые diagnostics достигали cached task.md/snapshot/events путей и errors; отдельные phase tests удерживают эти места | `complete_task`: safe ID до lock path, operations → mutation; locked variant не берёт non-reentrant lock повторно |
| F3 RAW handle до lock | `repro-before`: реальный WinError 5, а не подставленное исключение; after-fix closer упирается в ожидаемый bounded StoreLockTimeout, после освобождения reader begin завершается | `OperationStore.begin`: все TASK/RAW admission reads и begin persistence внутри operations → mutation |
| Early executor payload/manifest reads открывали TASK вне той же границы | Source walkthrough выявил обход до acquire/boundary | Preflight reads под operations → mutation; locks освобождаются до acquire. Failure → REFUSED/ADMISSION_UNAVAILABLE, INTENT сохраняется, apply=0; последующий replay безопасен |

Изменены ровно три runtime-файла: `web_alarm/task_store.py` (`_task_path`, `complete_task`, контракт `complete_task_locked`), `web_alarm/operation_store.py` (`begin`), `web_alarm/mutation_executor.py` (`_execute` preflight). CAS, ownership, STARTED-before-write, DONE receipt proof, RC-2/3/4/5/6 gates, authority boundaries и storage commit point не ослаблены. Прямое завершение остаётся негейтированным storage primitive; публичный workflow по-прежнему использует CloseoutService.

## 4. Test currency и развитие общей базы

CURRENT: исходные F2/F3 selectors и их строгие критерии; F3 writer-first требует REJECTED, crash branch требует exit9 и сохранность closed TASK. INSUFFICIENT: один random start barrier не задаёт порядок stat/read/move и не доказывает crash phase. NEEDS UPDATE: три diagnostic cases, ранее фиксировавшие исправляемые API errors, теперь проверяют сериализацию, raw state, event/receipt preservation и fresh replay. Старые selectors сохранены; OBSOLETE/removal нет. Неисправленные F1 и direct Projection cached snapshot tests сохраняют старый контракт.

В `test_web_alarm_wa4r002_diagnostics.py` добавлены 7 общих regression methods: phantom duplicate при real move; genuine duplicate refusal; move gap/UNKNOWN; held native RAW reader до admission; completion lock timeout без writes и последующее освобождение; invalid ID без lock files; preflight refusal без apply и безопасный replay. Старые 8 усилены phase/raw oracle; release-event case требует ровно один release event и одну физическую запись.

В `test_web_alarm_reliability_wa017.py` сохранён strict original race, добавлены реальные markers `before_directory_move → directory_moved → crash_exit_9`; parent требует их ровно в этом порядке для exit9. После kill процессы reaped до terminal snapshot.

В `test_web_alarm_mutation_executor.py` удалён старый 100-retry completion loop; первая ошибка теперь FAIL. Добавлены raw terminal TASK/plan/operations/events/file hashes, per-worker stdout/stderr/exit и физический apply count. Сохранены strict no-write-after-close assertions. Пропущенный при инструментировании импорт hashlib дал один harness ERROR; он сохранён и исправлен, затронутый selector повторён.

Focused первый раз дал ещё один FAIL: два EXECUTED в `test_two_executors_on_one_physical_target_never_both_write`. В тесте не было заранее объявленных контрактов; второй begin мог законно наблюдать POST первого. Контролируемый последовательный запуск старого oracle воспроизводит FAIL и raw records показывают `pre(B)=receipt(A)`, разные CAS bases. Исправлена постановка: оба INTENT заранее закрепляют literal BEFORE, затем конкурентные дети replay этих контрактов; строгий критерий ровно один apply не ослаблен. Добавлен восьмой общий method, доказывающий допустимые последовательные fresh contracts с разными CAS bases. Для конкретного случайного FAIL прежний harness не сохранил raw contracts, поэтому причинная реконструкция именно его расписания ограничена; дефект старого oracle установлен независимо.

## 5. Команды, collection и локальные результаты

Рабочий каталог `M:/GitHub/ag_llm`; Python `.venv/Scripts/python.exe`; TEMP root `C:/Users/REX/AppData/Local/Temp/codex-wa4r003-ap5tmftn`.

Каждая строка таблицы — отдельный output directory `<TEMP>/<attempt>`, stdout/stderr `<TEMP>/<attempt>.log`, exit `<TEMP>/<attempt>.exit`. Точный список targets, test IDs, source SHA, счётчики и первоначальные tracebacks — в `checks.json` и `evidence.zip`.

Стандартная команда для любой runner-строки: `.venv/Scripts/python.exe -B -X utf8 wa4a_acceptance.py --task CODEX-WA4-R-003-F2F3-LOCAL-REPAIR --output <TEMP>/<attempt> <targets из checks.json>`.

Для `restart-utf8` и итогового `full-utf8` перед командой установлено `$env:PYTHONUTF8 = '1'`, чтобы UTF-8 наследовали Python children. Остальные attempts запускались с `-X utf8` только у parent.

Focused targets: `test_web_alarm_mutation_executor test_web_alarm_reliability_wa017 test_web_alarm_wa4r002_diagnostics test_web_alarm_projection_concurrency`. FULL target: `all`.

Stress targets (5 отдельных запусков, не retry-on-failure): `test_web_alarm_mutation_executor.RaceTests.test_execution_racing_the_task_closure_never_writes_into_a_closed_task test_web_alarm_reliability_wa017.CompletionCrashRaceTests.test_writers_racing_a_dying_completion_never_land_in_the_closed_task`.

Quality: `.venv/Scripts/python.exe -B -X utf8 reports/CODEX-WA4-R-003-F2F3-LOCAL-REPAIR/quality_controls.py <TEMP>/quality-final`. Предыдущий quality запуск дополнительно передавал `<TEMP>` вторым аргументом старому loader. Final controls используют сохранённые узкие method snippets `control-inputs.json`, в памяти; production files не подменяются. Outer PASS означает ожидаемый inner RED с конкретной причиной, не product PASS.

| Attempt | PASS / FAIL / ERROR / SKIP | Exit / guard violations | Runner s |
| --- | --- | --- | --- |
| baseline | 10 / 0 / 0 / 0 | 0 / 0 | 20.837 |
| repro-before | 1 / 1 / 1 / 0 | 1 / 0 | 2.201 |
| target-1 | 13 / 0 / 0 / 0 | 0 / 0 | 27.462 |
| gap-before | 0 / 0 / 1 / 0 | 1 / 0 | 0.783 |
| target-final | 17 / 0 / 0 / 0 | 0 / 0 | 30.709 |
| quality | 5 / 0 / 0 / 0 | 0 / 0 | 3.761 |
| target-raw-final | 16 / 0 / 1 / 0 | 1 / 0 | 24.459 |
| f2-import-fixed | 1 / 0 / 0 / 0 | 0 / 0 | 6.051 |
| focused-final | 69 / 1 / 0 / 0 | 1 / 0 | 115.773 |
| cas-harness-final | 4 / 0 / 0 / 0 | 0 / 0 | 20.035 |
| quality-final | 6 / 0 / 0 / 0 | 0 / 0 | 8.084 |
| focused-final-2 | 71 / 0 / 0 / 0 | 0 / 0 | 115.750 |
| stress-1 | 2 / 0 / 0 / 0 | 0 / 0 | 12.405 |
| stress-2 | 2 / 0 / 0 / 0 | 0 / 0 | 13.143 |
| stress-3 | 2 / 0 / 0 / 0 | 0 / 0 | 14.280 |
| stress-4 | 2 / 0 / 0 / 0 | 0 / 0 | 11.400 |
| stress-5 | 2 / 0 / 0 / 0 | 0 / 0 | 10.974 |
| full-final | 766 / 0 / 2 / 1 | 1 / 0 | 730.356 |
| restart-diagnostic | 0 / 0 / 2 / 0 | 1 / 0 | 3.289 |
| restart-utf8 | 2 / 0 / 0 / 0 | 0 / 0 | 4.479 |
| full-utf8 | 768 / 0 / 0 / 1 | 0 / 0 | 727.239 |

Первый FULL: 766 PASS/0 FAIL/2 ERROR/1 SKIP. Оба ERROR restart/checkpoint имели исходный UnicodeDecodeError в Windows `_readerthread`, затем json.loads(None): parent `-X utf8` не наследовался children, печатавшими non-ASCII JSON в Windows-кодировке. Read-only environment probe установил parent utf8_mode=1, default child cp1251/utf8_mode=0, child с PYTHONUTF8=1 — utf-8/utf8_mode=1 (`encoding-probe.json` в ZIP). Изолированный `restart-diagnostic` воспроизвёл обе ошибки; только `PYTHONUTF8=1` дал `restart-utf8` 2 PASS без source edits. После устранения этой ошибки команды полный набор повторён целиком в `full-utf8`; первый red FULL сохранён и не считается приёмкой.

Syntax gate: AST/compile 6 изменённых файлов и 7 embedded child scripts; bytecode не создавался. Семь common regression methods диагностики + один sequential CAS method добавлены без потери прежних 761 IDs. Final collection: **769 уникальных IDs = 761 прежних + 8 новых; FULL 768 PASS / 0 FAIL / 0 ERROR / 1 SKIP**; итоговый runtime manifest совпал с static inventory. Focused: 71 IDs; quality: 6 outer controls. Все финальные source SHA совпадают между addressed/focused/quality/stress/FULL и текущими исходниками.

Bounded stress: 5 × 2 methods × 4 внутренних раунда = 40 раундов. F2: 17 EXECUTED и 3 REFUSED, строго 1/0 apply и соответствующие POST/PRE. F3: 20 exit9 с полными markers; natural writer-first REJECTED в этих 20 раундах не наблюдался, его отдельно доказывает deterministic writer-first test. Это ограниченная выборка, не вероятность отсутствия всех гонок Windows.

Negative controls: возвращение old lookup → duplicate ERROR; отключение bounded recheck → unknown ERROR; снятие completion outer lock → expected-timeout assertion FAIL; удаление native fault trigger → F1 oracle FAIL; counterfeit raw receipt → FAIL; старый CAS oracle при lawful sequential execution → FAIL с подтверждёнными разными bases. Итоговый FULL имеет один platform SKIP: `test_web_alarm_target_identity.CanonicalTargetTests.test_symlink_target_fails_closed`, symlink creation is not permitted here. Этот сценарий локально не проверен; иных SKIP нет.

Все 6 controls обнаружили целевое нарушение; без blanket exceptions, SKIP/XFAIL или убранных selectors.

## 6. MANUAL ENGINEERING REVIEW — отдельная ревизия после исправлений

1. Перечитаны изменённые функции целиком и callers `CloseoutService.complete`, executor `_intent/_drive/_manifest_refusal/_mutate_locked/_release`, OperationStore `_serialized/_prepare/_touch_checkpoint`, TargetClaimService acquire/mutation_boundary/release, TaskStore mutation writers. Проверен порядок operations → mutation → target; TaskStore metadata writers не обращаются обратно к OperationStore под mutation lock. Единственный внешний caller `complete_task_locked` — CloseoutService, уже держащий оба lock. Повторный non-reentrant lock туда не добавлен; preflight освобождает оба lock перед acquire/boundary.
2. Admission-first, close-first, остановка перед STARTED, во время apply, после DONE до release и после move до status разобраны отдельно. До STARTED ошибки не дают physical apply. Boundary повторно проверяет lifecycle/manifest/CAS под locks; stale preflight не даёт authority. Direct close может оставить admitted INTENT в completed, но subsequent execute строго REFUSED; gated close с открытым intent/claim строго REJECTED. Raw DONE/receipt и единственный release event сохраняются при последующем move/replay.
3. Timeout/invalid ID/exception exits: ID проверяется до создания lock path; acquisition failure не переносит TASK и не пишет target. Вложенные context managers освобождают outer lock при отказе inner lock; OS releases locks при crash. Fresh-process recovery/replay проверяет реальное durable состояние, не RAM прошлой инстанции. Отказ move сохраняет active/PRE; native status-write refusal оставляет completed/PLANNED и gated fresh completion восстанавливает статус без повторной mutation. Это F1 compatibility evidence, не закрытие F1.
4. Adversarial counterexample к первой версии location repair найден вручную и сначала RED, затем исправлен. Destination-first + bounded recheck корректен для compliant monotonic active→completed; genuine simultaneous duplicate по-прежнему fail-closed. Возвращённый Path может устареть немедленно для несериализованного внешнего reader; функция не обещает filesystem snapshot.
5. Независимо от production enum прочитаны JSON/JSONL и literal binary target hashes из финального focused evidence. Проверены PRE/POST, active/completed, status, operation/receipt, claims/event history, preserved checkpoint и fresh outcomes. В `checks.json.raw_review` дан индекс фактически проверенных raw states; полные bytes/hex/hash и фазовые промежуточные наблюдения — в ZIP. Полные terminal observations получены после остановки workers; промежуточные barriers помечены отдельно.
6. Отвергнуты гипотезы «всякий WinError 5 — status-pending», «exit0 означает успешный close», «любой CloseoutError допустим вместо REJECTED», «два EXECUTED всегда нарушение», «зелёный rerun закрывает исторический FAIL». Receipt — историческое доказательство соответствующего apply, не доказательство текущего состояния после последующих lawful mutations. Новый sequential test специально проверяет это различие.

## 7. Остаточные риски и ограничения

- Исторический F3 handle owner и все внешние причины WinError 5 не наблюдались. Локальный causal reproducer закрывает найденный read-before-lock механизм, не доказывает отсутствие стороннего reader/антивируса. F1 OPEN; WARN/GATEWAY REQUIRED/STRICT не включались.
- Direct несериализованный `ProjectionService.build` всё ещё может получить FileNotFoundError по cached snapshot после move. Сохранённый test доказывает неизменность raw data/checkpoint и fresh STALE/non-authoritative projection; runtime этого read-only пути здесь не ремонтировался. Нельзя выдавать весь Web Alarm за свободный от I/O ошибок.
- Advisory locks предполагают compliant writers. Внешнее изменение/удаление TASK, real disk exhaustion, reboot/power loss, файловые системы кроме текущего локального Windows не полностью моделируются; нет формальной linearizability proof или performance benchmark больших payloads. Дополнительная сериализация может дать честный bounded timeout при долгом writer, не SUCCESS.
- Source revisions — file-byte SHA; Git equivalence и новая GitHub CI не проверялись/не запускались. Исходный 80-round F2 ZIP не предоставлен. Все локальные intermediate RED/ERROR сохранены; локальные зелёные проверки — self-reported до независимого аудита.
- В защищённом начальном наборе 159 файлов обнаружен drift нескольких общих документов вне моих записей. Точные before/observed-after hashes перечислены в `versions.json.observed_non_scope_drift`; эти файлы не откатывались. Актуальные относящиеся к задаче TEST-ENG/DOC-GIT/Block1 правила адресно сверены. Runtime/test revision во время финальных прогонов оставалась неизменной.

## 8. Артефакты, DOC IMPACT / SHARED DOC DELTA и NEXT

Один основной отчёт: этот файл. `checks.json` — 21 attempts, counts/IDs/SHA/isolation/негативные controls/raw index; `versions.json` — baseline/after и collection; `evidence.zip` — полные results/logs/exit/isolation, шесть scoped before sources, необходимые промежуточные версии и обычный difflib patch (без Git). `historical-CI.zip` / `historical-F3.json` — оригинальные пользовательские вложения. `quality_controls.py` / `control-inputs.json` — воспроизводимые outer controls. `rotation.json` / `manifest.json` — lossless personal closeout и hashes артефактов. TEMP paths служебные и не гарантируются после очистки; переносимые evidence уже находятся в reports.

**SHARED DOC DELTA — предложено, не записано локально:**

| Файл/контур | Предлагаемая запись после независимой проверки |
| --- | --- |
| 23/24/25 | Completion и admission lock topology operations → mutation; ungated direct storage primitive vs gated public Closeout; preflight ADMISSION_UNAVAILABLE не даёт physical authority; предел path lookup |
| 36.2 | Воспроизводимые Windows commands с наследуемой UTF-8 кодировкой; 8 новых regression methods, deterministic/native/negative controls, точный common collection 769; исправленная постановка общего CAS basis; отдельная историческая receipt vs current bytes гарантия |
| 000/34/05/06/01 | F2/F3 local repair RESULT READY, ссылки на первичные FAIL и этот report, тесты/ограничения; F1 OPEN, independent verification pending, STRICT NOT VERIFIED; не выдавать local PASS за CI acceptance |
| 18/08/36/36.1, Ultra/Voice/UI | Новых нормативных изменений или runtime/UI правил этой TASK не требуется |

DOC CLOSEOUT INCOMPLETE для общего контура до решения координатора. Персональная ротация сохраняет полную первоначальную постановку в БЛОКЕ 2 и старый хвост БЛОКОВ 2–3 дословно в архиве, factual result в БЛОКЕ 3, затем освобождает БЛОК 1. AMENDMENT не подменяет исходную задачу.

**NEXT SAFE ACTION:** WEB_07 независимо проверяет sources/diff, актуальность oracle, historical ZIP/frames, raw terminal/recovery и source hashes; повторяет адресные controls/regressions, при отдельном решении пользователя организует GitHub Windows CI. Только независимый verifier решает VERIFIED/acceptance. Следующие задачи, merge и rollout не запускать.
